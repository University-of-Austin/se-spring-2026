"""Shared fixtures: in-memory SQLite engine with schema, plus a TestClient.

Every production module reaches the engine through `db.engine` rather than
capturing it at import time (`from db import engine`). That means one
`monkeypatch.setattr(db, "engine", _test_engine)` redirects the whole app
to the in-memory test engine. Autouse so no test can accidentally reach
for bbs.db.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session")
def _test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _pragma(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")
        cur.close()

    return engine


@pytest.fixture(autouse=True)
def _swap_engine(monkeypatch, _test_engine):
    """Point `db.engine` at the in-memory test engine for every test."""
    import db

    # The convention across the codebase is `import db; db.engine.X()` so
    # that this single patch redirects every caller.
    monkeypatch.setattr(db, "engine", _test_engine)

    _reset_schema(_test_engine)
    yield


def _reset_schema(engine) -> None:
    """Drop and recreate every table so each test starts clean.

    Mirrors db.init_db() — if the production schema grows another table,
    trigger, or index, add it here too.
    """
    with engine.begin() as conn:
        # Triggers reference posts_fts; drop them before dropping the table.
        for trig in ("posts_ai", "posts_ad", "posts_au"):
            conn.execute(text(f"DROP TRIGGER IF EXISTS {trig}"))
        conn.execute(text("DROP TABLE IF EXISTS posts_fts"))
        conn.execute(text("DROP TABLE IF EXISTS reactions"))
        conn.execute(text("DROP TABLE IF EXISTS idempotency_keys"))
        conn.execute(text("DROP TABLE IF EXISTS posts"))
        conn.execute(text("DROP TABLE IF EXISTS users"))
        conn.execute(text("""
            CREATE TABLE users (
                id         INTEGER PRIMARY KEY,
                username   TEXT NOT NULL COLLATE NOCASE,
                bio        TEXT,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                UNIQUE (username)
            )
        """))
        conn.execute(text("""
            CREATE TABLE posts (
                id         INTEGER PRIMARY KEY,
                user_id    INTEGER NOT NULL REFERENCES users(id),
                parent_id  INTEGER REFERENCES posts(id) ON DELETE CASCADE,
                message    TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                updated_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE reactions (
                user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                post_id    INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                kind       TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                PRIMARY KEY (user_id, post_id, kind)
            )
        """))
        conn.execute(text("""
            CREATE TABLE idempotency_keys (
                user_id       INTEGER NOT NULL REFERENCES users(id),
                key           TEXT    NOT NULL,
                body_hash     TEXT    NOT NULL,
                response_json TEXT    NOT NULL,
                created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                PRIMARY KEY (user_id, key)
            )
        """))
        conn.execute(text("""
            CREATE VIRTUAL TABLE posts_fts USING fts5(
                message, content='posts', content_rowid='id'
            )
        """))
        conn.execute(text("""
            CREATE TRIGGER posts_ai AFTER INSERT ON posts BEGIN
                INSERT INTO posts_fts(rowid, message) VALUES (new.id, new.message);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER posts_ad AFTER DELETE ON posts BEGIN
                INSERT INTO posts_fts(posts_fts, rowid, message)
                VALUES ('delete', old.id, old.message);
            END
        """))
        conn.execute(text("""
            CREATE TRIGGER posts_au AFTER UPDATE ON posts BEGIN
                INSERT INTO posts_fts(posts_fts, rowid, message)
                VALUES ('delete', old.id, old.message);
                INSERT INTO posts_fts(rowid, message) VALUES (new.id, new.message);
            END
        """))


@pytest.fixture
def client(_test_engine):
    """FastAPI TestClient backed by the in-memory engine.

    Imports main lazily so the autouse engine swap is in effect first.
    """
    from fastapi.testclient import TestClient
    import main

    with TestClient(main.app) as c:
        yield c
