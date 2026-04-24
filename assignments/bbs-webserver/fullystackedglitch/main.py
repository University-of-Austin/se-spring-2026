from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from db import engine, init_db


USERNAME_PATTERN = r"^[a-zA-Z0-9_]+$"


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=USERNAME_PATTERN)


class UserPatchIn(BaseModel):
    bio: Optional[str] = Field(default=None, max_length=200)


class PostIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class PostPatchIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


def user_shape(conn, row) -> dict:
    """row: (id, username, bio, created_at). Computes post_count on the fly."""
    user_id, username, bio, created_at = row
    count = conn.execute(
        text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"),
        {"uid": user_id},
    ).scalar_one()
    return {
        "username": username,
        "created_at": created_at,
        "bio": bio or "",
        "post_count": count,
    }


def post_shape(row, include_updated_at: bool = False) -> dict:
    """row: (id, username, message, created_at[, updated_at])."""
    obj = {
        "id": row[0],
        "username": row[1],
        "message": row[2],
        "created_at": row[3],
    }
    if include_updated_at:
        obj["updated_at"] = row[4]
    return obj


# ----------------------------- Users -----------------------------

@app.post("/users", status_code=201)
def create_user(body: UserIn):
    now = datetime.now().isoformat()
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": body.username},
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists")

        conn.execute(
            text("INSERT INTO users (username, bio, created_at) VALUES (:u, '', :ts)"),
            {"u": body.username, "ts": now},
        )
        row = conn.execute(
            text("SELECT id, username, bio, created_at FROM users WHERE username = :u"),
            {"u": body.username},
        ).fetchone()
        return user_shape(conn, row)


@app.get("/users")
def list_users():
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, username, bio, created_at FROM users ORDER BY username"
        )).fetchall()
        return [user_shape(conn, r) for r in rows]


@app.get("/users/{username}")
def get_user(username: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, username, bio, created_at FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return user_shape(conn, row)


@app.get("/users/{username}/posts")
def get_user_posts(username: str):
    with engine.connect() as conn:
        user = conn.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        rows = conn.execute(
            text("""
                SELECT p.id, u.username, p.message, p.created_at
                FROM posts p JOIN users u ON p.user_id = u.id
                WHERE u.username = :u
                ORDER BY p.created_at DESC, p.id DESC
            """),
            {"u": username},
        ).fetchall()
        return [post_shape(r) for r in rows]


@app.patch("/users/{username}")
def patch_user(username: str, body: UserPatchIn):
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="User not found")

        if body.bio is not None:
            conn.execute(
                text("UPDATE users SET bio = :bio WHERE username = :u"),
                {"bio": body.bio, "u": username},
            )

        row = conn.execute(
            text("SELECT id, username, bio, created_at FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        return user_shape(conn, row)


# ----------------------------- Posts -----------------------------

@app.post("/posts", status_code=201)
def create_post(
    body: PostIn,
    x_username: Optional[str] = Header(default=None, alias="X-Username"),
):
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header required")

    now = datetime.now().isoformat()
    with engine.begin() as conn:
        user = conn.execute(
            text("SELECT id, username FROM users WHERE username = :u"),
            {"u": x_username},
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        result = conn.execute(
            text("""
                INSERT INTO posts (user_id, message, created_at, updated_at)
                VALUES (:uid, :msg, :ts, NULL)
            """),
            {"uid": user[0], "msg": body.message, "ts": now},
        )
        return {
            "id": result.lastrowid,
            "username": user[1],
            "message": body.message,
            "created_at": now,
        }


@app.get("/posts")
def list_posts(
    q: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    sql = (
        "SELECT p.id, u.username, p.message, p.created_at "
        "FROM posts p JOIN users u ON p.user_id = u.id "
        "WHERE 1=1"
    )
    params: dict = {"limit": limit, "offset": offset}
    if q:
        sql += " AND p.message LIKE :q"
        params["q"] = f"%{q}%"
    if username:
        sql += " AND u.username = :username"
        params["username"] = username
    sql += " ORDER BY p.created_at DESC, p.id DESC LIMIT :limit OFFSET :offset"

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
    return [post_shape(r) for r in rows]


@app.get("/posts/{post_id}")
def get_post(post_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT p.id, u.username, p.message, p.created_at
                FROM posts p JOIN users u ON p.user_id = u.id
                WHERE p.id = :id
            """),
            {"id": post_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        return post_shape(row)


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM posts WHERE id = :id"),
            {"id": post_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        conn.execute(text("DELETE FROM posts WHERE id = :id"), {"id": post_id})


@app.patch("/posts/{post_id}")
def patch_post(
    post_id: int,
    body: PostPatchIn,
    x_username: Optional[str] = Header(default=None, alias="X-Username"),
):
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header required")

    now = datetime.now().isoformat()
    with engine.begin() as conn:
        row = conn.execute(
            text("""
                SELECT p.id, u.username, p.message, p.created_at, p.updated_at
                FROM posts p JOIN users u ON p.user_id = u.id
                WHERE p.id = :id
            """),
            {"id": post_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        if row[1] != x_username:
            raise HTTPException(status_code=403, detail="Only the author can edit this post")

        conn.execute(
            text("UPDATE posts SET message = :msg, updated_at = :ts WHERE id = :id"),
            {"msg": body.message, "ts": now, "id": post_id},
        )
        updated = conn.execute(
            text("""
                SELECT p.id, u.username, p.message, p.created_at, p.updated_at
                FROM posts p JOIN users u ON p.user_id = u.id
                WHERE p.id = :id
            """),
            {"id": post_id},
        ).fetchone()
        return post_shape(updated, include_updated_at=True)
