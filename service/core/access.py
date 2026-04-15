"""鉴权、身份验证、密码生成等"""
from datetime import timedelta,datetime,timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import HTTPException, Depends, status
from core.data import get_user
from core.config import conf
from utils.hash import verify_password
SECRET_KEY = conf["secret_key"]
ALGORITHM = conf["algorithm"]
ACCESS_TOKEN_EXPIRE_MINUTES = conf["access_token_expire_minutes"]

# --- 安全工具 ---

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



def create_access_token(data:dict, expires_delta:Optional[timedelta] = None):
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """验证token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 1. 解析 Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # 2. 查询用户是否存在 (可选，为了双重保险)
    user = get_user(username)
    if user is None:
        raise credentials_exception

    # 3. 返回用户信息，供接口使用
    return user


def auth(role:str,path:str):
    """鉴权"""
    user = [
        "/xxx/xx",
        "/bbb/bbb"
    ]
    admin = [
        "/zzz/dd"
    ]

    #admin拥有user角色所有权限
    paths = {
        "admin":[*admin,*user],
        "user":user
    }

    try:
        if path in paths[role]:
            return True
        else:
            return False
    except KeyError:
        return False
