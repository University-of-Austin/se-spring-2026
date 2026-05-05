import re
from datetime import datetime

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import text

from db import engine, init_db

app = FastAPI()


@app.on_event("startup")
def startup():
    init_db()


# --------------- Pydantic models ---------------

class CreateUser(BaseModel):
    username: str
    bio: str | None = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", v) or not (3 <= len(v) <= 20):
            raise ValueError("username must be 3-20 alphanumeric/underscore characters")
        return v

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 200:
            raise ValueError("bio must be at most 200 characters")
        return v


class UpdateUser(BaseModel):
    bio: str

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, v: str) -> str:
        if len(v) > 200:
            raise ValueError("bio must be at most 200 characters")
        return v


class CreatePost(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if len(v) == 0:
            raise ValueError("message must not be empty")
        if len(v) > 500:
            raise ValueError("message must be at most 500 characters")
        return v


class UpdatePost(BaseModel):
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if len(v) == 0:
            raise ValueError("message must not be empty")
        if len(v) > 500:
            raise ValueError("message must be at most 500 characters")
        return v


# --------------- Shape helpers ---------------

def user_shape(username: str, created_at: str, bio: str, post_count: int) -> dict:
    return {
        "username": username,
        "created_at": created_at,
        "bio": bio,
        "post_count": post_count,
    }


def post_shape(pid: int, username: str, message: str, created_at: str, updated_at: str | None) -> dict:
    return {
        "id": pid,
        "username": username,
        "message": message,
        "created_at": created_at,
        "updated_at": updated_at,
    }


# --------------- User endpoints ---------------

@app.post("/users", status_code=201)
def create_user(body: CreateUser):
    now = datetime.now().isoformat(timespec="seconds")
    bio = body.bio or ""
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT username FROM users WHERE username = :u"),
            {"u": body.username},
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="username already exists")
        conn.execute(
            text("INSERT INTO users (username, created_at, bio) VALUES (:u, :t, :b)"),
            {"u": body.username, "t": now, "b": bio},
        )
    return user_shape(body.username, now, bio, 0)


@app.get("/users")
def list_users():
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT u.username, u.created_at, u.bio, "
                "(SELECT COUNT(*) FROM posts WHERE user_id = u.id) AS post_count "
                "FROM users u ORDER BY u.username"
            )
        ).fetchall()
    return [user_shape(r[0], r[1], r[2], r[3]) for r in rows]


@app.get("/users/{username}")
def get_user(username: str):
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT u.username, u.created_at, u.bio, "
                "(SELECT COUNT(*) FROM posts WHERE user_id = u.id) AS post_count "
                "FROM users u WHERE u.username = :u"
            ),
            {"u": username},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return user_shape(row[0], row[1], row[2], row[3])


@app.patch("/users/{username}")
def update_user(username: str, body: UpdateUser):
    with engine.begin() as conn:
        user = conn.execute(
            text("SELECT id, created_at FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="user not found")
        conn.execute(
            text("UPDATE users SET bio = :b WHERE username = :u"),
            {"b": body.bio, "u": username},
        )
        count = conn.execute(
            text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"),
            {"uid": user[0]},
        ).scalar()
    return user_shape(username, user[1], body.bio, count)


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
                "SELECT id, message, created_at, updated_at "
                "FROM posts WHERE user_id = :uid ORDER BY created_at"
            ),
            {"uid": user[0]},
        ).fetchall()
    return [post_shape(r[0], username, r[1], r[2], r[3]) for r in rows]


# --------------- Post endpoints ---------------

@app.post("/posts", status_code=201)
def create_post(body: CreatePost, x_username: str | None = Header(None)):
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header is required")
    now = datetime.now().isoformat(timespec="seconds")
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
                "VALUES (:uid, :msg, :t)"
            ),
            {"uid": user[0], "msg": body.message, "t": now},
        )
        post_id = result.lastrowid
    return post_shape(post_id, x_username, body.message, now, None)


@app.get("/posts")
def list_posts(
    q: str | None = None,
    username: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    with engine.connect() as conn:
        where_clauses = []
        params: dict = {"limit": limit, "offset": offset}

        if username is not None:
            user = conn.execute(
                text("SELECT id FROM users WHERE username = :u"),
                {"u": username},
            ).fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="user not found")
            where_clauses.append("p.user_id = :uid")
            params["uid"] = user[0]

        if q:
            where_clauses.append("p.message LIKE :q")
            params["q"] = f"%{q}%"

        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        rows = conn.execute(
            text(
                "SELECT p.id, u.username, p.message, p.created_at, p.updated_at "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                f"{where_sql} "
                "ORDER BY p.created_at "
                "LIMIT :limit OFFSET :offset"
            ),
            params,
        ).fetchall()
    return [post_shape(r[0], r[1], r[2], r[3], r[4]) for r in rows]


@app.get("/posts/{post_id}")
def get_post(post_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT p.id, u.username, p.message, p.created_at, p.updated_at "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                "WHERE p.id = :pid"
            ),
            {"pid": post_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="post not found")
    return post_shape(row[0], row[1], row[2], row[3], row[4])


@app.patch("/posts/{post_id}")
def update_post(post_id: int, body: UpdatePost, x_username: str | None = Header(None)):
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header is required")
    now = datetime.now().isoformat(timespec="seconds")
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT p.id, u.username, p.created_at "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                "WHERE p.id = :pid"
            ),
            {"pid": post_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="post not found")
        if row[1] != x_username:
            raise HTTPException(status_code=403, detail="only the author can edit this post")
        conn.execute(
            text("UPDATE posts SET message = :msg, updated_at = :t WHERE id = :pid"),
            {"msg": body.message, "t": now, "pid": post_id},
        )
    return post_shape(post_id, row[1], body.message, row[2], now)


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int):
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM posts WHERE id = :pid"),
            {"pid": post_id},
        )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="post not found")
    return None
