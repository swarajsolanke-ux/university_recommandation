import sqlite3
from config import settings

def get_db():
    conn = sqlite3.connect(settings.DATABASE_NAME, check_same_thread=False,timeout=10)
    try:
        conn.row_factory = sqlite3.Row
        print(f"db connection sucessful created")
        yield conn
    except Exception as e:
        print(f"db connection error: {e}")
        raise e
    finally:
        conn.close()
