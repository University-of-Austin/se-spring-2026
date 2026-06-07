from pathlib import Path

from sqlalchemy import create_engine, event, text

DB_PATH = Path(__file__).with_name("bbs.db")
engine = create_engine(f"sqlite:///{DB_PATH}")


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY,
                username   TEXT NOT NULL COLLATE NOCASE,
                bio        TEXT,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                UNIQUE (username)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id         INTEGER PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                parent_id  INTEGER REFERENCES posts(id) ON DELETE CASCADE,
                message    TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                updated_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reactions (
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                kind       TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                PRIMARY KEY (user_id, post_id, kind)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                user_id       INTEGER NOT NULL REFERENCES users(id),
                key           TEXT    NOT NULL,
                body_hash     TEXT    NOT NULL,
                response_json TEXT    NOT NULL,
                created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                PRIMARY KEY (user_id, key)
            )
        """))

        # FTS5 external-content index over posts.message. `content='posts'` tells
        # FTS5 to read the source text from the posts table on demand instead of
        # duplicating it — the virtual table stores only the inverted index.
        # Triggers below keep the index in sync on INSERT / DELETE / UPDATE.
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS posts_fts USING fts5(
                message, content='posts', content_rowid='id'
            )
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS posts_ai AFTER INSERT ON posts BEGIN
                INSERT INTO posts_fts(rowid, message) VALUES (new.id, new.message);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS posts_ad AFTER DELETE ON posts BEGIN
                INSERT INTO posts_fts(posts_fts, rowid, message)
                VALUES ('delete', old.id, old.message);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS posts_au AFTER UPDATE ON posts BEGIN
                INSERT INTO posts_fts(posts_fts, rowid, message)
                VALUES ('delete', old.id, old.message);
                INSERT INTO posts_fts(rowid, message) VALUES (new.id, new.message);
            END
        """))
