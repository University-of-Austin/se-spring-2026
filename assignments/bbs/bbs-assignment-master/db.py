"""
db.py - Database module for BBS SQLite backend.
Exports: engine, init_db()
"""

from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///bbs.db")


def init_db():
    """Create tables if they don't already exist."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT    UNIQUE NOT NULL,
                bio        TEXT    NOT NULL DEFAULT '',
                created_at TEXT    NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                message    TEXT    NOT NULL,
                timestamp  TEXT    NOT NULL,
                parent_id  INTEGER REFERENCES posts(id)
            )
        """))
