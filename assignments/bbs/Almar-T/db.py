"""
Database module for the BBS.

Exports the SQLAlchemy engine and an init_db() function that creates
all tables if they don't already exist.

Schema:
  users     - id, username (unique), bio, created_at
  posts     - id, user_id (FK), message, timestamp, parent_id (FK self-ref for threads)
  messages  - id, sender_id (FK), recipient_id (FK), message, timestamp, read (bool)
  reactions - id, post_id (FK), user_id (FK), emoji (unique per user+post+emoji)
"""

import os
from sqlalchemy import create_engine, text

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bbs.db")
engine = create_engine(f"sqlite:///{DB_PATH}")


def init_db():
    """Create all tables if they don't exist."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                bio TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                parent_id INTEGER DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id),
                FOREIGN KEY (parent_id) REFERENCES posts (id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                read INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (sender_id) REFERENCES users (id),
                FOREIGN KEY (recipient_id) REFERENCES users (id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts (id),
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE (post_id, user_id, emoji)
            )
        """))
        conn.commit()
