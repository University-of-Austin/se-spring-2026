"""
db.py — SQLAlchemy engine and schema initialisation for the BBS webserver.

Exports:
  engine    — the single SQLAlchemy engine for bbs.db
  init_db() — creates the users, posts, and reactions tables (idempotent)

Schema design rationale
───────────────────────
users   One row per unique username.  bio + created_at support profiles.
        Identical column set to A1's users table.
posts   Core content table.  Slim subset of A1's posts — drops board_id,
        parent_id, and pinned (unused by the REST API).  timestamp stays as
        the physical column name; SELECT aliases it AS created_at in every
        handler so the API surface uses consistent naming.  edited_at is
        aliased AS updated_at similarly.  ISO-8601 TEXT timestamps let
        SQLite's ORDER BY work correctly while remaining human-readable.

Note: this db.py is a slimmed copy of A1's assignments/bbs/halynk21/db.py.
No init_econ(), no get_or_create_user(), no boards/mentions/
private_messages/subscriptions.  Reactions are added fresh (see schema
below and README Design Decision #8).  The webserver owns its own bbs.db
(created relative to the process's cwd when uvicorn starts in this directory).
"""

from sqlalchemy import create_engine, event, text

# ── Engine ──────────────────────────────────────────────────────────────────
engine = create_engine("sqlite:///bbs.db", echo=False)


@event.listens_for(engine, "connect")
def _fk_pragma_on_connect(dbapi_conn, _):
    """Enable FK enforcement (including CASCADE) on every pooled connection."""
    dbapi_conn.execute("PRAGMA foreign_keys=ON")


# ── Schema init ─────────────────────────────────────────────────────────────
def init_db() -> None:
    """Create all tables if they do not already exist (idempotent)."""
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
            CREATE TABLE IF NOT EXISTS posts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL REFERENCES users(id),
                message   TEXT    NOT NULL,
                timestamp TEXT    NOT NULL,
                edited_at TEXT
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reactions (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                kind       TEXT    NOT NULL,
                created_at TEXT    NOT NULL,
                UNIQUE(user_id, post_id, kind)
            )
        """))

        # Indexes for common query patterns
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_user_id   ON posts(user_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_timestamp ON posts(timestamp)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_posts_message   ON posts(message)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reactions_post_id ON reactions(post_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_reactions_user_id ON reactions(user_id)"))

        conn.commit()
