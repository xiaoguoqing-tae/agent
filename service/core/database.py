"""Database access based on SQLAlchemy and MySQL."""
from __future__ import annotations

import re
from typing import Any, Iterable

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, Result
from sqlalchemy.engine.url import URL

from core.config import conf
from utils.hash import get_password_hash


def _build_database_url() -> str:
    db_conf = conf.get("db", {})
    database_url = db_conf.get("url")
    if database_url:
        return database_url

    return URL.create(
        "mysql+pymysql",
        username=db_conf.get("user", "root"),
        password=db_conf.get("password", "root"),
        host=db_conf.get("host", "127.0.0.1"),
        port=int(db_conf.get("port", 3306)),
        database=db_conf.get("database", "chain"),
        query={"charset": db_conf.get("charset", "utf8mb4")},
    ).render_as_string(hide_password=False)


engine: Engine = create_engine(
    _build_database_url(),
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
)


class Cursor:
    def __init__(self, conn: Connection):
        self.conn = conn
        self._result: Result | None = None
        self.lastrowid: int | None = None

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> "Cursor":
        sql_text, bound_params = _convert_qmark_params(sql, params)
        self._result = self.conn.execute(text(sql_text), bound_params)
        self.lastrowid = getattr(self._result, "lastrowid", None)
        return self

    def fetchone(self) -> dict[str, Any] | None:
        if self._result is None:
            return None
        row = self._result.fetchone()
        return dict(row._mapping) if row else None

    def fetchall(self) -> list[dict[str, Any]]:
        if self._result is None:
            return []
        return [dict(row._mapping) for row in self._result.fetchall()]

    def close(self) -> None:
        if self._result is not None:
            self._result.close()
            self._result = None


class DatabaseConnection:
    def __init__(self):
        self.conn = engine.connect()
        self.trans = self.conn.begin()

    def cursor(self) -> Cursor:
        return Cursor(self.conn)

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> Cursor:
        cursor = self.cursor()
        return cursor.execute(sql, params)

    def commit(self) -> None:
        self.trans.commit()
        self.trans = self.conn.begin()

    def rollback(self) -> None:
        self.trans.rollback()
        self.trans = self.conn.begin()

    def close(self) -> None:
        if self.trans.is_active:
            self.trans.rollback()
        self.conn.close()


def _convert_qmark_params(sql: str, params: Iterable[Any] | None = None) -> tuple[str, dict[str, Any]]:
    if params is None:
        return sql, {}

    values = list(params)
    index = 0
    bound_params: dict[str, Any] = {}

    def replace(_: re.Match[str]) -> str:
        nonlocal index
        key = f"p{index}"
        bound_params[key] = values[index]
        index += 1
        return f":{key}"

    converted_sql = re.sub(r"\?", replace, sql)
    if index != len(values):
        raise ValueError("SQL parameter count does not match placeholder count")
    return converted_sql, bound_params


def get_chat() -> str:
    checkpoint_url = conf.get("db", {}).get("checkpoint_url")
    if checkpoint_url:
        return checkpoint_url

    database_url = _build_database_url()
    if database_url.startswith("mysql+pymysql://"):
        return database_url.replace("mysql+pymysql://", "mysql+aiomysql://", 1)
    return database_url


def get_conn() -> DatabaseConnection:
    return DatabaseConnection()


def init() -> None:
    """Create all business tables in MySQL."""
    db = get_conn()
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE,
                hashed_password VARCHAR(255) NOT NULL,
                is_active TINYINT DEFAULT 1,
                role VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP NULL,
                last_login_ip VARCHAR(64),
                CONSTRAINT ck_users_role CHECK (role IN ('admin', 'user'))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS depts (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_dept (
                user_id BIGINT NOT NULL,
                dept_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, dept_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (dept_id) REFERENCES depts(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                user_id BIGINT NOT NULL,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                user_id BIGINT NOT NULL,
                dept_id BIGINT,
                type VARCHAR(20) NOT NULL,
                name VARCHAR(255) NOT NULL,
                size BIGINT NOT NULL,
                path VARCHAR(500) NOT NULL,
                hash VARCHAR(64) NOT NULL,
                status INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT ck_documents_type CHECK (type IN ('dept', 'personal')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (dept_id) REFERENCES depts(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        hashed_password = get_password_hash("123456")
        cursor.execute(
            """
            INSERT INTO users(username, email, hashed_password, is_active, role)
            VALUES('admin', 'lastbit@163.com', ?, 1, 'admin')
            ON DUPLICATE KEY UPDATE username = username
            """,
            (hashed_password,),
        )
        cursor.execute(
            """
            INSERT INTO depts(name)
            VALUES('IT')
            ON DUPLICATE KEY UPDATE name = name
            """
        )
        cursor.execute(
            """
            INSERT IGNORE INTO user_dept(user_id, dept_id)
            SELECT u.id, d.id FROM users u, depts d
            WHERE u.username = 'admin' AND d.name = 'IT'
            """
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()
        db.close()


if __name__ == "__main__":
    init()
