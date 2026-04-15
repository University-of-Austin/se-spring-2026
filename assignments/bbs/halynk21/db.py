"""
db.py — Shared SQLAlchemy engine and schema initialisation.

Exports:
  engine    — the single SQLAlchemy engine for bbs.db
  init_db() — creates every table (idempotent via CREATE TABLE IF NOT EXISTS)

Schema design rationale
───────────────────────
users       One row per unique username.  bio + created_at support profiles.
boards      Named discussion areas (e.g. "general", "python").  A default
            "general" board is seeded on first run.
posts       Core content table.  board_id links a post to its board;
            parent_id (self-referential FK) enables threaded replies.
            Storing timestamps as ISO-8601 TEXT lets SQLite's LIKE/ORDER
            work correctly while remaining human-readable.
reactions   One row per (post, user, reaction) triple, with a UNIQUE
            constraint to prevent duplicate reactions from the same user.
private_messages  Sender → recipient direct messages; read_at is NULL
            until the recipient views the message.
mentions    One row per (@username, post) pair; notified flips to 1 on
            the mentioned user's next login.
subscriptions  One row per (user, board) pair; last_digest_at tracks the
            cutoff timestamp for the digest command.
"""

from datetime import datetime
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///bbs.db", echo=False)


def init_db() -> None:
    """Create all tables if they do not already exist."""
    with engine.connect() as conn:

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT    UNIQUE NOT NULL,
                bio        TEXT    DEFAULT '',
                created_at TEXT    NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS boards (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    UNIQUE NOT NULL,
                description TEXT    DEFAULT '',
                created_at  TEXT    NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL REFERENCES users(id),
                board_id  INTEGER REFERENCES boards(id),
                parent_id INTEGER REFERENCES posts(id),
                message   TEXT    NOT NULL,
                timestamp TEXT    NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reactions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id    INTEGER NOT NULL REFERENCES posts(id),
                user_id    INTEGER NOT NULL REFERENCES users(id),
                reaction   TEXT    NOT NULL,
                created_at TEXT    NOT NULL,
                UNIQUE(post_id, user_id, reaction)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS private_messages (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id    INTEGER NOT NULL REFERENCES users(id),
                recipient_id INTEGER NOT NULL REFERENCES users(id),
                message      TEXT    NOT NULL,
                timestamp    TEXT    NOT NULL,
                read_at      TEXT
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mentions (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id             INTEGER NOT NULL REFERENCES posts(id),
                mentioned_user_id   INTEGER NOT NULL REFERENCES users(id),
                notified            INTEGER NOT NULL DEFAULT 0,
                UNIQUE(post_id, mentioned_user_id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL REFERENCES users(id),
                board_id       INTEGER NOT NULL REFERENCES boards(id),
                created_at     TEXT    NOT NULL,
                last_digest_at TEXT,
                UNIQUE(user_id, board_id)
            )
        """))

        # Seed the default board (INSERT OR IGNORE is idempotent)
        conn.execute(
            text("""
                INSERT OR IGNORE INTO boards (name, description, created_at)
                VALUES ('general', 'General discussion', :ts)
            """),
            {"ts": datetime.now().isoformat(timespec="seconds")},
        )

        # Indexes for common query patterns
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_message   ON posts(message)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_user_id   ON posts(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_board_id  ON posts(board_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_timestamp ON posts(timestamp)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_parent_id ON posts(parent_id)"))

        # Add new columns to existing databases (idempotent)
        for stmt in [
            "ALTER TABLE posts ADD COLUMN edited_at TEXT",
            "ALTER TABLE posts ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN is_mod   INTEGER NOT NULL DEFAULT 0",
        ]:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass  # Column already exists

        conn.commit()


def init_econ() -> None:
    """Create economy tables and add wallet columns to users (idempotent)."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inventory (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL REFERENCES users(id),
                fish_type TEXT    NOT NULL,
                quantity  INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, fish_type)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS econ_log (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES users(id),
                action        TEXT    NOT NULL,
                detail        TEXT,
                amount        INTEGER NOT NULL,
                balance_after INTEGER NOT NULL,
                timestamp     TEXT    NOT NULL
            )
        """))
        for stmt in [
            "ALTER TABLE users ADD COLUMN balance      INTEGER DEFAULT 100",
            "ALTER TABLE users ADD COLUMN total_earned INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN total_lost   INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN peak_balance INTEGER DEFAULT 100",
        ]:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
        conn.commit()
