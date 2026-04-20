"""
BBS Webserver - Assignment 2 (Silver tier).

FastAPI wrapper around the SQLite BBS database. Resources: /users, /posts.

Silver features on top of Bronze:
  - user responses include `bio` and `post_count`
  - PATCH /users/{username} to update bio
  - PATCH /posts/{id} to edit message (adds updated_at to the post)
    Ownership policy: X-Username header must match the original author.
  - GET /posts?username=<name> to filter by author (composable with ?q=, ?limit=, ?offset=)
"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from db import engine, init_db

app = FastAPI(title="BBS Webserver")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


# ---------- Request bodies ----------

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")


class UserPatch(BaseModel):
    bio: Optional[str] = Field(None, max_length=200)


class PostCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class PostPatch(BaseModel):
    message: Optional[str] = Field(None, min_length=1, max_length=500)


# ---------- Helpers ----------

def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def fetch_user_row(conn, username: str):
    return conn.execute(
        text("SELECT id, username, created_at, bio FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()


def user_to_dict(conn, row) -> dict:
    """Shape a user row into the public response. Includes Silver post_count."""
    post_count = conn.execute(
        text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"),
        {"uid": row.id},
    ).scalar_one()
    return {
        "username": row.username,
        "created_at": row.created_at,
        "bio": row.bio,
        "post_count": post_count,
    }


def post_row_to_dict(row) -> dict:
    # Silver: always include updated_at (None until the post is edited).
    return {
        "id": row.id,
        "username": row.username,
        "message": row.message,
        "created_at": row.created_at,
        "updated_at": getattr(row, "updated_at", None),
    }


# ---------- /users ----------

@app.post("/users", status_code=201)
def create_user(body: UserCreate):
    with engine.begin() as conn:
        existing = fetch_user_row(conn, body.username)
        if existing:
            raise HTTPException(status_code=409, detail="username already exists")
        conn.execute(
            text("INSERT INTO users (username, created_at, bio) VALUES (:u, :c, NULL)"),
            {"u": body.username, "c": now_iso()},
        )
        row = fetch_user_row(conn, body.username)
        return user_to_dict(conn, row)


@app.get("/users")
def list_users():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, username, created_at, bio FROM users ORDER BY id")
        ).fetchall()
        return [user_to_dict(conn, r) for r in rows]


@app.get("/users/{username}")
def get_user(username: str):
    with engine.connect() as conn:
        row = fetch_user_row(conn, username)
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        return user_to_dict(conn, row)


@app.patch("/users/{username}")
def patch_user(username: str, body: UserPatch):
    with engine.begin() as conn:
        row = fetch_user_row(conn, username)
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        if body.bio is not None:
            conn.execute(
                text("UPDATE users SET bio = :b WHERE id = :id"),
                {"b": body.bio, "id": row.id},
            )
        row = fetch_user_row(conn, username)
        return user_to_dict(conn, row)


@app.get("/users/{username}/posts")
def get_posts_for_user(
    username: str,
    q: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    with engine.connect() as conn:
        user = fetch_user_row(conn, username)
        if not user:
            raise HTTPException(status_code=404, detail="user not found")

        sql = (
            "SELECT p.id, u.username, p.message, p.created_at, p.updated_at "
            "FROM posts p JOIN users u ON p.user_id = u.id "
            "WHERE u.username = :u"
        )
        params: dict = {"u": username}
        if q:
            sql += " AND p.message LIKE :q"
            params["q"] = f"%{q}%"
        sql += " ORDER BY p.id DESC LIMIT :lim OFFSET :off"
        params["lim"] = limit
        params["off"] = offset

        rows = conn.execute(text(sql), params).fetchall()
        return [post_row_to_dict(r) for r in rows]


# ---------- /posts ----------

@app.post("/posts", status_code=201)
def create_post(
    body: PostCreate,
    x_username: Optional[str] = Header(default=None, alias="X-Username"),
):
    if not x_username:
        raise HTTPException(status_code=400, detail="X-Username header required")

    with engine.begin() as conn:
        user = fetch_user_row(conn, x_username)
        if not user:
            raise HTTPException(status_code=404, detail="user not found")

        created = now_iso()
        result = conn.execute(
            text(
                "INSERT INTO posts (user_id, message, created_at) "
                "VALUES (:uid, :m, :c)"
            ),
            {"uid": user.id, "m": body.message, "c": created},
        )
        pid = result.lastrowid
        return {
            "id": pid,
            "username": user.username,
            "message": body.message,
            "created_at": created,
            "updated_at": None,
        }


@app.get("/posts")
def list_posts(
    q: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    with engine.connect() as conn:
        sql = (
            "SELECT p.id, u.username, p.message, p.created_at, p.updated_at "
            "FROM posts p JOIN users u ON p.user_id = u.id "
            "WHERE 1=1"
        )
        params: dict = {}
        if q:
            sql += " AND p.message LIKE :q"
            params["q"] = f"%{q}%"
        if username:
            sql += " AND u.username = :un"
            params["un"] = username
        sql += " ORDER BY p.id DESC LIMIT :lim OFFSET :off"
        params["lim"] = limit
        params["off"] = offset

        rows = conn.execute(text(sql), params).fetchall()
        return [post_row_to_dict(r) for r in rows]


@app.get("/posts/{post_id}")
def get_post(post_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT p.id, u.username, p.message, p.created_at, p.updated_at "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                "WHERE p.id = :id"
            ),
            {"id": post_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="post not found")
        return post_row_to_dict(row)


@app.patch("/posts/{post_id}")
def patch_post(
    post_id: int,
    body: PostPatch,
    x_username: Optional[str] = Header(default=None, alias="X-Username"),
):
    # Ownership policy: X-Username must match the original author.
    if not x_username:
        raise HTTPException(status_code=400, detail="X-Username header required")

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT p.id, u.username, p.message, p.created_at, p.updated_at "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                "WHERE p.id = :id"
            ),
            {"id": post_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="post not found")
        if row.username != x_username:
            raise HTTPException(status_code=403, detail="only the author can edit this post")

        if body.message is not None:
            conn.execute(
                text("UPDATE posts SET message = :m, updated_at = :u WHERE id = :id"),
                {"m": body.message, "u": now_iso(), "id": post_id},
            )

        row = conn.execute(
            text(
                "SELECT p.id, u.username, p.message, p.created_at, p.updated_at "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                "WHERE p.id = :id"
            ),
            {"id": post_id},
        ).fetchone()
        return post_row_to_dict(row)


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM posts WHERE id = :id"),
            {"id": post_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="post not found")
        conn.execute(text("DELETE FROM posts WHERE id = :id"), {"id": post_id})
    return None
