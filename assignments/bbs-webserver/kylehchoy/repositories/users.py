from typing import Optional

from sqlalchemy import text

import db

_USER_SELECT = """
    SELECT u.id, u.username, u.bio, u.created_at,
           (SELECT COUNT(*) FROM posts WHERE user_id = u.id) AS post_count
    FROM users u
"""


def _row_to_dict(row) -> Optional[dict]:
    if row is None:
        return None
    return {
        "id": row.id,
        "username": row.username,
        "bio": row.bio,
        "created_at": row.created_at,
        "post_count": row.post_count,
    }


def create(username: str) -> dict:
    with db.engine.begin() as conn:
        conn.execute(
            text("INSERT INTO users (username) VALUES (:username)"),
            {"username": username},
        )
        row = conn.execute(
            text(_USER_SELECT + " WHERE u.username = :username"),
            {"username": username},
        ).fetchone()
    assert row is not None  # the row we just inserted must exist
    return _row_to_dict(row)  # type: ignore[return-value]


def get_by_username(username: str) -> Optional[dict]:
    with db.engine.connect() as conn:
        row = conn.execute(
            text(_USER_SELECT + " WHERE u.username = :username"),
            {"username": username},
        ).fetchone()
    return _row_to_dict(row)


def list_all(limit: int = 50, offset: int = 0) -> list[dict]:
    with db.engine.connect() as conn:
        rows = conn.execute(
            text(_USER_SELECT + " ORDER BY u.id ASC LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset},
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def exists_by_username(username: str) -> bool:
    with db.engine.connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM users WHERE username = :username LIMIT 1"),
            {"username": username},
        ).fetchone()
    return row is not None


def get_id_by_username(username: str) -> Optional[int]:
    """Minimal identity lookup for the auth dependency. Returns just the
    user's id — deliberately avoids the public read model (bio, post_count,
    created_at) so authenticated writes don't pay for a correlated COUNT(*)
    subquery on every request just to extract user_id."""
    with db.engine.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": username},
        ).fetchone()
    return row.id if row is not None else None


def update_bio(username: str, bio: Optional[str]) -> Optional[dict]:
    """UPDATE ... RETURNING collapses the 404-check, update, and read into one round-trip."""
    sql = """
        UPDATE users
           SET bio = :bio
         WHERE username = :username
     RETURNING id, username, bio, created_at,
               (SELECT COUNT(*) FROM posts WHERE user_id = users.id) AS post_count
    """
    with db.engine.begin() as conn:
        row = conn.execute(
            text(sql),
            {"bio": bio, "username": username},
        ).fetchone()
    return _row_to_dict(row)
