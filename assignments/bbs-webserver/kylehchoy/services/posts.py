import base64
import binascii
import hashlib
import json
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

import db
from repositories import idempotency as idem_repo
from repositories import posts as posts_repo
from repositories import users as users_repo


def create_post(user_id: int, message: str, parent_id: Optional[int] = None) -> dict:
    _validate_parent(parent_id)
    try:
        return posts_repo.create(user_id, message, parent_id=parent_id)
    except IntegrityError:
        # The pre-check above passed but the FK failed at INSERT time —
        # a concurrent deletion of the parent between check and write.
        # Translate to 404 instead of leaking a 500. parent_id being None
        # can't reach here (no FK to violate on the user_id side under
        # normal use), so we don't need to re-check that branch.
        raise HTTPException(status_code=404, detail="Parent post not found")


def create_post_idempotent(
    user_id: int, key: str, message: str, parent_id: Optional[int] = None,
) -> dict:
    """Stripe-style idempotency under concurrency: the key claim and the post
    insert run in one transaction, so at most one post per (user, key) is
    ever inserted. Same (user, key) + same body replays the stored response;
    same (user, key) + different body → 422; same (user, key) observed while
    the winner is still mid-flight → 409.

    The body hash covers both message and parent_id so a replay with the
    same key but a different parent is rejected.
    """
    body_hash = _body_hash(message, parent_id)

    # Fast path: a completed row already exists. Avoids opening a transaction
    # just to roll it back on the IntegrityError path below.
    existing = idem_repo.get(user_id, key)
    if existing is not None:
        return _replay_or_error(existing, body_hash)

    try:
        with db.engine.begin() as conn:
            idem_repo.claim(conn, user_id, key, body_hash)
            _validate_parent(parent_id, conn=conn)
            try:
                post = posts_repo.create(
                    user_id, message, parent_id=parent_id, conn=conn,
                )
            except IntegrityError:
                # Parent existed at _validate_parent but was deleted before
                # our INSERT could reference it. Same translation as the
                # non-idempotent path — 404 with a clean message, not 500.
                raise HTTPException(
                    status_code=404, detail="Parent post not found",
                )
            idem_repo.finalize(conn, user_id, key, json.dumps(post))
            return post
    except IntegrityError:
        # The claim INSERT failed with a PK collision — another request won
        # the race. Re-read the winner's row and replay.
        winner = idem_repo.get(user_id, key)
        assert winner is not None  # the PK collision implies a row exists
        return _replay_or_error(winner, body_hash)


def _body_hash(message: str, parent_id: Optional[int]) -> str:
    return hashlib.sha256(
        json.dumps({"message": message, "parent_id": parent_id}, sort_keys=True)
        .encode("utf-8")
    ).hexdigest()


def _replay_or_error(row: dict, body_hash: str) -> dict:
    """Map a stored idempotency row to a replay response or a 4xx.

    - body_hash mismatch → 422 (same key, different body is a client bug).
    - response_json == '' → 409 (winner claimed the key but has not yet
      finalized; client should retry shortly).
    - otherwise → decode and return.
    """
    if row["body_hash"] != body_hash:
        raise HTTPException(
            status_code=422,
            detail="Idempotency-Key was used for a different request",
        )
    if row["response_json"] == "":
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key request is still in progress",
        )
    return json.loads(row["response_json"])


def _validate_parent(parent_id: Optional[int], *, conn=None) -> None:
    if parent_id is None:
        return
    if posts_repo.get_by_id(parent_id, conn=conn) is None:
        raise HTTPException(status_code=404, detail="Parent post not found")


def get_post_or_404(post_id: int) -> dict:
    post = posts_repo.get_by_id(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


def delete_post(post_id: int, user_id: int) -> None:
    post = get_post_or_404(post_id)
    if post["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only the author can delete this post")
    posts_repo.delete(post_id)


_LIST_KEYS = (
    "id", "username", "parent_id", "message",
    "created_at", "updated_at", "reaction_counts",
)


def _project_list_item(row: dict, include_snippet: bool = False) -> dict:
    """Strip internal columns (user_id, etag_source) from a list response
    row. Snippet — produced only on the FTS search path — is preserved when
    requested so clients can render highlighted match context."""
    out = {k: row[k] for k in _LIST_KEYS}
    if include_snippet and "snippet" in row:
        out["snippet"] = row["snippet"]
    return out


_SORT_CHOICES = ("recent", "top")


def list_posts(
    q: Optional[str],
    username: Optional[str],
    limit: int,
    offset: int,
    cursor: Optional[str],
    sort: str = "recent",
    window_hours: Optional[int] = None,
) -> tuple[list[dict], Optional[str]]:
    """Returns (posts, next_cursor).

    sort='recent' (default) is chronological; cursor pagination is available on
    this path. sort='top' ranks by reaction count (optionally within a sliding
    `window_hours`) — cursor is disabled here because rank isn't monotonic in
    id, same reason as the FTS search path.

    When `q` is non-empty, results are ranked by FTS5 bm25 and each row
    includes a highlighted `snippet` field. Cursor is also disabled on this
    path. Combining q + sort=top isn't supported — q wins, as search is the
    more specific user intent.
    """
    if sort not in _SORT_CHOICES:
        raise HTTPException(status_code=422, detail=f"sort must be one of {_SORT_CHOICES}")

    # Cursor and offset are two pagination modes. Accepting both would force a
    # silent precedence rule ("cursor wins") that no spec states — better to
    # make the client's intent explicit. offset=0 is the Query default and
    # means "not supplied," so we only reject when the caller actually sent a
    # non-zero offset alongside a cursor.
    if cursor is not None and offset > 0:
        raise HTTPException(
            status_code=422,
            detail="cursor and offset cannot be combined — pick one pagination mode",
        )

    cursor_id = _decode_cursor(cursor) if cursor is not None else None

    if username is not None and not users_repo.exists_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")

    if q:
        if cursor_id is not None:
            raise HTTPException(
                status_code=422,
                detail="cursor pagination is not supported with ?q= (use offset)",
            )
        rows = posts_repo.search_posts(
            q=q, username=username, limit=limit, offset=offset, top_level_only=True,
        )
        return [_project_list_item(r, include_snippet=True) for r in rows], None

    if sort == "top":
        if cursor_id is not None:
            raise HTTPException(
                status_code=422,
                detail="cursor pagination is not supported with sort=top (use offset)",
            )
        rows = posts_repo.list_posts_top(
            username=username, window_hours=window_hours,
            limit=limit, offset=offset, top_level_only=True,
        )
        return [_project_list_item(r) for r in rows], None

    # Offset-only recent path: skip cursor machinery entirely.
    if cursor_id is None and offset > 0:
        rows = posts_repo.list_posts(
            username=username, limit=limit, offset=offset, top_level_only=True,
        )
        return [_project_list_item(r) for r in rows], None

    rows = posts_repo.list_posts(
        username=username, cursor_id=cursor_id, limit=limit + 1, top_level_only=True,
    )
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = _encode_cursor(rows[-1]["id"])
    else:
        next_cursor = None
    return [_project_list_item(r) for r in rows], next_cursor


def list_trending(window_hours: int = 24, limit: int = 10) -> list[dict]:
    """Preset: top-ranked posts from the last `window_hours`. Thin wrapper
    over list_posts_top so the main feed and /posts/trending share ranking
    logic — diverging would create a silent discrepancy between 'trending now'
    and 'sort=top&window=24h'."""
    rows = posts_repo.list_posts_top(
        window_hours=window_hours, limit=limit, offset=0, top_level_only=True,
    )
    return [_project_list_item(r) for r in rows]


def list_replies(post_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    # 404 the reply-list for a missing parent rather than returning [], so
    # clients can distinguish "no replies yet" from "post was deleted."
    get_post_or_404(post_id)
    rows = posts_repo.list_replies(post_id, limit=limit, offset=offset)
    return [_project_list_item(r) for r in rows]


def list_posts_by_username(username: str, limit: int = 50, offset: int = 0) -> list[dict]:
    user = users_repo.get_by_username(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return posts_repo.list_by_user_id(user["id"], limit=limit, offset=offset)


def edit_post(post_id: int, message: str, user_id: int) -> dict:
    post = get_post_or_404(post_id)
    if post["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Only the author can edit this post")
    updated = posts_repo.update_message(post_id, message)
    if updated is None:
        # Concurrent delete between the ownership check and the UPDATE.
        raise HTTPException(status_code=404, detail="Post not found")
    return updated


def _encode_cursor(last_id: int) -> str:
    raw = json.dumps({"id": last_id}).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> int:
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        data = json.loads(raw)
        return int(data["id"])
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError, TypeError):
        raise HTTPException(status_code=422, detail="Invalid cursor")
