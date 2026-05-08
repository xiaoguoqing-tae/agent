import hashlib
from os.path import exists

from utils.hash import get_password_hash
from utils.file import get_abs_path
from utils.file import get_file_md5
from fastapi import FastAPI,Query, HTTPException, Depends, status,File, UploadFile, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from oauthlib.uri_validate import userinfo
from pydantic import BaseModel
from datetime import datetime, timedelta
from fastapi.responses import StreamingResponse
from core.data import get_user
from core.access import create_access_token,get_current_user
from core.database import get_conn
from core.model import chat_model
from utils.hash import verify_password
from core.config import conf
from agent.agent_service import ChatAgentService
from typing import List, Dict, Any

from rag.rag_service import RagService
import os

from core.data import get_departments

app = FastAPI(title="智能助手", version="1.0.0")

# 添加CORS中间件，允许Vue前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应具体指定前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str

class ChatRequest(BaseModel):
    action:str
    messages:str
    doc_ids:list[int]

agent_service = ChatAgentService()

# 健康检查接口
@app.get("/", response_model=dict)
async def root():
    """
    根路径健康检查
    """
    return {
        "success": True,
        "message": "API服务正常运行",
        "data": {
            "title": "智能助手 API",
            "version": "1.0.0"
        }
    }

@app.post("/login")
async def login(request:dict[str,Any]):
    """
    用户登录接口
    接收用户名和密码，验证后返回JWT令牌
    """
    try:
        user = get_user(request['username'])

        if not user or not verify_password(request['password'], user["hashed_password"]):
            raise ValueError('用名或密码错误。')

        if user['is_active']!=1:
            raise ValueError('账号已冻结，请联系管理员。')

        access_token_expire = timedelta(minutes=conf["access_token_expire_minutes"])
        access_token = create_access_token(
            data={"sub": user["username"], "role": user["role"]},
            expires_delta=access_token_expire
        )

        return {
            "status":"success",
            "message":"登录成功。",
            "data":{"token": access_token, "token_type": "bearer", "username": user['username'],
            "role": user["role"]}
        }
    except Exception as e:
        return {"status": "error", "message": f"登录失败，{str(e)}", "data": {}}

#=============================== chat =======================
@app.post("/chat")
async def chat(chatData: ChatRequest,current_user: dict = Depends(get_current_user)):
    """对话"""
    thread_id = f"user_{current_user['id']}:chat_{chatData.action}"

    return StreamingResponse(
        agent_service.stream_chat(thread_id,chatData.messages,chatData.doc_ids),
        media_type="text/event-stream",
    )

@app.post("/chat/title")
async def chat_title(data:dict[str,Any],current_user: dict = Depends(get_current_user)):
    """给新对话取名字"""
    message = data.get("message")
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        llm = chat_model
        res = llm.invoke(f"请为以下文本生成一个简短的标题：\n\n{message}")
        title = message
        if res:
            title = res.content
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO chat(user_id,title)VALUES(?,?)""",(current_user["id"],title,))
        chat_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return {"id": chat_id, "title": title,"message":message}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

@app.get("/chat/list")
def get_chat_list(current_user: dict = Depends(get_current_user)):
    """获取对话列表"""
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""SELECT * FROM chat WHERE user_id = ?""",(current_user["id"],))
        chat_list = cursor.fetchall()
        cursor.close()
        conn.close()
        return chat_list
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

@app.get("/chat/message")
async def get_chat_message(id,current_user: dict = Depends(get_current_user)) -> List[dict[str, Any]]:
    """获取 chat 内容"""
    thread_id = f"user_{current_user['id']}:chat_{id}"
    return await agent_service.get_history(thread_id)

@app.post("/chat/delete")
async def delete_chat_message(data:dict[str,Any],current_user: dict = Depends(get_current_user)):
    """清空指定会话的历史（通过保存空状态实现）"""
    try:
        thread_id = f"user_{current_user['id']}:chat_{data.get('id')}"
        await agent_service.clear_history(thread_id)
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""DELETE FROM chat WHERE id = ?""",(data.get('id'),))
        conn.commit()
        cursor.close()
        conn.close()
        return {"status":"success","message":"操作成功。"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/chat/rename")
async def rename_chat_message(data:dict[str,Any],current_user: dict = Depends(get_current_user)):
    """chat 重命名"""
    try:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""UPDATE chat SET title = ? WHERE id = ?""",(data.get('title'),data.get('id')))
        conn.commit()
        cursor.close()
        conn.close()
        return { "status":"success" ,"message":"操作成功。"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#==================部门==================================
@app.get("/dept/list")
async def get_dept_list(current_user: dict = Depends(get_current_user)):
    try:
        res = get_departments()
        return {"status":"success","message":"获取成。","data":res}
    except Exception as e:
        return {"status": "error", "message": f"获取失败。{str(e)}", "data": {}}

@app.post("/dept/create")
async def dept_create(data:dict[str,Any],current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    cursor = conn.cursor()
    try:

        has = cursor.execute("SELECT * FROM depts WHERE name = ?",(data.get('name'),)).fetchone()
        if has:
            raise ValueError("此名称已存在，请勿重复操作。")

        cursor.execute("INSERT INTO depts(name) VALUES (?)",(data.get('name'),))
        id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        if id:
            return {"status":"success","message":"创建成功。","data":{"id":id,"name":data.get("name")}}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"创建失败，{str(e)}", "data": {}}

@app.post("/dept/update")
async def dept_update(data:dict[str,Any],current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE depts SET name = ? WHERE id = ?",(data.get('name'),data.get('id')))
        conn.commit()
        cursor.close()
        conn.close()
        return {"status":"success","message":"修改成功。","data":{"id":data.get('id'),"name":data.get("name")}}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"修改失败，{str(e)}", "data": {}}

@app.post("/dept/delete")
async def dept_delete(id:int,current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM depts WHERE id = ?",(id,))
        conn.commit()
        cursor.close()
        conn.close()
        return {"status":"success","message":"删除成功。","data":{}}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"删除失败，{str(e)}", "data": {}}

@app.get("/dept/user")
async def dept_user(id:int,current_user: dict = Depends(get_current_user)):
    """获取未分配的账号"""
    conn = get_conn()
    cursor = conn.cursor()
    try:
        # sql="""
        # SELECT
        #     u.id,
        #     u.username,
        #     u.email,
        #     CASE
        #         WHEN ud.user_id IS NOT NULL THEN 'Y'
        #         ELSE 'N'
        #     END AS assign
        # FROM users u
        # LEFT JOIN (
        #     -- 先去重，避免一个用户关联多个部门导致重复行
        #     SELECT DISTINCT user_id
        #     FROM user_dept
        # ) ud ON u.id = ud.user_id;
        # """
        sql="""
        SELECT 
            u.id,
            u.username,
            u.email,
            CASE 
                WHEN ud.dept_id IS NOT NULL THEN 'Y'
                ELSE 'N'
            END AS assign
        FROM users u
        LEFT JOIN user_dept ud 
            ON u.id = ud.user_id 
            AND ud.dept_id = ?
        """

        data = cursor.execute(sql,(id,)).fetchall()

        cursor.close()
        conn.close()
        return {"status":"success","message":"获取成功。","data":data}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"获取失败失败，{str(e)}", "data": {}}

@app.post("/dept/assign")
async def dept_assign(request:dict[str,Any],current_user: dict = Depends(get_current_user)):
    """获取未分配的账号"""

    conn = get_conn()
    cursor = conn.cursor()
    try:

        cursor.execute("DELETE FROM user_dept WHERE dept_id = ?",(request.get('deptId'),))
        for userId in request.get('userIds'):
            cursor.execute("INSERT INTO user_dept(dept_id,user_id) VALUES (?,?)",(request.get('deptId'),userId))
        conn.commit()
        cursor.close()
        conn.close()
        return {"status":"success","message":"操作成功。","data":userinfo}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"操作失败，{str(e)}", "data": {}}


#========================用户==================
@app.get("/user/list")
async def user_list(current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        users = cursor.execute("""SELECT * FROM users""").fetchall()

        cursor.close()
        conn.close()
        return {"status": "success", "message": "查找成功。", "data": users}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"查找失败，{str(e)}", "data": {}}

@app.post("/user/create")
async def user_create(request:dict[str,Any],current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        user = cursor.execute("""SELECT * FROM users WHERE username = ?""",(request.get('username'),)).fetchone()
        if user:
            raise ValueError(f"此账号“{user['username']}”已存在，请勿重复创建。")

        user = cursor.execute("""SELECT * FROM users WHERE email = ?""", (request.get('email'),)).fetchone()
        if user:
            raise ValueError(f"此邮箱“{user['email']}”已被占用，请更换。")


        if request.get('password') == "":
            raise ValueError(f"密码不能为空。")

        password_hash = get_password_hash(request.get('password'))

        cursor.execute("INSERT INTO users(username,email,hashed_password,is_active,role) VALUES (?,?,?,?,?)",(request.get('username'),request.get('email'),password_hash,request.get('active'),request.get('role')))

        id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "success", "message": "创建成功。", "data": {"id":id,"username":request.get('username'),"email":request.get('email'),"active":request.get('active'),"role":request.get('role')}}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"创建失败，{str(e)}", "data": {}}

@app.post("/user/update")
async def user_update(request:dict[str,Any],current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        user = cursor.execute("""SELECT * FROM users WHERE username = ?""", (request.get('username'),)).fetchone()
        if not user:
            raise ValueError(f"找不到此账号“{request.get('username')}”")


        email = cursor.execute("""SELECT * FROM users WHERE username != ? AND email = ?""", (request.get('username'),request.get('email'))).fetchone()

        if email:
            raise ValueError(f"此邮箱“{email['email']}”已被占用，请更换。")

        password_hash = user['hashed_password']
        if request.get('password') != "":
            password_hash = get_password_hash(request.get('password'))

        cursor.execute("""UPDATE users SET email = ?,hashed_password = ?,is_active = ?,role = ? WHERE username = ?""",(request.get('email'),password_hash,request.get('active'),request.get('role'),request.get('username')))

        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "success", "message": "修改成功。", "data":{"id":user['id'],"username":user['username'],"email":user['email'],"role":user['role']}}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"修改失败，{str(e)}", "data": {}}

@app.post("/user/delete")
async def user_delete(request:dict[str,Any],current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        user = cursor.execute("""SELECT * FROM users WHERE id = ?""", (request.get('id'),)).fetchone()
        if not user:
            raise ValueError(f"找不到此账号“{request.get('username')}”")

        if user['username'] == current_user['username']:
            raise ValueError('不能删除当前登录账号。')
        elif user['username'] == 'admin':
            raise ValueError(f'不能删除管理员“{user["username"]}”账号。')

        cursor.execute("""DELETE FROM user_dept WHERE user_id = ?""",(user['id'],))
        cursor.execute("""DELETE FROM users WHERE id = ?""",(user['id'],))
        conn.commit()
        cursor.close()
        conn.close()

        return {"status": "success", "message": "删除成功。", "data":{"id":user['id'],"username":user['username'],"email":user['email'],"role":user['role']}}
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"删除失败，{str(e)}", "data": {}}

#=========================文件操作===========================
@app.post('/docs/upload')
async def docs_upload(
    file: UploadFile = File(...),
    name: str = Form(...),
    category: str = Form(...),
    size: int = Form(...),
    dept_id: int = Form(...),
    current_user: dict = Depends(get_current_user)
):
    #允许接收的文件
    allowed_types = {
        "text/plain": ".txt",
        "application/pdf": ".pdf",
    }


    try:
        #校验文件
        if file.content_type not in allowed_types:
            raise ValueError(f"不支持文件类型：{file.content_type}")
        if category == 'dept' and not dept_id:
            raise ValueError(f"部门文件，必须选择部门。")

        content = await file.read()

        hx = hashlib.md5(content).hexdigest()

        upload_dir = get_abs_path('data/upload')
        os.makedirs(upload_dir, exist_ok=True)
        with open(get_abs_path(os.path.join(upload_dir, name)), mode='wb') as f:
            f.write(content)
        await file.close()

        conn = get_conn()
        cursor = conn.cursor()

        if category == 'dept':
            cursor.execute(
                """INSERT INTO documents(user_id,dept_id,type,name,size,path,hash,status) VALUES (?,?,?,?,?,?,?,?)""",
                (current_user['id'],dept_id,category,name,size,f"data/upload/{name}",hx,0)
            )
        else:
            cursor.execute(
                """INSERT INTO documents(user_id,type,name,size,path,hash,status) VALUES (?,?,?,?,?,?,?)""",
                (current_user['id'],category,name,size,f"data/upload/{name}",hx,0)
            )
        file_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": "上传成功。",
            "data": {
                "id": file_id,
                "name": name,
                "size": size,
                "path": os.path.join(upload_dir, name),
            }
        }

    except Exception as e:
        return {"status": "error", "message": f"上传失败，{str(e)}", "data": {}}


@app.get("/docs/list")
async def docs_list(current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        sql="""
SELECT 
    d.id,
    d.name,
    d.size,
    d.path,
    d.type as category,
    d.user_id AS owner_id,
    u.username AS owner_name,
    d.status,
    d.dept_id,
    dept.name AS dept_name,
    CASE 
        WHEN d.type = 'personal' THEN '个人文档'
        WHEN d.type = 'dept' THEN '部门文档'
    END AS category_alias,
    d.created_at
FROM documents d
LEFT JOIN users u ON d.user_id = u.id
LEFT JOIN depts dept ON d.dept_id = dept.id
WHERE 
    -- 条件1: 个人文档且是当前用户的
    (d.type = 'personal' AND d.user_id = ?)
    OR
    -- 条件2: 部门文档且用户属于该部门
    (d.type = 'dept' AND d.dept_id IN (
        SELECT ud.dept_id 
        FROM user_dept ud 
        WHERE ud.user_id = ?
    ))
ORDER BY 
    d.type,
    d.id DESC;
        """


        docs = cursor.execute(sql,(current_user['id'],current_user['id'],)).fetchall()

        cursor.close()
        conn.close()
        return {"status": "success", "message": "查找成功。", "data": docs}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"查找失败，{str(e)}", "data": {}}

@app.post("/docs/update")
async def docs_update(data:dict[str,Any],current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    cursor = conn.cursor()
    try:
        id = data.get('id')
        category = data.get('category')
        dept_id = data.get('dept_id')

        if category == 'dept' and dept_id == 0:
            raise ValueError("请选择一个部门。")


        if category == 'dept':
            cursor.execute("UPDATE documents SET type = 'dept',dept_id = ? WHERE id = ?",(dept_id,id))
        else:
            cursor.execute("UPDATE documents SET type = 'personal',dept_id = null WHERE id = ?", (id,))

        conn.commit()
        cursor.close()
        conn.close()
        return {"status":"success","message":"修改成功。","data":{"id":data.get('id'),"dept_id":dept_id,"category":category}}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"修改失败，{str(e)}", "data": {}}


@app.post("/docs/delete")
async def dept_delete(id:int,current_user: dict = Depends(get_current_user)):
    conn = get_conn()
    cursor = conn.cursor()
    try:

        srv = RagService()
        srv.delete(id)

        return {"status":"success","message":"删除成功。","data":{}}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"删除失败，{str(e)}", "data": {}}

@app.post("/docs/in")
async def docs_update(data:dict[str,Any],current_user: dict = Depends(get_current_user)):
    """向量入库"""
    conn = get_conn()
    cursor = conn.cursor()
    try:
        id = data.get('id')
        srv = RagService()
        srv.add_document(id)
        return {"status":"success","message":"入库成功。","data":{}}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"入库失败，{str(e)}", "data": {}}

@app.post("/docs/out")
async def docs_update(data:dict[str,Any],current_user: dict = Depends(get_current_user)):
    """向量入库"""
    conn = get_conn()
    cursor = conn.cursor()
    try:
        id = data.get('id')
        srv = RagService()
        srv.remove(id)
        return {"status":"success","message":"出库成功。","data":{}}
    except Exception as e:
        cursor.close()
        conn.close()
        return {"status": "error", "message": f"出库失败，{str(e)}", "data": {}}