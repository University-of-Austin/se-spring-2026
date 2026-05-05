"""All SQL lives here. Route handlers never write SQL."""
from datetime import datetime, timezone
from sqlalchemy import text


class UserNotFound(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _user_row_to_out(conn, row) -> dict:
    """Convert a user row-mapping to the silver-shaped dict with post_count."""
    username = row["username"]
    count_row = conn.execute(
        text("SELECT COUNT(*) as cnt FROM posts WHERE user_id = :uid"),
        {"uid": row["id"]},
    ).mappings().fetchone()
    post_count = count_row["cnt"] if count_row else 0
    return {
        "username": username,
        "created_at": row["created_at"],
        "bio": row["bio"],
        "post_count": post_count,
    }


def create_user(conn, username: str, bio: str = "") -> dict:
    now = _now()
    result = conn.execute(
        text("INSERT INTO users (username, bio, created_at) VALUES (:username, :bio, :created_at)"),
        {"username": username, "bio": bio, "created_at": now},
    )
    row = conn.execute(
        text("SELECT id, username, bio, created_at FROM users WHERE id = :id"),
        {"id": result.lastrowid},
    ).mappings().fetchone()
    return _user_row_to_out(conn, row)


def get_user(conn, username: str) -> dict | None:
    row = conn.execute(
        text("SELECT id, username, bio, created_at FROM users WHERE username = :username"),
        {"username": username},
    ).mappings().fetchone()
    if row is None:
        return None
    return _user_row_to_out(conn, row)


def list_users(conn) -> list[dict]:
    rows = conn.execute(
        text("SELECT id, username, bio, created_at FROM users ORDER BY id ASC"),
    ).mappings().fetchall()
    return [_user_row_to_out(conn, r) for r in rows]


def user_exists(conn, username: str) -> bool:
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    ).mappings().fetchone()
    return row is not None


def update_user_bio(conn, username: str, bio: str) -> dict | None:
    row = conn.execute(
        text("SELECT id, username, bio, created_at FROM users WHERE username = :username"),
        {"username": username},
    ).mappings().fetchone()
    if row is None:
        return None
    conn.execute(
        text("UPDATE users SET bio = :bio WHERE username = :username"),
        {"bio": bio, "username": username},
    )
    updated = conn.execute(
        text("SELECT id, username, bio, created_at FROM users WHERE username = :username"),
        {"username": username},
    ).mappings().fetchone()
    return _user_row_to_out(conn, updated)


def post_count_for(conn, username: str) -> int:
    row = conn.execute(
        text("""
            SELECT COUNT(*) as cnt FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE u.username = :username
        """),
        {"username": username},
    ).mappings().fetchone()
    return row["cnt"] if row else 0


def create_post(conn, username: str, message: str) -> dict:
    if not user_exists(conn, username):
        raise UserNotFound(f"User '{username}' not found")
    now = _now()
    user_row = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    ).mappings().fetchone()
    result = conn.execute(
        text("""
            INSERT INTO posts (user_id, message, created_at, updated_at)
            VALUES (:user_id, :message, :created_at, :updated_at)
        """),
        {"user_id": user_row["id"], "message": message, "created_at": now, "updated_at": now},
    )
    row = conn.execute(
        text("""
            SELECT p.id, u.username, p.message, p.created_at, p.updated_at
            FROM posts p JOIN users u ON p.user_id = u.id
            WHERE p.id = :id
        """),
        {"id": result.lastrowid},
    ).mappings().fetchone()
    return dict(row)


def get_post(conn, post_id: int) -> dict | None:
    row = conn.execute(
        text("""
            SELECT p.id, u.username, p.message, p.created_at, p.updated_at
            FROM posts p JOIN users u ON p.user_id = u.id
            WHERE p.id = :id
        """),
        {"id": post_id},
    ).mappings().fetchone()
    if row is None:
        return None
    return dict(row)


def list_posts(conn, *, q=None, username=None, limit=50, offset=0, after_id=None) -> list[dict]:
    if after_id is not None:
        # Cursor-based path: WHERE id > after_id, offset ignored
        q_param = f"%{q}%" if q else None
        rows = conn.execute(
            text("""
                SELECT p.id, u.username, p.message, p.created_at, p.updated_at
                FROM posts p JOIN users u ON p.user_id = u.id
                WHERE p.id > :after_id
                AND (:username IS NULL OR u.username = :username)
                AND (:q IS NULL OR p.message LIKE :q)
                ORDER BY p.id ASC
                LIMIT :limit
            """),
            {"after_id": after_id, "username": username, "q": q_param, "limit": limit},
        ).mappings().fetchall()
    else:
        q_param = f"%{q}%" if q else None
        rows = conn.execute(
            text("""
                SELECT p.id, u.username, p.message, p.created_at, p.updated_at
                FROM posts p JOIN users u ON p.user_id = u.id
                WHERE (:username IS NULL OR u.username = :username)
                AND (:q IS NULL OR p.message LIKE :q)
                ORDER BY p.id ASC
                LIMIT :limit OFFSET :offset
            """),
            {"username": username, "q": q_param, "limit": limit, "offset": offset},
        ).mappings().fetchall()
    return [dict(r) for r in rows]


def delete_post(conn, post_id: int) -> bool:
    result = conn.execute(
        text("DELETE FROM posts WHERE id = :id"),
        {"id": post_id},
    )
    return result.rowcount > 0


def update_post_message(conn, post_id: int, new_message: str) -> dict | None:
    row = conn.execute(
        text("SELECT id FROM posts WHERE id = :id"),
        {"id": post_id},
    ).mappings().fetchone()
    if row is None:
        return None
    now = _now()
    conn.execute(
        text("UPDATE posts SET message = :message, updated_at = :updated_at WHERE id = :id"),
        {"message": new_message, "updated_at": now, "id": post_id},
    )
    updated = conn.execute(
        text("""
            SELECT p.id, u.username, p.message, p.created_at, p.updated_at
            FROM posts p JOIN users u ON p.user_id = u.id
            WHERE p.id = :id
        """),
        {"id": post_id},
    ).mappings().fetchone()
    return dict(updated)


def list_user_posts(conn, username: str) -> list[dict] | None:
    """Returns None if user doesn't exist; empty list if user has no posts."""
    if not user_exists(conn, username):
        return None
    rows = conn.execute(
        text("""
            SELECT p.id, u.username, p.message, p.created_at, p.updated_at
            FROM posts p JOIN users u ON p.user_id = u.id
            WHERE u.username = :username
            ORDER BY p.id ASC
        """),
        {"username": username},
    ).mappings().fetchall()
    return [dict(r) for r in rows]
