from pathlib import Path

from app_paths import ensure_data_dir, get_db_path
from sqlalchemy import create_engine, event, text


_engine = None
_engine_path: Path | None = None
_initialized_paths: set[Path] = set()


def _database_path() -> Path:
    return get_db_path()


def get_engine():
    global _engine, _engine_path

    database_path = _database_path()
    if _engine is not None and _engine_path == database_path:
        return _engine

    if _engine is not None:
        _engine.dispose()

    _engine = create_engine(f"sqlite:///{database_path}")
    event.listen(_engine, "connect", _enable_sqlite_foreign_keys)
    _engine_path = database_path
    return _engine


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
    finally:
        cursor.close()


class _EngineProxy:
    def __getattr__(self, name):
        return getattr(get_engine(), name)


engine = _EngineProxy()


def init_db() -> None:
    database_path = _database_path()
    ensure_data_dir()
    if database_path in _initialized_paths:
        return

    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            joined_at TEXT NOT NULL,
            bio TEXT NOT NULL DEFAULT '',
            pin TEXT NOT NULL DEFAULT '',
            pin_hash TEXT NOT NULL DEFAULT '',
            pin_needs_reset INTEGER NOT NULL DEFAULT 1
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS boards (
            id INTEGER PRIMARY KEY,
            slug TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            board_id INTEGER NOT NULL,
            parent_post_id INTEGER,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (board_id) REFERENCES boards(id),
            FOREIGN KEY (parent_post_id) REFERENCES posts(id)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_posts_timestamp ON posts(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_posts_board_timestamp ON posts(board_id, timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_posts_user_timestamp ON posts(user_id, timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_posts_parent ON posts(parent_post_id)",
        """
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL UNIQUE,
            hash TEXT NOT NULL,
            original_name TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_attachments_post ON attachments(post_id)",
    ]
    with get_engine().begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        columns = [
            row[1]
            for row in connection.execute(text("PRAGMA table_info(users)"))
        ]
        if "pin" not in columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN pin TEXT NOT NULL DEFAULT ''")
            )
        if "pin_hash" not in columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN pin_hash TEXT NOT NULL DEFAULT ''")
            )
        if "pin_needs_reset" not in columns:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN pin_needs_reset INTEGER NOT NULL DEFAULT 1")
            )
        connection.execute(
            text(
                """
                UPDATE users
                SET pin_needs_reset = CASE
                    WHEN TRIM(COALESCE(pin_hash, '')) != '' THEN 0
                    WHEN TRIM(COALESCE(pin, '')) != '' THEN 0
                    ELSE 1
                END
                """
            )
        )
    _initialized_paths.add(database_path)
