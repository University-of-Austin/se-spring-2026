"""db.py - SQLite backend for the BBS webserver (Assignment 2).

Exports: engine, init_db()

Schema differences from A1:
  - posts.timestamp renamed to posts.created_at to match the API field name
  - posts.updated_at added (nullable) for PATCH /posts/{id}
  - posts.parent_id removed (A1's threading is unused in A2)
  - reactions table added (gold tier association table)

The database auto-create-user behavior from A1 has been removed. POST /posts
now returns 404 when the poster does not already exist; users must be
created explicitly via POST /users.
"""

from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///bbs.db")


def init_db():
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))
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
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                message    TEXT    NOT NULL,
                created_at TEXT    NOT NULL,
                updated_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reactions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                kind       TEXT    NOT NULL,
                created_at TEXT    NOT NULL,
                UNIQUE (post_id, user_id, kind)
            )
        """))
