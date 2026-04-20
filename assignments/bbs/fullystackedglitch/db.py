from pathlib import Path
from sqlalchemy import create_engine, text

_db_path = Path(__file__).parent / "bbs.db"
engine = create_engine(f"sqlite:///{_db_path}")


def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    UNIQUE NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL REFERENCES users(id),
                message   TEXT    NOT NULL,
                timestamp TEXT    NOT NULL,
                parent_id INTEGER REFERENCES posts(id)
            )
        """))
