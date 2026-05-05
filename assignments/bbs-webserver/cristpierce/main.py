"""BBS Webserver API — Gold+ tier.

Run with: uvicorn main:app --port 8000
"""

import base64
import json
import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text

from db import engine, init_db

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="BBS Webserver API", version="1.0.0")

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CreateUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)

    @field_validator("username")
    @classmethod
    def username_alphanum(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Username must contain only letters, digits, and underscores")
        return v


class CreatePost(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class UpdateBio(BaseModel):
    bio: str = Field(..., max_length=200)


class UpdatePost(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class CreateBoard(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def name_valid(cls, v: str) -> str:
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Board name must contain only letters, digits, underscores, and hyphens")
        return v


class CreateReaction(BaseModel):
    username: str = Field(..., min_length=1)
    kind: str = Field(..., min_length=1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_response(row) -> dict:
    """Build a user response dict with silver fields."""
    return {
        "username": row["username"],
        "created_at": row["created_at"],
        "bio": row["bio"],
        "post_count": row["post_count"],
    }


def _post_response(row) -> dict:
    """Build a post response dict with silver fields."""
    resp = {
        "id": row["id"],
        "username": row["username"],
        "message": row["message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    return resp


def _encode_cursor(post_id: int) -> str:
    """Encode a post ID as a base64 cursor."""
    return base64.urlsafe_b64encode(json.dumps({"id": post_id}).encode()).decode()


def _decode_cursor(cursor: str) -> int:
    """Decode a base64 cursor to a post ID."""
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor))
        return int(data["id"])
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid cursor")


# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def landing_page():
    with engine.begin() as conn:
        user_count = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
        post_count = conn.execute(text("SELECT COUNT(*) FROM posts")).fetchone()[0]
        board_count = conn.execute(text("SELECT COUNT(*) FROM boards")).fetchone()[0]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BBS Webserver API</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="terminal">
        <div class="scanline"></div>
        <div class="header">
            <pre class="ascii-art">
 ____  ____  ____
| __ )| __ )/ ___|
|  _ \\|  _ \\___ \\
| |_) | |_) |__) |
|____/|____/____/
 W E B S E R V E R   A P I
            </pre>
            <p class="subtitle">A RESTful BBS API built with FastAPI</p>
        </div>

        <div class="stats-bar">
            <span class="stat"><span class="label">USERS</span> <span class="value">{user_count}</span></span>
            <span class="stat"><span class="label">POSTS</span> <span class="value">{post_count}</span></span>
            <span class="stat"><span class="label">BOARDS</span> <span class="value">{board_count}</span></span>
        </div>

        <div class="section">
            <h2>&gt; API Documentation</h2>
            <div class="links">
                <a href="/docs" class="btn">Swagger UI &rarr;</a>
                <a href="/redoc" class="btn">ReDoc &rarr;</a>
            </div>
        </div>

        <div class="section">
            <h2>&gt; Endpoints</h2>
            <table>
                <tr><th>Method</th><th>Path</th><th>Description</th></tr>
                <tr><td class="method post">POST</td><td>/users</td><td>Create a user</td></tr>
                <tr><td class="method get">GET</td><td>/users</td><td>List all users</td></tr>
                <tr><td class="method get">GET</td><td>/users/{{username}}</td><td>Get one user</td></tr>
                <tr><td class="method get">GET</td><td>/users/{{username}}/posts</td><td>Posts by user</td></tr>
                <tr><td class="method patch">PATCH</td><td>/users/{{username}}</td><td>Update bio</td></tr>
                <tr><td class="method post">POST</td><td>/posts</td><td>Create a post</td></tr>
                <tr><td class="method get">GET</td><td>/posts</td><td>List &amp; search posts</td></tr>
                <tr><td class="method get">GET</td><td>/posts/{{id}}</td><td>Get one post</td></tr>
                <tr><td class="method patch">PATCH</td><td>/posts/{{id}}</td><td>Edit post message</td></tr>
                <tr><td class="method delete">DELETE</td><td>/posts/{{id}}</td><td>Delete a post</td></tr>
                <tr><td class="method post">POST</td><td>/boards</td><td>Create a board</td></tr>
                <tr><td class="method get">GET</td><td>/boards</td><td>List boards</td></tr>
                <tr><td class="method get">GET</td><td>/boards/{{name}}/posts</td><td>Posts in a board</td></tr>
                <tr><td class="method get">GET</td><td>/feed</td><td>Recent posts feed</td></tr>
                <tr><td class="method post">POST</td><td>/posts/{{id}}/reactions</td><td>Add reaction</td></tr>
                <tr><td class="method delete">DELETE</td><td>/posts/{{id}}/reactions/{{username}}</td><td>Remove reaction</td></tr>
            </table>
        </div>

        <div class="section">
            <h2>&gt; Quick Start</h2>
            <pre class="code-block">
# Create a user
curl -X POST http://localhost:8000/users \\
  -H "Content-Type: application/json" \\
  -d '{{"username": "alice"}}'

# Create a post
curl -X POST http://localhost:8000/posts \\
  -H "Content-Type: application/json" \\
  -H "X-Username: alice" \\
  -d '{{"message": "Hello, BBS!"}}'

# List posts
curl http://localhost:8000/posts

# Search posts
curl "http://localhost:8000/posts?q=hello"</pre>
        </div>

        <div class="footer">
            <p>Assignment 2 &mdash; Software Engineering &mdash; UATX Spring 2026</p>
            <p class="dim">Gold+ Tier &bull; cristpierce</p>
        </div>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html)


# ===================================================================
# BRONZE ENDPOINTS
# ===================================================================

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@app.post("/users", status_code=201)
def create_user(body: CreateUser):
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT username FROM users WHERE username = :u"),
            {"u": body.username},
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists")

        now = datetime.now().isoformat()
        conn.execute(
            text("INSERT INTO users (username, bio, created_at) VALUES (:u, NULL, :c)"),
            {"u": body.username, "c": now},
        )
        return {"username": body.username, "created_at": now, "bio": None, "post_count": 0}


@app.get("/users")
def list_users():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT u.username, u.created_at, u.bio,
                   (SELECT COUNT(*) FROM posts p WHERE p.username = u.username) as post_count
            FROM users u ORDER BY u.created_at ASC
        """)).fetchall()
        return [_user_response(dict(r._mapping)) for r in rows]


@app.get("/users/{username}")
def get_user(username: str):
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT u.username, u.created_at, u.bio,
                   (SELECT COUNT(*) FROM posts p WHERE p.username = u.username) as post_count
            FROM users u WHERE u.username = :u
        """), {"u": username}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return _user_response(dict(row._mapping))


@app.get("/users/{username}/posts")
def get_user_posts(username: str):
    with engine.begin() as conn:
        user = conn.execute(
            text("SELECT username FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        rows = conn.execute(text("""
            SELECT id, username, message, created_at, updated_at
            FROM posts WHERE username = :u ORDER BY created_at DESC
        """), {"u": username}).fetchall()
        return [_post_response(dict(r._mapping)) for r in rows]


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

@app.post("/posts", status_code=201)
def create_post(body: CreatePost, x_username: Optional[str] = Header(None)):
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header is required")

    with engine.begin() as conn:
        user = conn.execute(
            text("SELECT username FROM users WHERE username = :u"),
            {"u": x_username},
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        now = datetime.now().isoformat()
        conn.execute(
            text("INSERT INTO posts (username, message, created_at) VALUES (:u, :m, :c)"),
            {"u": x_username, "m": body.message, "c": now},
        )
        row = conn.execute(text("SELECT last_insert_rowid()")).fetchone()
        post_id = row[0]

        return {
            "id": post_id,
            "username": x_username,
            "message": body.message,
            "created_at": now,
            "updated_at": None,
        }


@app.get("/posts")
def list_posts(
    q: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    cursor: Optional[str] = None,
):
    with engine.begin() as conn:
        conditions = []
        params: dict = {}

        if q:
            conditions.append("message LIKE :q")
            params["q"] = f"%{q}%"

        if username:
            conditions.append("username = :username")
            params["username"] = username

        if cursor:
            cursor_id = _decode_cursor(cursor)
            conditions.append("id < :cursor_id")
            params["cursor_id"] = cursor_id

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        # For cursor pagination, always order by id DESC
        if cursor:
            query = f"SELECT id, username, message, created_at, updated_at FROM posts {where} ORDER BY id DESC LIMIT :lim"
            params["lim"] = limit
        else:
            query = f"SELECT id, username, message, created_at, updated_at FROM posts {where} ORDER BY created_at DESC LIMIT :lim OFFSET :off"
            params["lim"] = limit
            params["off"] = offset

        rows = conn.execute(text(query), params).fetchall()
        posts = [_post_response(dict(r._mapping)) for r in rows]

        # Cursor pagination returns envelope
        if cursor is not None or (cursor is None and "cursor" in str(params)):
            pass  # only return envelope when cursor param was explicitly provided

        # If cursor was used, return envelope format
        if cursor is not None:
            next_cursor = None
            if len(posts) == limit and posts:
                next_cursor = _encode_cursor(posts[-1]["id"])
            return {"posts": posts, "next_cursor": next_cursor}

        return posts


@app.get("/posts/{post_id}")
def get_post(post_id: int):
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT id, username, message, created_at, updated_at
            FROM posts WHERE id = :pid
        """), {"pid": post_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        return _post_response(dict(row._mapping))


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int):
    with engine.begin() as conn:
        # Delete associated reactions first
        conn.execute(text("DELETE FROM reactions WHERE post_id = :pid"), {"pid": post_id})
        result = conn.execute(text("DELETE FROM posts WHERE id = :pid"), {"pid": post_id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Post not found")
        return None


# ===================================================================
# SILVER ENDPOINTS
# ===================================================================

@app.patch("/users/{username}")
def update_user(username: str, body: UpdateBio):
    with engine.begin() as conn:
        user = conn.execute(
            text("SELECT username FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        conn.execute(
            text("UPDATE users SET bio = :bio WHERE username = :u"),
            {"bio": body.bio, "u": username},
        )

        row = conn.execute(text("""
            SELECT u.username, u.created_at, u.bio,
                   (SELECT COUNT(*) FROM posts p WHERE p.username = u.username) as post_count
            FROM users u WHERE u.username = :u
        """), {"u": username}).fetchone()
        return _user_response(dict(row._mapping))


@app.patch("/posts/{post_id}")
def update_post(post_id: int, body: UpdatePost, x_username: Optional[str] = Header(None)):
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header is required")

    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT id, username, message, created_at, updated_at
            FROM posts WHERE id = :pid
        """), {"pid": post_id}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")

        post = dict(row._mapping)
        if post["username"] != x_username:
            raise HTTPException(status_code=403, detail="Only the original author can edit this post")

        now = datetime.now().isoformat()
        conn.execute(
            text("UPDATE posts SET message = :m, updated_at = :u WHERE id = :pid"),
            {"m": body.message, "u": now, "pid": post_id},
        )

        updated = conn.execute(text("""
            SELECT id, username, message, created_at, updated_at
            FROM posts WHERE id = :pid
        """), {"pid": post_id}).fetchone()
        return _post_response(dict(updated._mapping))


# ===================================================================
# GOLD ENDPOINTS
# ===================================================================

# ---------------------------------------------------------------------------
# Boards
# ---------------------------------------------------------------------------

@app.post("/boards", status_code=201)
def create_board(body: CreateBoard):
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT name FROM boards WHERE name = :n"),
            {"n": body.name},
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Board already exists")

        now = datetime.now().isoformat()
        conn.execute(
            text("INSERT INTO boards (name, created_at) VALUES (:n, :c)"),
            {"n": body.name, "c": now},
        )
        return {"name": body.name, "created_at": now}


@app.get("/boards")
def list_boards():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT b.name, b.created_at,
                   (SELECT COUNT(*) FROM posts p WHERE p.board = b.name) as post_count
            FROM boards b ORDER BY b.name ASC
        """)).fetchall()
        return [{"name": r[0], "created_at": r[1], "post_count": r[2]} for r in rows]


@app.get("/boards/{name}/posts")
def get_board_posts(
    name: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    with engine.begin() as conn:
        board = conn.execute(
            text("SELECT name FROM boards WHERE name = :n"),
            {"n": name},
        ).fetchone()
        if not board:
            raise HTTPException(status_code=404, detail="Board not found")

        rows = conn.execute(text("""
            SELECT id, username, message, created_at, updated_at
            FROM posts WHERE board = :n ORDER BY created_at DESC LIMIT :lim OFFSET :off
        """), {"n": name, "lim": limit, "off": offset}).fetchall()
        return [_post_response(dict(r._mapping)) for r in rows]


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------

@app.get("/feed")
def feed(
    limit: int = Query(default=50, ge=1, le=200),
    since: Optional[str] = None,
):
    with engine.begin() as conn:
        if since:
            rows = conn.execute(text("""
                SELECT id, username, message, created_at, updated_at
                FROM posts WHERE created_at > :since
                ORDER BY created_at DESC LIMIT :lim
            """), {"since": since, "lim": limit}).fetchall()
        else:
            rows = conn.execute(text("""
                SELECT id, username, message, created_at, updated_at
                FROM posts ORDER BY created_at DESC LIMIT :lim
            """), {"lim": limit}).fetchall()
        return [_post_response(dict(r._mapping)) for r in rows]


# ---------------------------------------------------------------------------
# Reactions
# ---------------------------------------------------------------------------

@app.post("/posts/{post_id}/reactions", status_code=201)
def add_reaction(post_id: int, body: CreateReaction):
    with engine.begin() as conn:
        post = conn.execute(
            text("SELECT id FROM posts WHERE id = :pid"),
            {"pid": post_id},
        ).fetchone()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        user = conn.execute(
            text("SELECT username FROM users WHERE username = :u"),
            {"u": body.username},
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        existing = conn.execute(
            text("SELECT id FROM reactions WHERE post_id = :pid AND username = :u"),
            {"pid": post_id, "u": body.username},
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="User already reacted to this post")

        conn.execute(
            text("INSERT INTO reactions (post_id, username, kind) VALUES (:pid, :u, :k)"),
            {"pid": post_id, "u": body.username, "k": body.kind},
        )
        return {"post_id": post_id, "username": body.username, "kind": body.kind}


@app.delete("/posts/{post_id}/reactions/{username}", status_code=204)
def remove_reaction(post_id: int, username: str):
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM reactions WHERE post_id = :pid AND username = :u"),
            {"pid": post_id, "u": username},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Reaction not found")
        return None
