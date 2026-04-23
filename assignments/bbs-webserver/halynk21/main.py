"""
main.py — FastAPI BBS webserver (Assignment 2, halynk21).

Bronze + Silver + Gold tier implementation.
Raw SQL via sqlalchemy.text(), matching A1 style conventions.

Run from inside this directory so sqlite:///bbs.db resolves here:
    uvicorn main:app --port 8000
"""

import base64
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal, get_args

from fastapi import FastAPI, Header, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from db import engine, init_db


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


# ── Helpers ───────────────────────────────────────────────────────────────────
def now_iso() -> str:
    """Return current UTC time as an ISO-8601 string (seconds precision)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── Pydantic models ───────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bio: str | None = Field(default=None, max_length=200)


class UserOut(BaseModel):
    username: str
    created_at: str
    bio: str
    post_count: int


class PostCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(..., min_length=1, max_length=500)


class PostUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str | None = Field(default=None, min_length=1, max_length=500)


class PostOut(BaseModel):
    id: int
    username: str
    message: str
    created_at: str
    updated_at: str | None


class CursorPage(BaseModel):
    posts: list[PostOut]
    next_cursor: str | None


ReactionKind = Literal["like", "fire", "laugh", "heart"]
ALLOWED_REACTION_KINDS: tuple[str, ...] = get_args(ReactionKind)


class ReactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: ReactionKind


class ReactionOut(BaseModel):
    id: int
    username: str
    kind: str
    created_at: str


class ReactionSummary(BaseModel):
    total: int
    by_kind: dict[str, int]
    reactions: list[ReactionOut]


# ── SQL helpers ───────────────────────────────────────────────────────────────
_USER_SELECT = """
    SELECT u.username, u.created_at, u.bio,
           (SELECT COUNT(*) FROM posts p WHERE p.user_id = u.id) AS post_count
    FROM users u
"""

_POST_SELECT = """
    SELECT p.id, u.username, p.message,
           p.timestamp AS created_at,
           p.edited_at AS updated_at
    FROM posts p
    JOIN users u ON u.id = p.user_id
"""


def _row_to_user(row) -> UserOut:
    return UserOut(
        username=row.username,
        created_at=row.created_at,
        bio=row.bio or "",
        post_count=row.post_count,
    )


def _row_to_post(row) -> PostOut:
    return PostOut(
        id=row.id,
        username=row.username,
        message=row.message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


# ── User routes ───────────────────────────────────────────────────────────────

@app.post("/users", status_code=201, response_model=UserOut)
def create_user(body: UserCreate) -> UserOut:
    ts = now_iso()
    with engine.connect() as conn:
        try:
            conn.execute(
                text("INSERT INTO users (username, bio, created_at) VALUES (:u, '', :ts)"),
                {"u": body.username, "ts": ts},
            )
            conn.commit()
        except IntegrityError:
            raise HTTPException(status_code=409, detail="username already exists")

        row = conn.execute(
            text(_USER_SELECT + "WHERE u.username = :u"),
            {"u": body.username},
        ).fetchone()

    return _row_to_user(row)


@app.get("/users", response_model=list[UserOut])
def list_users() -> list[UserOut]:
    with engine.connect() as conn:
        rows = conn.execute(text(_USER_SELECT + "ORDER BY u.created_at")).fetchall()
    return [_row_to_user(r) for r in rows]


@app.get("/users/{username}", response_model=UserOut)
def get_user(username: str) -> UserOut:
    with engine.connect() as conn:
        row = conn.execute(
            text(_USER_SELECT + "WHERE u.username = :u"),
            {"u": username},
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return _row_to_user(row)


@app.patch("/users/{username}", response_model=UserOut)
def patch_user(username: str, body: UserUpdate) -> UserOut:
    with engine.connect() as conn:
        row = conn.execute(
            text(_USER_SELECT + "WHERE u.username = :u"),
            {"u": username},
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="user not found")

        if body.bio is not None:
            conn.execute(
                text("UPDATE users SET bio = :bio WHERE username = :u"),
                {"bio": body.bio, "u": username},
            )
            conn.commit()

        row = conn.execute(
            text(_USER_SELECT + "WHERE u.username = :u"),
            {"u": username},
        ).fetchone()

    return _row_to_user(row)


@app.get("/users/{username}/posts", response_model=list[PostOut])
def get_user_posts(username: str) -> list[PostOut]:
    with engine.connect() as conn:
        user_row = conn.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if user_row is None:
            raise HTTPException(status_code=404, detail="user not found")

        rows = conn.execute(
            text(_POST_SELECT + "WHERE u.username = :u ORDER BY p.timestamp DESC"),
            {"u": username},
        ).fetchall()
    return [_row_to_post(r) for r in rows]


# ── Post routes ───────────────────────────────────────────────────────────────

@app.post("/posts", status_code=201, response_model=PostOut)
def create_post(
    body: PostCreate,
    x_username: str | None = Header(default=None, alias="X-Username"),
) -> PostOut:
    # Must return 400, not 422, when header is absent (see §8 gotchas)
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header is required")

    ts = now_iso()
    with engine.connect() as conn:
        user_row = conn.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": x_username},
        ).fetchone()
        if user_row is None:
            raise HTTPException(status_code=404, detail="user not found")

        result = conn.execute(
            text("INSERT INTO posts (user_id, message, timestamp) VALUES (:uid, :msg, :ts)"),
            {"uid": user_row.id, "msg": body.message, "ts": ts},
        )
        conn.commit()
        post_id = result.lastrowid

        row = conn.execute(
            text(_POST_SELECT + "WHERE p.id = :pid"),
            {"pid": post_id},
        ).fetchone()

    return _row_to_post(row)


@app.get("/posts", response_model=list[PostOut] | CursorPage)
def list_posts(
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    username: str | None = Query(default=None),
    cursor: str | None = Query(default=None),
):
    if cursor is not None:
        # Gold path: cursor-based pagination
        try:
            decoded = base64.urlsafe_b64decode(cursor.encode())
            data = json.loads(decoded)
            if not isinstance(data, dict) or "id" not in data:
                raise ValueError("missing id key")
            cursor_id = int(data["id"])
            if cursor_id < 0:
                raise ValueError("negative id")
        except Exception:
            raise HTTPException(status_code=422, detail="invalid cursor")

        conditions = ["p.id < :cursor_id"]
        params: dict = {"cursor_id": cursor_id, "limit": limit + 1}

        if q is not None:
            conditions.append("p.message LIKE '%' || :q || '%'")
            params["q"] = q
        if username is not None:
            conditions.append("u.username = :username")
            params["username"] = username

        where = "WHERE " + " AND ".join(conditions)
        sql = text(_POST_SELECT + where + " ORDER BY p.id DESC LIMIT :limit")
        with engine.connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        has_next = len(rows) > limit
        page_rows = rows[:limit]
        posts = [_row_to_post(r) for r in page_rows]

        next_cursor: str | None = None
        if has_next and page_rows:
            last_id = page_rows[-1].id
            payload = json.dumps({"id": last_id}).encode()
            next_cursor = base64.urlsafe_b64encode(payload).decode()

        return CursorPage(posts=posts, next_cursor=next_cursor)

    # Bronze/silver path: offset-based, return bare list
    conditions = []
    params = {"limit": limit, "offset": offset}

    if q is not None:
        conditions.append("p.message LIKE '%' || :q || '%'")
        params["q"] = q
    if username is not None:
        conditions.append("u.username = :username")
        params["username"] = username

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = text(_POST_SELECT + where + " ORDER BY p.timestamp DESC LIMIT :limit OFFSET :offset")
    with engine.connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_post(r) for r in rows]


@app.get("/posts/{post_id}", response_model=PostOut)
def get_post(post_id: int) -> PostOut:
    with engine.connect() as conn:
        row = conn.execute(
            text(_POST_SELECT + "WHERE p.id = :pid"),
            {"pid": post_id},
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="post not found")
    return _row_to_post(row)


@app.patch("/posts/{post_id}", response_model=PostOut)
def patch_post(
    post_id: int,
    body: PostUpdate,
    x_username: str | None = Header(default=None, alias="X-Username"),
) -> PostOut:
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header is required")

    with engine.connect() as conn:
        row = conn.execute(
            text(_POST_SELECT + "WHERE p.id = :pid"),
            {"pid": post_id},
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="post not found")
        if row.username != x_username:
            raise HTTPException(status_code=403, detail="forbidden: not the post author")

        if body.message is not None:
            conn.execute(
                text("UPDATE posts SET message = :msg, edited_at = :now WHERE id = :pid"),
                {"msg": body.message, "now": now_iso(), "pid": post_id},
            )
            conn.commit()

        row = conn.execute(
            text(_POST_SELECT + "WHERE p.id = :pid"),
            {"pid": post_id},
        ).fetchone()

    return _row_to_post(row)


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int) -> Response:
    with engine.connect() as conn:
        result = conn.execute(
            text("DELETE FROM posts WHERE id = :pid"),
            {"pid": post_id},
        )
        conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="post not found")
    return Response(status_code=204)


# ── Reaction routes ───────────────────────────────────────────────────────────

@app.post("/posts/{post_id}/reactions", status_code=201, response_model=ReactionOut)
def create_reaction(
    post_id: int,
    body: ReactionCreate,
    x_username: str | None = Header(default=None, alias="X-Username"),
) -> ReactionOut:
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header is required")

    ts = now_iso()
    with engine.connect() as conn:
        if conn.execute(text("SELECT 1 FROM posts WHERE id = :pid"),
                        {"pid": post_id}).fetchone() is None:
            raise HTTPException(status_code=404, detail="post not found")

        user_row = conn.execute(text("SELECT id FROM users WHERE username = :u"),
                                {"u": x_username}).fetchone()
        if user_row is None:
            raise HTTPException(status_code=404, detail="user not found")

        try:
            result = conn.execute(
                text("INSERT INTO reactions (user_id, post_id, kind, created_at) "
                     "VALUES (:uid, :pid, :k, :ts)"),
                {"uid": user_row.id, "pid": post_id, "k": body.kind, "ts": ts},
            )
            conn.commit()
        except IntegrityError:
            raise HTTPException(status_code=409, detail="reaction already exists")

        row = conn.execute(
            text("SELECT r.id, u.username, r.kind, r.created_at "
                 "FROM reactions r JOIN users u ON u.id = r.user_id "
                 "WHERE r.id = :rid"),
            {"rid": result.lastrowid},
        ).fetchone()

    return ReactionOut(id=row.id, username=row.username, kind=row.kind, created_at=row.created_at)


@app.delete("/posts/{post_id}/reactions/{kind}", status_code=204)
def delete_reaction(
    post_id: int,
    kind: str,
    x_username: str | None = Header(default=None, alias="X-Username"),
) -> Response:
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header is required")
    if kind not in ALLOWED_REACTION_KINDS:
        raise HTTPException(status_code=422, detail="invalid reaction kind")

    with engine.connect() as conn:
        result = conn.execute(
            text("""
                DELETE FROM reactions
                WHERE post_id = :pid
                  AND kind = :k
                  AND user_id = (SELECT id FROM users WHERE username = :u)
            """),
            {"pid": post_id, "k": kind, "u": x_username},
        )
        conn.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="reaction not found")
    return Response(status_code=204)


@app.get("/posts/{post_id}/reactions", response_model=ReactionSummary)
def get_reactions(post_id: int) -> ReactionSummary:
    with engine.connect() as conn:
        if conn.execute(text("SELECT 1 FROM posts WHERE id = :pid"),
                        {"pid": post_id}).fetchone() is None:
            raise HTTPException(status_code=404, detail="post not found")

        rows = conn.execute(
            text("""
                SELECT r.id, u.username, r.kind, r.created_at
                FROM reactions r JOIN users u ON u.id = r.user_id
                WHERE r.post_id = :pid ORDER BY r.created_at
            """),
            {"pid": post_id},
        ).fetchall()

    reactions = [ReactionOut(id=r.id, username=r.username, kind=r.kind, created_at=r.created_at)
                 for r in rows]
    by_kind: dict[str, int] = {}
    for r in reactions:
        by_kind[r.kind] = by_kind.get(r.kind, 0) + 1
    return ReactionSummary(total=len(reactions), by_kind=by_kind, reactions=reactions)


# ── Pulse endpoint ────────────────────────────────────────────────────────────

@app.get("/")
def pulse() -> dict:
    return {
        "service": "bbs-webserver",
        "status": "ok",
        "motd": "halynk21 BBS webserver — A2 stacked bronze+silver+gold",
    }
