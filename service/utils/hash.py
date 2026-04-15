from passlib.context import CryptContext


# --- 安全工具 ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password:str)->str:
    """获取密码哈希"""
    return pwd_context.hash(password)

def verify_password(plain_password:str, hashed_password:str)->bool:
    """密码验证"""
    return pwd_context.verify(plain_password, hashed_password)


if __name__ == '__main__':
    print(get_password_hash("123456"))