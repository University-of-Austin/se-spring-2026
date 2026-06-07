"""created_at is schema-defaulted (DEFAULT (strftime(...))). If that clause
is ever dropped, INSERTs that omit created_at will fail at runtime rather
than at import — this test catches that regression.
"""
import re

from sqlalchemy import text

import db
from repositories import posts as posts_repo
from repositories import users as users_repo

# created_at is second-precision (SQLite strftime default); updated_at is
# microsecond-precision (Python-generated) to keep weak ETags advancing even on
# same-second edits. Accept both shapes.
UTC_Z_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")


def test_users_created_at_is_utc_z_iso():
    user = users_repo.create("alice")
    assert UTC_Z_ISO.match(user["created_at"]), user["created_at"]


def test_posts_created_at_is_utc_z_iso():
    alice = users_repo.create("alice")
    post = posts_repo.create(alice["id"], "hello")
    assert UTC_Z_ISO.match(post["created_at"]), post["created_at"]


def test_users_default_applies_when_created_at_omitted():
    """Direct SQL INSERT without created_at must still produce a timestamp."""
    with db.engine.begin() as conn:
        conn.execute(text("INSERT INTO users (username) VALUES ('direct')"))
        row = conn.execute(text("SELECT created_at FROM users WHERE username = 'direct'")).fetchone()
    assert row is not None
    assert UTC_Z_ISO.match(row.created_at), row.created_at


def test_posts_updated_at_nullable_until_patched():
    alice = users_repo.create("alice")
    post = posts_repo.create(alice["id"], "fresh")
    assert post["updated_at"] is None


def test_posts_updated_at_populated_after_update():
    alice = users_repo.create("alice")
    post = posts_repo.create(alice["id"], "fresh")
    updated = posts_repo.update_message(post["id"], "edited")
    assert updated is not None
    assert UTC_Z_ISO.match(updated["updated_at"]), updated["updated_at"]
