import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query,Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text

from db import engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


USERNAME_RE = re.compile(r"^[A-Za-z0-9_]+$")


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)

    @field_validator("username")
    @classmethod
    def _valid_chars(cls, v: str) -> str:
        if not USERNAME_RE.fullmatch(v):
            raise ValueError("username may only contain letters, digits, or underscores")
        return v


class PostCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.post("/users", status_code=201)
def create_user(payload: UserCreate):
    created_at = _now()
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT 1 FROM users WHERE username = :u"),
            {"u": payload.username},
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="username already exists")
        conn.execute(
            text("INSERT INTO users (username, created_at) VALUES (:u, :c)"),
            {"u": payload.username, "c": created_at},
        )
    return {"username": payload.username, "created_at": created_at}


@app.get("/users")
def list_users():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT username, created_at FROM users ORDER BY id")
        ).fetchall()
    return [{"username": r[0], "created_at": r[1]} for r in rows]


@app.get("/users/{username}")
def get_user(username: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT username, created_at FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return {"username": row[0], "created_at": row[1]}


@app.get("/users/{username}/posts")
def get_user_posts(username: str):
    with engine.connect() as conn:
        user = conn.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="user not found")
        rows = conn.execute(
            text(
                """
                SELECT p.id, u.username, p.message, p.created_at
                FROM posts p
                JOIN users u ON u.id = p.user_id
                WHERE u.username = :u
                ORDER BY p.id DESC
                """
            ),
            {"u": username},
        ).fetchall()
    return [
        {"id": r[0], "username": r[1], "message": r[2], "created_at": r[3]}
        for r in rows
    ]


@app.post("/posts", status_code=201)
def create_post(payload: PostCreate, x_username: Optional[str] = Header(default=None)):
    if not x_username:
        raise HTTPException(status_code=400, detail="X-Username header is required")
    created_at = _now()
    with engine.begin() as conn:
        user = conn.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": x_username},
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="user not found")
        result = conn.execute(
            text(
                "INSERT INTO posts (user_id, message, created_at) "
                "VALUES (:uid, :m, :c)"
            ),
            {"uid": user[0], "m": payload.message, "c": created_at},
        )
        post_id = result.lastrowid
    return {
        "id": post_id,
        "username": x_username,
        "message": payload.message,
        "created_at": created_at,
    }


@app.get("/posts")
def list_posts(
    q: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    sql = (
        "SELECT p.id, u.username, p.message, p.created_at "
        "FROM posts p JOIN users u ON u.id = p.user_id"
    )
    params: dict = {}
    if q is not None:
        sql += " WHERE p.message LIKE :q"
        params["q"] = f"%{q}%"
    sql += " ORDER BY p.id DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
    return [
        {"id": r[0], "username": r[1], "message": r[2], "created_at": r[3]}
        for r in rows
    ]


@app.get("/posts/{post_id}")
def get_post(post_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT p.id, u.username, p.message, p.created_at
                FROM posts p
                JOIN users u ON u.id = p.user_id
                WHERE p.id = :pid
                """
            ),
            {"pid": post_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="post not found")
    return {"id": row[0], "username": row[1], "message": row[2], "created_at": row[3]}


@app.delete("/posts/{post_id}")
def delete_post(post_id: int):
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM posts WHERE id = :pid"),
            {"pid": post_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="post not found")
    return Response(status_code=204)
