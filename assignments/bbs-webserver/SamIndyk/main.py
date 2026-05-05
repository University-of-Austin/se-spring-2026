"""main.py - FastAPI BBS webserver

Endpoints:

  Bronze (spec):
    POST   /users                          -> 201
    GET    /users                          -> 200
    GET    /users/{username}               -> 200/404
    GET    /users/{username}/posts         -> 200/404
    POST   /posts                          -> 201/400/404/422      (X-Username)
    GET    /posts                          -> 200 (?q, ?limit, ?offset)
    GET    /posts/{id}                     -> 200/404
    DELETE /posts/{id}                     -> 204/404

  Silver:
    PATCH  /users/{username}               -> 200/404/422          (bio edit)
    PATCH  /posts/{id}                     -> 200/400/403/404/422  (X-Username, author-only)
    GET    /posts?username=alice           -> filter by author

  Gold (reactions):
    POST   /posts/{id}/reactions           -> 201/404/409/422
    GET    /posts/{id}/reactions           -> 200/404
    DELETE /posts/{id}/reactions/{username}-> 204/404
"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from db import engine, init_db

app = FastAPI(title="BBS Webserver", version="2.0")


@app.on_event("startup")
def _startup() -> None:
    init_db()


USERNAME_PATTERN = r"^[a-zA-Z0-9_]+$"


# ---------------------------------------------------------------------------
# Pydantic request models (extra="forbid" rejects unknown fields -> 422)
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(..., min_length=3, max_length=20, pattern=USERNAME_PATTERN)


class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bio: Optional[str] = Field(None, max_length=200)


class PostCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(..., min_length=1, max_length=500)


class PostPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(..., min_length=1, max_length=500)


class ReactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(..., min_length=3, max_length=20, pattern=USERNAME_PATTERN)
    kind: str = Field(..., min_length=1, max_length=20)


# ---------------------------------------------------------------------------
# Row-to-dict helpers. The shape returned here is the single source of truth
# for every endpoint that returns a user or a post.
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _user_dict(conn, user_row) -> dict:
    uid, username, bio, created_at = user_row
    post_count = conn.execute(
        text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"),
        {"uid": uid},
    ).scalar() or 0
    return {
        "username": username,
        "created_at": created_at,
        "bio": bio,
        "post_count": post_count,
    }


def _post_dict(conn, post_row) -> dict:
    pid, username, message, created_at, updated_at = post_row
    reactions = {
        kind: count
        for (kind, count) in conn.execute(
            text(
                "SELECT kind, COUNT(*) FROM reactions "
                "WHERE post_id = :pid GROUP BY kind"
            ),
            {"pid": pid},
        ).fetchall()
    }
    return {
        "id": pid,
        "username": username,
        "message": message,
        "created_at": created_at,
        "updated_at": updated_at,
        "reactions": reactions,
    }


POST_SELECT = """
    SELECT p.id, u.username, p.message, p.created_at, p.updated_at
    FROM posts p
    JOIN users u ON u.id = p.user_id
"""


def _fetch_user(conn, username: str):
    return conn.execute(
        text("SELECT id, username, bio, created_at FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()


def _fetch_post(conn, post_id: int):
    return conn.execute(
        text(POST_SELECT + " WHERE p.id = :pid"),
        {"pid": post_id},
    ).fetchone()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


@app.post("/users", status_code=201)
def create_user(body: UserCreate):
    now = _now()
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO users (username, bio, created_at) "
                    "VALUES (:u, '', :ts)"
                ),
                {"u": body.username, "ts": now},
            )
            row = _fetch_user(conn, body.username)
            return _user_dict(conn, row)
    except IntegrityError:
        raise HTTPException(status_code=409, detail="username already exists")


@app.get("/users")
def list_users():
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, username, bio, created_at FROM users "
                "ORDER BY username ASC"
            )
        ).fetchall()
        return [_user_dict(conn, r) for r in rows]


@app.get("/users/{username}")
def get_user(username: str):
    with engine.connect() as conn:
        row = _fetch_user(conn, username)
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        return _user_dict(conn, row)


@app.patch("/users/{username}")
def patch_user(username: str, body: UserPatch):
    with engine.begin() as conn:
        row = _fetch_user(conn, username)
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        if body.bio is not None:
            conn.execute(
                text("UPDATE users SET bio = :b WHERE id = :uid"),
                {"b": body.bio, "uid": row[0]},
            )
        fresh = _fetch_user(conn, username)
        return _user_dict(conn, fresh)


@app.get("/users/{username}/posts")
def get_user_posts(username: str):
    with engine.connect() as conn:
        row = _fetch_user(conn, username)
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        rows = conn.execute(
            text(POST_SELECT + " WHERE p.user_id = :uid ORDER BY p.id DESC"),
            {"uid": row[0]},
        ).fetchall()
        return [_post_dict(conn, r) for r in rows]


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------


@app.post("/posts", status_code=201)
def create_post(
    body: PostCreate,
    x_username: Optional[str] = Header(None, alias="X-Username"),
):
    if not x_username:
        raise HTTPException(status_code=400, detail="X-Username header required")
    now = _now()
    with engine.begin() as conn:
        user_row = _fetch_user(conn, x_username)
        if not user_row:
            raise HTTPException(status_code=404, detail="poster does not exist")
        result = conn.execute(
            text(
                "INSERT INTO posts (user_id, message, created_at, updated_at) "
                "VALUES (:uid, :m, :ts, NULL)"
            ),
            {"uid": user_row[0], "m": body.message, "ts": now},
        )
        return _post_dict(conn, _fetch_post(conn, result.lastrowid))


@app.get("/posts")
def list_posts(
    q: Optional[str] = None,
    username: Optional[str] = Query(
        None, min_length=3, max_length=20, pattern=USERNAME_PATTERN
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    clauses = []
    params: dict = {"limit": limit, "offset": offset}
    if q is not None:
        clauses.append("p.message LIKE :q")
        params["q"] = f"%{q}%"
    if username is not None:
        clauses.append("u.username = :uname")
        params["uname"] = username
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = POST_SELECT + where + " ORDER BY p.id DESC LIMIT :limit OFFSET :offset"
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
        return [_post_dict(conn, r) for r in rows]


@app.get("/posts/{post_id}")
def get_post(post_id: int):
    with engine.connect() as conn:
        row = _fetch_post(conn, post_id)
        if not row:
            raise HTTPException(status_code=404, detail="post not found")
        return _post_dict(conn, row)


@app.patch("/posts/{post_id}")
def patch_post(
    post_id: int,
    body: PostPatch,
    x_username: Optional[str] = Header(None, alias="X-Username"),
):
    if not x_username:
        raise HTTPException(status_code=400, detail="X-Username header required")
    with engine.begin() as conn:
        row = _fetch_post(conn, post_id)
        if not row:
            raise HTTPException(status_code=404, detail="post not found")
        if row[1] != x_username:
            raise HTTPException(
                status_code=403, detail="only the author may edit this post"
            )
        conn.execute(
            text("UPDATE posts SET message = :m, updated_at = :ts WHERE id = :pid"),
            {"m": body.message, "ts": _now(), "pid": post_id},
        )
        return _post_dict(conn, _fetch_post(conn, post_id))


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM posts WHERE id = :pid"),
            {"pid": post_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="post not found")
        conn.execute(text("DELETE FROM reactions WHERE post_id = :pid"), {"pid": post_id})
        conn.execute(text("DELETE FROM posts WHERE id = :pid"), {"pid": post_id})
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Reactions (gold)
# ---------------------------------------------------------------------------


@app.post("/posts/{post_id}/reactions", status_code=201)
def create_reaction(post_id: int, body: ReactionCreate):
    now = _now()
    with engine.begin() as conn:
        post = conn.execute(
            text("SELECT id FROM posts WHERE id = :pid"), {"pid": post_id}
        ).fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="post not found")
        user_row = _fetch_user(conn, body.username)
        if not user_row:
            raise HTTPException(status_code=404, detail="user not found")
        try:
            conn.execute(
                text(
                    "INSERT INTO reactions (post_id, user_id, kind, created_at) "
                    "VALUES (:pid, :uid, :k, :ts)"
                ),
                {"pid": post_id, "uid": user_row[0], "k": body.kind, "ts": now},
            )
        except IntegrityError:
            raise HTTPException(
                status_code=409, detail="reaction already exists"
            )
        return {
            "post_id": post_id,
            "username": body.username,
            "kind": body.kind,
            "created_at": now,
        }


@app.get("/posts/{post_id}/reactions")
def list_reactions(post_id: int):
    with engine.connect() as conn:
        post = conn.execute(
            text("SELECT id FROM posts WHERE id = :pid"), {"pid": post_id}
        ).fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="post not found")
        rows = conn.execute(
            text(
                "SELECT u.username, r.kind, r.created_at "
                "FROM reactions r JOIN users u ON u.id = r.user_id "
                "WHERE r.post_id = :pid ORDER BY r.id ASC"
            ),
            {"pid": post_id},
        ).fetchall()
        return [
            {"username": uname, "kind": k, "created_at": c}
            for (uname, k, c) in rows
        ]


@app.delete("/posts/{post_id}/reactions/{username}", status_code=204)
def delete_reaction(post_id: int, username: str):
    with engine.begin() as conn:
        post = conn.execute(
            text("SELECT id FROM posts WHERE id = :pid"), {"pid": post_id}
        ).fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="post not found")
        user_row = _fetch_user(conn, username)
        if not user_row:
            raise HTTPException(status_code=404, detail="user not found")
        result = conn.execute(
            text("DELETE FROM reactions WHERE post_id = :pid AND user_id = :uid"),
            {"pid": post_id, "uid": user_row[0]},
        )
        if result.rowcount == 0:
            raise HTTPException(
                status_code=404, detail="no reactions from that user on this post"
            )
    return Response(status_code=204)
