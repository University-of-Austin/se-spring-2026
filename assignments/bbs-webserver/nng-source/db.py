"""
Database layer for the BBS webserver (Assignment 2).

Changes from A1's db.py:
- Renamed the user's timestamp column from `joined` to `created_at` to
  match the API response shape.
- Added an `updated_at` column on posts for the Silver PATCH /posts/{id}
  feature.
- Dropped the boards / reply_to columns - this assignment doesn't need
  them, and the API spec doesn't expose them.
- Auto-create-user behavior is NOT in this file. The A1 CLI created
  users on first post; A2 rejects posts from unknown users with 404,
  so user creation only happens via POST /users in main.py.
"""

from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///bbs.db")


def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                bio TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
