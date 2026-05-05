import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text

DB_PATH = Path(__file__).parent / "bbs.db"
engine = create_engine(f"sqlite:///{DB_PATH}")


def _ensure_column(conn, table: str, column: str, definition: str) -> None:
    """Add a column to a table if it doesn't already exist (SQLite-only migration helper)."""
    info = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    if not any(row.name == column for row in info):
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))


def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                bio TEXT DEFAULT NULL,
                deleted_at TEXT DEFAULT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT DEFAULT NULL,
                board_id INTEGER DEFAULT NULL REFERENCES boards(id),
                parent_id INTEGER DEFAULT NULL REFERENCES posts(id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                username TEXT NOT NULL,
                kind TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(post_id, username)
            )
        """))
        # Migrations: add new columns to existing databases without losing data.
        _ensure_column(conn, "users", "deleted_at", "TEXT DEFAULT NULL")
        _ensure_column(conn, "posts", "parent_id", "INTEGER DEFAULT NULL REFERENCES posts(id)")


def _now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def _user_dict(row) -> dict:
    return {
        "username": row.username,
        "created_at": row.created_at,
        "bio": row.bio,
        "post_count": row.post_count,
    }


def _post_dict(row, reaction_counts: Optional[dict] = None) -> dict:
    d = {
        "id": row.id,
        "username": row.username,
        "message": row.message,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "parent_id": row.parent_id,
        "board": row.board_name,
        "reaction_counts": reaction_counts or {},
    }
    return d


def _board_dict(row) -> dict:
    return {
        "name": row.name,
        "description": row.description,
        "created_at": row.created_at,
        "post_count": row.post_count,
    }


def _get_reaction_counts(conn, post_ids: List[int]) -> Dict[int, dict]:
    """Get aggregated reaction counts for a list of post ids."""
    if not post_ids:
        return {}
    # int() coerces each id, raising ValueError on anything non-numeric.
    # This makes the function self-defending against callers that violate
    # the List[int] type hint (hints are not enforced at runtime).
    placeholders = ",".join(str(int(pid)) for pid in post_ids)
    rows = conn.execute(text(f"""
        SELECT post_id, kind, COUNT(*) as cnt
        FROM reactions
        WHERE post_id IN ({placeholders})
        GROUP BY post_id, kind
    """)).fetchall()
    counts = {}  # type: Dict[int, dict]
    for r in rows:
        counts.setdefault(r.post_id, {})[r.kind] = r.cnt
    return counts


def _get_single_post_reaction_counts(post_id: int) -> dict:
    with engine.connect() as conn:
        return _get_reaction_counts(conn, [post_id]).get(post_id, {})


_USER_SELECT = """
    SELECT u.username, u.created_at, u.bio,
           (SELECT COUNT(*) FROM posts p WHERE p.user_id = u.id) AS post_count
    FROM users u
    WHERE u.deleted_at IS NULL
"""


_POST_SELECT = """
    SELECT p.id,
           CASE WHEN u.deleted_at IS NOT NULL THEN '[deleted]' ELSE u.username END AS username,
           p.message, p.created_at, p.updated_at, p.parent_id,
           b.name AS board_name
    FROM posts p
    JOIN users u ON p.user_id = u.id
    LEFT JOIN boards b ON p.board_id = b.id
"""


_BOARD_SELECT = """
    SELECT b.name, b.description, b.created_at,
           (SELECT COUNT(*) FROM posts p WHERE p.board_id = b.id) AS post_count
    FROM boards b
"""


# ── Users ──────────────────────────────────────────────────────────

def create_user(username: str) -> Optional[dict]:
    ts = _now()
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT 1 FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if existing:
            return None
        conn.execute(
            text("INSERT INTO users (username, created_at) VALUES (:u, :ts)"),
            {"u": username, "ts": ts},
        )
    return {"username": username, "created_at": ts, "bio": None, "post_count": 0}


def get_user(username: str) -> Optional[dict]:
    with engine.connect() as conn:
        row = conn.execute(
            text(_USER_SELECT + " AND u.username = :u"),
            {"u": username},
        ).fetchone()
    if row is None:
        return None
    return _user_dict(row)


def get_all_users() -> List[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(_USER_SELECT + " ORDER BY u.id")
        ).fetchall()
    return [_user_dict(r) for r in rows]


def update_user_bio(username: str, bio: str) -> Optional[dict]:
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE users SET bio = :bio WHERE username = :u AND deleted_at IS NULL"),
            {"bio": bio, "u": username},
        )
        if result.rowcount == 0:
            return None
    return get_user(username)


def delete_user(username: str) -> bool:
    """Soft-delete a user by setting deleted_at. Returns True if a user was marked."""
    ts = _now()
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE users SET deleted_at = :ts WHERE username = :u AND deleted_at IS NULL"),
            {"ts": ts, "u": username},
        )
    return result.rowcount > 0


# ── Posts ──────────────────────────────────────────────────────────

def create_post(
    username: str,
    message: str,
    board: Optional[str] = None,
    parent_id: Optional[int] = None,
) -> dict:
    ts = _now()
    with engine.begin() as conn:
        user_id = conn.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone().id

        # Replies: inherit no board, validate parent exists.
        if parent_id is not None:
            parent = conn.execute(
                text("SELECT id FROM posts WHERE id = :pid"),
                {"pid": parent_id},
            ).fetchone()
            if parent is None:
                return {"_error": "parent_not_found"}
            board_id = None
            board_name = None
        else:
            board_id = None
            board_name = None
            if board is not None:
                board_row = conn.execute(
                    text("SELECT id, name FROM boards WHERE name = :n"),
                    {"n": board},
                ).fetchone()
                if board_row is None:
                    return {"_error": "board_not_found"}
                board_id = board_row.id
                board_name = board_row.name

        result = conn.execute(
            text("INSERT INTO posts (user_id, message, created_at, board_id, parent_id) VALUES (:uid, :msg, :ts, :bid, :par)"),
            {"uid": user_id, "msg": message, "ts": ts, "bid": board_id, "par": parent_id},
        )
        post_id = result.lastrowid
    return {
        "id": post_id, "username": username, "message": message,
        "created_at": ts, "updated_at": None, "parent_id": parent_id,
        "board": board_name, "reaction_counts": {},
    }


def get_post(post_id: int) -> Optional[dict]:
    with engine.connect() as conn:
        row = conn.execute(
            text(_POST_SELECT + " WHERE p.id = :pid"),
            {"pid": post_id},
        ).fetchone()
        if row is None:
            return None
        rc = _get_reaction_counts(conn, [post_id]).get(post_id, {})
    return _post_dict(row, rc)


def get_posts(
    q: Optional[str] = None,
    username: Optional[str] = None,
    board: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    cursor: Optional[str] = None,
    include_replies: bool = False,
) -> dict:
    """Returns {"posts": [...], "next_cursor": ..., "has_more": bool}.

    By default returns only top-level posts (parent_id IS NULL). Pass
    include_replies=True to return replies too.
    """
    clauses = []
    params = {}  # type: Dict[str, object]
    if not include_replies:
        clauses.append("p.parent_id IS NULL")
    if q:
        clauses.append("p.message LIKE :q")
        params["q"] = f"%{q}%"
    if username:
        # Filter by an explicit username: exclude soft-deleted users so their
        # name isn't "findable" anymore. Their posts still appear in unfiltered
        # feeds as "[deleted]".
        clauses.append("u.username = :username AND u.deleted_at IS NULL")
        params["username"] = username
    if board:
        clauses.append("b.name = :board")
        params["board"] = board

    cursor_id = None
    if cursor:
        try:
            decoded = json.loads(base64.b64decode(cursor))
            cursor_id = int(decoded["id"])
        except Exception:
            cursor_id = None

    if cursor_id is not None:
        clauses.append("p.id > :cursor_id")
        params["cursor_id"] = cursor_id
    elif offset > 0:
        params["offset"] = offset

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    # Fetch limit+1 to check has_more
    fetch_limit = limit + 1
    params["limit"] = fetch_limit

    if cursor_id is not None or offset == 0:
        sql = f"{_POST_SELECT} {where} ORDER BY p.id LIMIT :limit"
    else:
        sql = f"{_POST_SELECT} {where} ORDER BY p.id LIMIT :limit OFFSET :offset"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
        post_ids = [r.id for r in rows[:limit]]
        rc_map = _get_reaction_counts(conn, post_ids)

    has_more = len(rows) > limit
    rows = rows[:limit]
    posts = [_post_dict(r, rc_map.get(r.id, {})) for r in rows]

    next_cursor = None
    if has_more and posts:
        last_id = posts[-1]["id"]
        next_cursor = base64.b64encode(json.dumps({"id": last_id}).encode()).decode()

    return {"posts": posts, "next_cursor": next_cursor, "has_more": has_more}


def get_user_posts(username: str) -> List[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(_POST_SELECT + " WHERE u.username = :u AND u.deleted_at IS NULL ORDER BY p.id"),
            {"u": username},
        ).fetchall()
        post_ids = [r.id for r in rows]
        rc_map = _get_reaction_counts(conn, post_ids)
    return [_post_dict(r, rc_map.get(r.id, {})) for r in rows]


def update_post_message(post_id: int, message: str) -> Optional[dict]:
    ts = _now()
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE posts SET message = :msg, updated_at = :ts WHERE id = :pid"),
            {"msg": message, "ts": ts, "pid": post_id},
        )
        if result.rowcount == 0:
            return None
    return get_post(post_id)


def delete_post(post_id: int) -> bool:
    """Delete a post and all its descendants (cascade). Returns True if any post was deleted."""
    with engine.begin() as conn:
        # Gather every id in the subtree rooted at post_id via a recursive CTE.
        id_rows = conn.execute(text("""
            WITH RECURSIVE subtree(id) AS (
                SELECT id FROM posts WHERE id = :root_id
                UNION ALL
                SELECT p.id FROM posts p JOIN subtree s ON p.parent_id = s.id
            )
            SELECT id FROM subtree
        """), {"root_id": post_id}).fetchall()
        ids = [r.id for r in id_rows]
        if not ids:
            return False
        placeholders = ",".join(str(int(pid)) for pid in ids)
        # Delete reactions on all affected posts first (SQLite may not enforce CASCADE).
        conn.execute(text(f"DELETE FROM reactions WHERE post_id IN ({placeholders})"))
        # Delete descendants before the root so FK self-references stay valid.
        conn.execute(text(f"DELETE FROM posts WHERE id IN ({placeholders})"))
    return True


def get_thread(root_id: int) -> Optional[dict]:
    """Return a root post and every descendant, flat, in id order.

    Returns {"posts": [...]} or None if the root doesn't exist. Each post
    carries its own parent_id so the client can reconstruct the tree.
    """
    with engine.connect() as conn:
        root = conn.execute(text("SELECT id FROM posts WHERE id = :pid"), {"pid": root_id}).fetchone()
        if root is None:
            return None
        id_rows = conn.execute(text("""
            WITH RECURSIVE thread_ids(id) AS (
                SELECT id FROM posts WHERE id = :root_id
                UNION ALL
                SELECT p.id FROM posts p JOIN thread_ids t ON p.parent_id = t.id
            )
            SELECT id FROM thread_ids
        """), {"root_id": root_id}).fetchall()
        ids = [r.id for r in id_rows]
        placeholders = ",".join(str(int(pid)) for pid in ids)
        rows = conn.execute(text(
            f"{_POST_SELECT} WHERE p.id IN ({placeholders}) ORDER BY p.id"
        )).fetchall()
        rc_map = _get_reaction_counts(conn, ids)
    return {"posts": [_post_dict(r, rc_map.get(r.id, {})) for r in rows]}


# ── Boards ─────────────────────────────────────────────────────────

def create_board(name: str, description: Optional[str] = None) -> Optional[dict]:
    ts = _now()
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT 1 FROM boards WHERE name = :n"),
            {"n": name},
        ).fetchone()
        if existing:
            return None
        conn.execute(
            text("INSERT INTO boards (name, description, created_at) VALUES (:n, :d, :ts)"),
            {"n": name, "d": description, "ts": ts},
        )
    return {"name": name, "description": description, "created_at": ts, "post_count": 0}


def get_board(name: str) -> Optional[dict]:
    with engine.connect() as conn:
        row = conn.execute(
            text(_BOARD_SELECT + " WHERE b.name = :n"),
            {"n": name},
        ).fetchone()
    if row is None:
        return None
    return _board_dict(row)


def get_all_boards() -> List[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(_BOARD_SELECT + " ORDER BY b.id")
        ).fetchall()
    return [_board_dict(r) for r in rows]


# ── Reactions ──────────────────────────────────────────────────────

VALID_REACTIONS = {"heart", "laugh", "fire"}


def create_reaction(post_id: int, username: str, kind: str) -> Optional[dict]:
    """Upsert a reaction (one reaction per user per post).

    - No existing reaction: insert new row.
    - Existing reaction with same kind: no-op (idempotent).
    - Existing reaction with different kind: update kind, keep original created_at.
    Returns the final reaction dict, or {"_error": "post_not_found"}.
    """
    ts = _now()
    with engine.begin() as conn:
        post = conn.execute(text("SELECT id FROM posts WHERE id = :pid"), {"pid": post_id}).fetchone()
        if post is None:
            return {"_error": "post_not_found"}
        existing = conn.execute(
            text("SELECT kind, created_at FROM reactions WHERE post_id = :pid AND username = :u"),
            {"pid": post_id, "u": username},
        ).fetchone()
        if existing is None:
            conn.execute(
                text("INSERT INTO reactions (post_id, username, kind, created_at) VALUES (:pid, :u, :k, :ts)"),
                {"pid": post_id, "u": username, "k": kind, "ts": ts},
            )
            return {"post_id": post_id, "username": username, "kind": kind, "created_at": ts}
        if existing.kind == kind:
            return {"post_id": post_id, "username": username, "kind": kind, "created_at": existing.created_at}
        conn.execute(
            text("UPDATE reactions SET kind = :k WHERE post_id = :pid AND username = :u"),
            {"pid": post_id, "u": username, "k": kind},
        )
    return {"post_id": post_id, "username": username, "kind": kind, "created_at": existing.created_at}


def get_reactions(post_id: int) -> Optional[List[dict]]:
    """Get all reactions on a post. Returns None if post not found."""
    with engine.connect() as conn:
        post = conn.execute(text("SELECT id FROM posts WHERE id = :pid"), {"pid": post_id}).fetchone()
        if post is None:
            return None
        rows = conn.execute(
            text("SELECT username, kind, created_at FROM reactions WHERE post_id = :pid ORDER BY id"),
            {"pid": post_id},
        ).fetchall()
    return [{"username": r.username, "kind": r.kind, "created_at": r.created_at} for r in rows]


def delete_reaction(post_id: int, username: str) -> Optional[bool]:
    """Delete all reactions by a user on a post. Returns None if post not found, True if deleted, False if nothing to delete."""
    with engine.begin() as conn:
        post = conn.execute(text("SELECT id FROM posts WHERE id = :pid"), {"pid": post_id}).fetchone()
        if post is None:
            return None
        result = conn.execute(
            text("DELETE FROM reactions WHERE post_id = :pid AND username = :u"),
            {"pid": post_id, "u": username},
        )
    return result.rowcount > 0
