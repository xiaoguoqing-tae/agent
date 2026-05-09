"""鉴权、身份验证、token 管理"""
from datetime import timedelta, datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from core.config import conf
from core.data import get_user

try:
    import redis
except Exception:  # pragma: no cover
    redis = None

SECRET_KEY = conf["secret_key"]
ALGORITHM = conf["algorithm"]
ACCESS_TOKEN_EXPIRE_MINUTES = conf["access_token_expire_minutes"]
REDIS_CONF = conf.get("redis", {})

# 自动拿到 token，可直接用于 Depends
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
_redis_client = None


def get_redis_client():
    """返回 Redis 客户端；未启用或依赖缺失时返回 None。"""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if not REDIS_CONF.get("enabled", False):
        return None
    if redis is None:
        return None

    _redis_client = redis.Redis(
        host=REDIS_CONF.get("host", "127.0.0.1"),
        port=int(REDIS_CONF.get("port", 6379)),
        db=int(REDIS_CONF.get("db", 0)),
        password=REDIS_CONF.get("password") or None,
        decode_responses=True,
        socket_timeout=float(REDIS_CONF.get("socket_timeout", 2)),
        socket_connect_timeout=float(REDIS_CONF.get("socket_connect_timeout", 2)),
    )
    return _redis_client


def _token_blacklist_key(token: str) -> str:
    return f"auth:blacklist:{token}"


def _seconds_until_exp(exp_ts: int) -> int:
    now_ts = int(datetime.now(timezone.utc).timestamp())
    ttl = exp_ts - now_ts
    return ttl if ttl > 0 else 1


def revoke_token(token: str, exp_ts: int):
    """将 token 加入黑名单，TTL 到 token 过期。"""
    rds = get_redis_client()
    if not rds:
        return
    rds.setex(_token_blacklist_key(token), _seconds_until_exp(exp_ts), "1")


def revoke_token_by_jwt(token: str):
    """解析 JWT 的过期时间，并将当前 token 加入黑名单。"""
    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"verify_exp": False},
    )
    exp_ts = payload.get("exp")
    if exp_ts is None:
        raise ValueError("token 缺少 exp，无法加入黑名单")
    revoke_token(token, int(exp_ts))


def is_token_revoked(token: str) -> bool:
    """检查 token 是否在黑名单。"""
    rds = get_redis_client()
    if not rds:
        return False
    return bool(rds.exists(_token_blacklist_key(token)))




def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
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
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        if is_token_revoked(token):
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user(username)
    if user is None:
        raise credentials_exception

    return user


def auth(role: str, path: str):
    """鉴权"""
    user = [
        "/xxx/xx",
        "/bbb/bbb",
    ]
    admin = [
        "/zzz/dd",
    ]

    paths = {
        "admin": [*admin, *user],
        "user": user,
    }

    try:
        return path in paths[role]
    except KeyError:
        return False
