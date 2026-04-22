"""
FastAPI app for the BBS webserver (Assignment 2).

Handlers map to the endpoints in the assignment spec and call helpers in db.py.
This layer is responsible for:
  - HTTP request parsing (Pydantic models, headers, query params)
  - Status code selection (201/204/400/404/409/422)
  - Composing db helpers when an endpoint needs multiple db operations
"""
from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field

import db

app = FastAPI()

# Initialize the database on import. SQLite's CREATE TABLE IF NOT EXISTS makes
# this safe to run every time uvicorn reloads the module.
db.init_db()


class UserCreate(BaseModel):
    # Spec: 3-20 chars, regex ^[a-zA-Z0-9_]+$
    username: str = Field(min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")


@app.post("/users", status_code=201)
def create_user(payload: UserCreate) -> dict:
    with db.engine.connect() as conn:
        user = db.create_user(conn, payload.username)
    # db returned None - username already taken
    if user is None:
        raise HTTPException(status_code=409, detail="username already exists")
    return user


@app.get("/users")
def list_users() -> list[dict]:
    with db.engine.connect() as conn:
        return db.list_users(conn)


@app.get("/users/{username}")
def get_user_by_username(username: str) -> dict:
    with db.engine.connect() as conn:
        user = db.get_user_by_username(conn, username)
    # db returned None - no such user
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


class UserUpdate(BaseModel):
    # Spec: optional string, max 200 chars
    bio: str = Field(max_length=200)


@app.patch("/users/{username}")
def update_user(username: str, payload: UserUpdate) -> dict:
    with db.engine.connect() as conn:
        user = db.update_user_bio(conn, username, payload.bio)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@app.get("/users/{username}/posts")
def list_user_posts(username: str) -> list[dict]:
    with db.engine.connect() as conn:
        # Check user exists - empty list from list_posts can't signal "no such user"
        if db.get_user_by_username(conn, username) is None:
            raise HTTPException(status_code=404, detail="user not found")
        return db.list_posts(conn, username=username)


class PostCreate(BaseModel):
    # Spec: non-empty string, max 500 chars
    message: str = Field(min_length=1, max_length=500)


@app.post("/posts", status_code=201)
def create_post(
    payload: PostCreate,
    x_username: str | None = Header(default=None),
) -> dict:
    # Spec: missing X-Username returns 400 (custom), not 422 from Pydantic
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header required")
    with db.engine.connect() as conn:
        post = db.create_post(conn, x_username, payload.message)
    # db.create_post returns None when the username does not exist (A2 does not
    # auto-create users). Spec maps this to 404.
    if post is None:
        raise HTTPException(status_code=404, detail="user not found")
    return post


@app.get("/posts")
def list_posts(
    q: str | None = Query(default=None),
    username: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    with db.engine.connect() as conn:
        return db.list_posts(conn, q=q, username=username, limit=limit, offset=offset)


@app.get("/posts/{post_id}")
def get_post_by_id(post_id: int) -> dict:
    with db.engine.connect() as conn:
        post = db.get_post_by_id(conn, post_id)
    # db returned None - no post with that id
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    return post


class PostUpdate(BaseModel):
    # Spec: same validation as PostCreate
    message: str = Field(min_length=1, max_length=500)


@app.patch("/posts/{post_id}")
def update_post(post_id: int, payload: PostUpdate) -> dict:
    with db.engine.connect() as conn:
        post = db.update_post_message(conn, post_id, payload.message)
    if post is None:
        raise HTTPException(status_code=404, detail="post not found")
    return post


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int) -> None:
    with db.engine.connect() as conn:
        deleted = db.delete_post(conn, post_id)
    # db.delete_post returns False when no row was deleted (id didn't exist).
    # Map that to 404 - not the idempotent 204 the REST textbook suggests.
    if not deleted:
        raise HTTPException(status_code=404, detail="post not found")
    return None
