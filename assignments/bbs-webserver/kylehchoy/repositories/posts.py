from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from constants import REACTION_KINDS
import db


# Build the per-kind SQL fragments from REACTION_KINDS so a new kind added
# in constants.py flows through without touching SQL here. The values are
# closed lowercase ASCII identifiers (see constants.py), so f-string
# interpolation into SQL is safe — no user input reaches this code path.
_SUM_EXPRS = ",\n               ".join(
    f"SUM(CASE WHEN kind='{k}' THEN 1 ELSE 0 END) AS {k}_count"
    for k in REACTION_KINDS
)
_COALESCED_COUNTS = ",\n           ".join(
    f"COALESCE(rc.{k}_count, 0) AS {k}_count" for k in REACTION_KINDS
)

# Aggregate all-time reaction counts per post. LEFT JOIN so posts with no
# reactions still return a row (the SUMs come back NULL and are coalesced to
# 0 at projection time).
_REACTION_AGGREGATE_JOIN = f"""
    LEFT JOIN (
        SELECT post_id,
               {_SUM_EXPRS}
        FROM reactions
        GROUP BY post_id
    ) rc ON rc.post_id = p.id
"""

_POST_SELECT = f"""
    SELECT p.id, p.user_id, u.username, p.parent_id, p.message,
           p.created_at, p.updated_at,
           COALESCE(p.updated_at, p.created_at) AS etag_source,
           {_COALESCED_COUNTS}
    FROM posts p
    JOIN users u ON p.user_id = u.id
    {_REACTION_AGGREGATE_JOIN}
"""


def _now_utc_iso() -> str:
    # Microsecond precision. Second-precision timestamps collide when a client
    # creates then edits a post within the same second — the weak ETag would
    # not advance, and conditional requests would serve stale content.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _row_to_dict(row) -> Optional[dict]:
    if row is None:
        return None
    return {
        "id": row.id,
        "user_id": row.user_id,
        "username": row.username,
        "parent_id": row.parent_id,
        "message": row.message,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "etag_source": row.etag_source,
        "reaction_counts": {k: getattr(row, f"{k}_count") for k in REACTION_KINDS},
    }


def _fts_phrase(q: str) -> str:
    # Wrap the user query as a single FTS5 phrase. Double-quoting neutralizes
    # operator characters (:, ^, *, AND/OR/NOT, parentheses) so arbitrary user
    # input can't crash the parser or leak query syntax. Internal quotes are
    # escaped by doubling.
    return '"' + q.replace('"', '""') + '"'


def create(
    user_id: int,
    message: str,
    parent_id: Optional[int] = None,
    *,
    conn=None,
) -> dict:
    """Insert a post and return the shared-SELECT projection.

    If `conn` is supplied, runs inside that caller-owned transaction so the
    insert can be composed atomically with other writes (e.g. claiming an
    idempotency key). If omitted, opens its own engine.begin() block — the
    common single-write path.
    """
    if conn is not None:
        return _create_impl(conn, user_id, message, parent_id)
    with db.engine.begin() as c:
        return _create_impl(c, user_id, message, parent_id)


def _create_impl(conn, user_id: int, message: str, parent_id: Optional[int]) -> dict:
    result = conn.execute(
        text(
            "INSERT INTO posts (user_id, parent_id, message) "
            "VALUES (:user_id, :parent_id, :message)"
        ),
        {"user_id": user_id, "parent_id": parent_id, "message": message},
    )
    post_id = result.lastrowid
    row = conn.execute(
        text(_POST_SELECT + " WHERE p.id = :id"),
        {"id": post_id},
    ).fetchone()
    assert row is not None  # the row we just inserted must exist
    return _row_to_dict(row)  # type: ignore[return-value]


def get_by_id(post_id: int, *, conn=None) -> Optional[dict]:
    """Read the shared-SELECT projection for one post. Accepts an optional
    caller-owned `conn` so parent-existence checks can share a transaction
    with the write that follows — preventing check/write races."""
    if conn is not None:
        row = conn.execute(
            text(_POST_SELECT + " WHERE p.id = :id"),
            {"id": post_id},
        ).fetchone()
        return _row_to_dict(row)
    with db.engine.connect() as c:
        row = c.execute(
            text(_POST_SELECT + " WHERE p.id = :id"),
            {"id": post_id},
        ).fetchone()
    return _row_to_dict(row)


def delete(post_id: int) -> bool:
    with db.engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM posts WHERE id = :id"),
            {"id": post_id},
        )
        return result.rowcount > 0


def list_posts(
    username: Optional[str] = None,
    cursor_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    top_level_only: bool = False,
) -> list[dict]:
    """Return posts newest-first (ORDER BY id DESC).

    When cursor_id is provided, filters WHERE id < cursor_id and ignores offset.
    Full-text search is handled by search_posts() and popularity ranking by
    list_posts_top() — this path is the plain chronological listing.

    top_level_only filters out replies (parent_id IS NOT NULL) so the main
    feed shows top-level posts; replies are fetched per-post via list_replies.
    """
    where_parts = []
    params: dict = {"limit": limit}

    if username is not None:
        where_parts.append("u.username = :username")
        params["username"] = username
    if cursor_id is not None:
        where_parts.append("p.id < :cursor_id")
        params["cursor_id"] = cursor_id
    if top_level_only:
        where_parts.append("p.parent_id IS NULL")

    where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
    sql = _POST_SELECT + where_sql + " ORDER BY p.id DESC LIMIT :limit"
    if cursor_id is None:
        sql += " OFFSET :offset"
        params["offset"] = offset

    with db.engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
    return [_row_to_dict(r) for r in rows]


def list_posts_top(
    username: Optional[str] = None,
    window_hours: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    top_level_only: bool = False,
) -> list[dict]:
    """Rank posts by reaction count within an optional sliding window.

    The *ranking* uses only reactions whose `created_at` falls inside the
    window, so a post that went viral yesterday beats a post that collected
    reactions two months ago. The *displayed* reaction_counts remain all-time
    — windowing the display numbers would surprise clients who are used to
    "like this post" meaning "incremented the like count I see."

    Tiebreaker is p.id DESC so newer posts win ties. Cursor pagination is
    intentionally unsupported: rank_score is not monotonic in id.
    """
    where_parts: list[str] = []
    params: dict = {"limit": limit, "offset": offset}

    if username is not None:
        where_parts.append("u.username = :username")
        params["username"] = username
    if top_level_only:
        where_parts.append("p.parent_id IS NULL")

    if window_hours is not None:
        rank_join = """
            LEFT JOIN (
                SELECT post_id, COUNT(*) AS rank_score
                FROM reactions
                WHERE created_at >= strftime('%Y-%m-%dT%H:%M:%SZ', 'now', :window_expr)
                GROUP BY post_id
            ) rk ON rk.post_id = p.id
        """
        params["window_expr"] = f"-{int(window_hours)} hours"
    else:
        rank_join = """
            LEFT JOIN (
                SELECT post_id, COUNT(*) AS rank_score
                FROM reactions
                GROUP BY post_id
            ) rk ON rk.post_id = p.id
        """

    where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""
    sql = f"""
        SELECT p.id, p.user_id, u.username, p.parent_id, p.message,
               p.created_at, p.updated_at,
               COALESCE(p.updated_at, p.created_at) AS etag_source,
               {_COALESCED_COUNTS}
        FROM posts p
        JOIN users u ON p.user_id = u.id
        {_REACTION_AGGREGATE_JOIN}
        {rank_join}
        {where_sql}
        ORDER BY COALESCE(rk.rank_score, 0) DESC, p.id DESC
        LIMIT :limit OFFSET :offset
    """
    with db.engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
    return [_row_to_dict(r) for r in rows]


def list_replies(parent_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    """Direct replies to a post, oldest-first (threaded-conversation order).

    Only one level deep. Nested replies exist via parent_id chains but this
    query doesn't recurse — clients that want a full tree fetch replies
    per-node. SQLite CTE recursion would work here but adds complexity the
    assignment doesn't justify.
    """
    with db.engine.connect() as conn:
        rows = conn.execute(
            text(
                _POST_SELECT
                + " WHERE p.parent_id = :pid ORDER BY p.id ASC LIMIT :limit OFFSET :offset"
            ),
            {"pid": parent_id, "limit": limit, "offset": offset},
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def search_posts(
    q: str,
    username: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    top_level_only: bool = False,
) -> list[dict]:
    """FTS5 search over posts.message. Rows come back ordered by bm25 relevance
    (most relevant first) with a snippet() column highlighting the match.

    Cursor pagination is intentionally unsupported on the search path — bm25
    rank is not monotonic in id, so a last-seen id can't bound the next page.
    Use offset for paging through search results.

    top_level_only filters out replies so search preserves the same feed
    boundary as the non-search /posts path — the main feed is always
    top-level posts; replies are fetched per-post via /posts/{id}/replies.
    """
    where_parts = ["posts_fts MATCH :q"]
    params: dict = {"q": _fts_phrase(q), "limit": limit, "offset": offset}
    if username is not None:
        where_parts.append("u.username = :username")
        params["username"] = username
    if top_level_only:
        where_parts.append("p.parent_id IS NULL")

    sql = f"""
        SELECT p.id, p.user_id, u.username, p.parent_id, p.message,
               p.created_at, p.updated_at,
               COALESCE(p.updated_at, p.created_at) AS etag_source,
               {_COALESCED_COUNTS},
               snippet(posts_fts, 0, '<b>', '</b>', '…', 10) AS snippet
        FROM posts p
        JOIN users u ON p.user_id = u.id
        {_REACTION_AGGREGATE_JOIN}
        JOIN posts_fts ON posts_fts.rowid = p.id
        WHERE {' AND '.join(where_parts)}
        ORDER BY bm25(posts_fts) ASC, p.id DESC
        LIMIT :limit OFFSET :offset
    """
    with db.engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
    out = []
    for r in rows:
        d = _row_to_dict(r)
        assert d is not None
        d["snippet"] = r.snippet
        out.append(d)
    return out


def list_by_user_id(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    with db.engine.connect() as conn:
        rows = conn.execute(
            text(
                _POST_SELECT
                + " WHERE p.user_id = :uid ORDER BY p.id DESC LIMIT :limit OFFSET :offset"
            ),
            {"uid": user_id, "limit": limit, "offset": offset},
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_message(post_id: int, message: str) -> Optional[dict]:
    """Two-step: UPDATE then SELECT. RETURNING would collapse round-trips but
    can't join through to reaction aggregates cleanly, so we read back via the
    shared SELECT to keep response shape consistent across endpoints."""
    updated_at = _now_utc_iso()
    with db.engine.begin() as conn:
        result = conn.execute(
            text("UPDATE posts SET message = :message, updated_at = :ts WHERE id = :id"),
            {"message": message, "ts": updated_at, "id": post_id},
        )
        if result.rowcount == 0:
            return None
        row = conn.execute(
            text(_POST_SELECT + " WHERE p.id = :id"),
            {"id": post_id},
        ).fetchone()
    return _row_to_dict(row)
