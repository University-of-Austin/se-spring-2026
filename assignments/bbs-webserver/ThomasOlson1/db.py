import os
from sqlalchemy import create_engine, text

DB_URL = os.environ.get("BBS_DB_URL", "sqlite:///bbs.db")
engine = create_engine(DB_URL, future=True)


def init_db():
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    join_date TEXT NOT NULL,
                    post_count INTEGER NOT NULL DEFAULT 0,
                    bio TEXT NOT NULL DEFAULT ''
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS boards (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    board_id INTEGER NOT NULL,
                    board_post_id INTEGER NOT NULL,
                    parent_id INTEGER,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    upvotes INTEGER NOT NULL DEFAULT 0,
                    downvotes INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(board_id) REFERENCES boards(id),
                    FOREIGN KEY(parent_id) REFERENCES posts(id)
                )
                """
            )
        )
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_board_post_id "
                "ON posts (board_id, board_post_id)"
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS votes (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    post_id INTEGER NOT NULL,
                    vote_type TEXT NOT NULL CHECK(vote_type IN ('up', 'down')),
                    date TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(post_id) REFERENCES posts(id),
                    UNIQUE(user_id, post_id)
                )
                """
            )
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_votes_user_date ON votes (user_id, date)")
        )

        # A2 additive change #1: nullable updated_at on posts for silver PATCH.
        # SQLite has no ADD COLUMN IF NOT EXISTS, so probe table_info first.
        cols = [row[1] for row in conn.execute(text("PRAGMA table_info(posts)"))]
        if "updated_at" not in cols:
            conn.execute(text("ALTER TABLE posts ADD COLUMN updated_at TEXT"))

        # A2 additive change #2: seed a default 'general' board so POST /posts
        # (which has no board field in the A2 API) has somewhere to land.
        conn.execute(text("INSERT OR IGNORE INTO boards (name) VALUES ('general')"))


def default_board_id() -> int:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM boards WHERE name = 'general'")
        ).first()
        if row is None:
            raise RuntimeError("default 'general' board missing; did init_db run?")
        return row[0]
