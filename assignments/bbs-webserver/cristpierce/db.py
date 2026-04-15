"""Database engine and schema initialization for the BBS Webserver API.

Exports:
    engine  - SQLAlchemy engine connected to bbs.db
    init_db - creates all tables idempotently
"""

from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///bbs.db")


def init_db():
    """Create all tables if they don't already exist."""
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                bio TEXT DEFAULT NULL,
                created_at TEXT NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                message TEXT NOT NULL,
                board TEXT DEFAULT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT DEFAULT NULL,
                FOREIGN KEY (username) REFERENCES users(username)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                kind TEXT NOT NULL,
                UNIQUE(post_id, username),
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (username) REFERENCES users(username)
            )
        """))
