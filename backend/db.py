import psycopg
from contextlib import contextmanager

DB_CONFIG = {
    "dbname": "micro_volunteer",
    "user": "alexhsu",     # 或 macOS 使用者帳號
    "password": None,         # Homebrew PostgreSQL 預設沒有密碼
    "host": "localhost",
    "port": 5432
}

@contextmanager
def get_conn():
    conn = psycopg.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()