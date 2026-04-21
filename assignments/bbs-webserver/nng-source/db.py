"""
Database layer for the BBS webserver (Assignment 2, extended with auth).

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

Auth additions (Gold, beyond the A2 spec):
- `users.password_hash` stores a scrypt-hashed password ("salt$hash" in hex).
- A `sessions` table holds opaque bearer tokens issued at login time.

Board additions (Gold, beyond the A2 spec):
- A `boards` table keyed by name (e.g. "general", "tech").
- `posts.board_id` FKs into `boards`. A default "general" board is seeded
  on startup so posts without an explicit board land there.
"""

from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///bbs.db")

DEFAULT_BOARD = "general"


def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                bio TEXT,
                password_hash TEXT
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
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                board_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (board_id) REFERENCES boards(id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        # Best-effort migrations for older databases. SQLite throws on
        # duplicate columns; swallow and continue.
        for stmt in (
            "ALTER TABLE users ADD COLUMN password_hash TEXT",
            "ALTER TABLE posts ADD COLUMN board_id INTEGER",
        ):
            try:
                conn.execute(text(stmt))
            except Exception:
                pass

        # Seed the default board.
        conn.execute(
            text(
                "INSERT OR IGNORE INTO boards (name, created_at) "
                "VALUES (:n, strftime('%Y-%m-%dT%H:%M:%S', 'now'))"
            ),
            {"n": DEFAULT_BOARD},
        )

        # Back-fill any legacy posts that pre-date the board_id column by
        # pointing them at the default board.
        default_id = conn.execute(
            text("SELECT id FROM boards WHERE name = :n"), {"n": DEFAULT_BOARD}
        ).scalar_one()
        conn.execute(
            text("UPDATE posts SET board_id = :b WHERE board_id IS NULL"),
            {"b": default_id},
        )
