"""操作数据库数据"""
from core.database import get_conn


def get_departments():
    """获取部门数据"""
    conn = get_conn()
    res = conn.execute("""SELECT * FROM depts ORDER BY id""").fetchall()
    conn.close()
    return res

def get_departments_name(id):
    """获取部门名称"""
    conn = get_conn()
    res = conn.execute("""SELECT * FROM depts WHERE id = ?""", (id,)).fetchone()
    conn.close()
    if res is None:
        return ""
    return res['name']

def get_auth_departments(user_id):
    """获取授权部门"""
    conn = get_conn()
    res = conn.execute("""SELECT * FROM depts WHERE id IN(SELECT department_id FROM user_department WHERE user_id=?)""",(user_id,)).fetchall()
    conn.close()
    if res is None:
        return []
    return res

def get_auth_departments_ids(user_id):
    """获取授权部门的ID"""
    departments = get_auth_departments(user_id)

    res = []
    for dep in departments:
        res.append(dep['id'])
    return res

def get_user(username:str):
    """获取用户信息"""
    conn = get_conn()
    user = conn.execute("""SELECT * FROM users WHERE username = ?""", (username,)).fetchone()
    conn.close()
    return user
