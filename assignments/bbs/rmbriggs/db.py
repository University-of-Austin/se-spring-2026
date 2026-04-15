from sqlalchemy import create_engine, text
from pathlib import Path

DB_PATH = Path(__file__).parent / "bbs.db"
engine = create_engine(f"sqlite:///{DB_PATH}")


def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                parent_id INTEGER REFERENCES posts(id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS direct_messages (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id    INTEGER NOT NULL REFERENCES users(id),
                recipient_id INTEGER NOT NULL REFERENCES users(id),
                message      TEXT NOT NULL,
                timestamp    TEXT NOT NULL,
                read_at      TEXT
            )
        """))
