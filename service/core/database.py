"""数据库操作"""
import sqlite3
import os

from utils.hash import get_password_hash
from core.config import conf
from utils.file import get_abs_path
DB_PATH = get_abs_path(conf['db']['dir'])
DB_FILE = os.path.join(DB_PATH, "sqlite3.db")

os.makedirs(DB_PATH, exist_ok=True)


def get_chat():
    return os.path.join(DB_PATH, "chat.db")


def get_conn():
    conn = sqlite3.connect(DB_FILE,check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init():
    """初始化所有表"""
    db = get_conn()
    cursor = db.cursor()

    # 开启外键
    cursor.execute("PRAGMA foreign_keys = ON")

    #用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE,
        hashed_password TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        role TEXT NOT NULL CHECK(role IN('admin','user')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP,
        last_login_ip TEXT
    )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS depts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_dept(
        user_id INTEGER NOT NULL,
        dept_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (dept_id) REFERENCES depts(id) ON DELETE CASCADE
    )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        dept_id INTEGER,
        type TEXT NOT NULL CHECK(type IN('dept','personal')),
        name TEXT NOT NULL,
        size INTEGER NOT NULL,
        path TEXT NOT NULL,
        hash TEXT NOT NULL,
        status INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (dept_id) REFERENCES depts(id) ON DELETE CASCADE
    )
    """)
    hashed_password = get_password_hash("123456")
    cursor.execute("""INSERT INTO users(username,email,hashed_password,is_active,role)VALUES('admin','lastbit@163.com',?,1,'admin')""",(hashed_password,))
    cursor.execute("""INSERT INTO depts(name)VALUES('IT')""")
    cursor.execute("""INSERT INTO user_dept(user_id,dept_id)VALUES(1,1)""")
    #cursor.execute("""INSERT INTO documents(user_id,type,name,size,path,hash,status)VALUES(1,'personal','扫地机器人100问.pdf',12,'data/upload/扫地机器人100问.pdf','123',0)""")
    db.commit()
    cursor.close()
    db.close()


if __name__ == '__main__':
    init()