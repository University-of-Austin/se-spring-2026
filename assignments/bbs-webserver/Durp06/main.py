"""FastAPI application — route handlers delegate all SQL to queries.py."""
import base64
import json
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

import queries as q
from db import get_engine, init_db


# ---------------------------------------------------------------------------
# Engine dependency
# ---------------------------------------------------------------------------

def get_engine_dep():
    """Return the application engine. Tests override this via dependency_overrides."""
    return app.state.engine


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _app.state.engine = get_engine()
    init_db(_app.state.engine)
    yield


app = FastAPI(lifespan=lifespan)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")
    bio: str = Field(default="", max_length=200)


class UserOut(BaseModel):
    username: str
    created_at: str
    bio: str
    post_count: int


class PostCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class PostOut(BaseModel):
    id: int
    username: str
    message: str
    created_at: str
    updated_at: str


class UserPatch(BaseModel):
    bio: str | None = Field(default=None, max_length=200)


class PostPatch(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)


class PostsPage(BaseModel):
    posts: list[PostOut]
    next_cursor: Optional[str]


# ---------------------------------------------------------------------------
# Cursor helpers
# ---------------------------------------------------------------------------

def encode_cursor(last_id: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"id": last_id}).encode()).decode()


def decode_cursor(raw: str) -> int:
    try:
        decoded = int(json.loads(base64.urlsafe_b64decode(raw.encode()).decode())["id"])
    except Exception:
        raise HTTPException(status_code=422, detail="invalid cursor")
    if decoded < 0:
        raise HTTPException(status_code=422, detail="invalid cursor")
    return decoded


# ---------------------------------------------------------------------------
# X-Username dependency
# ---------------------------------------------------------------------------

def require_username(x_username: Optional[str] = Header(default=None)) -> str:
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header required")
    return x_username


# ---------------------------------------------------------------------------
# User routes
# ---------------------------------------------------------------------------

@app.post("/users", status_code=201, response_model=UserOut)
def create_user(body: UserCreate, engine=Depends(get_engine_dep)):
    with engine.begin() as conn:
        try:
            user = q.create_user(conn, body.username, body.bio)
        except IntegrityError:
            raise HTTPException(status_code=409, detail="Username already exists")
    return user


@app.get("/users", response_model=list[UserOut])
def list_users(engine=Depends(get_engine_dep)):
    with engine.begin() as conn:
        return q.list_users(conn)


@app.get("/users/{username}", response_model=UserOut)
def get_user(username: str, engine=Depends(get_engine_dep)):
    with engine.begin() as conn:
        user = q.get_user(conn, username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.patch("/users/{username}", response_model=UserOut)
def patch_user(username: str, body: UserPatch, engine=Depends(get_engine_dep)):
    with engine.begin() as conn:
        if body.bio is None:
            # No-op: return current user state without writing to DB
            user = q.get_user(conn, username)
        else:
            user = q.update_user_bio(conn, username, body.bio)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users/{username}/posts", response_model=list[PostOut])
def list_user_posts(username: str, engine=Depends(get_engine_dep)):
    with engine.begin() as conn:
        posts = q.list_user_posts(conn, username)
    if posts is None:
        raise HTTPException(status_code=404, detail="User not found")
    return posts


# ---------------------------------------------------------------------------
# Post routes
# ---------------------------------------------------------------------------

@app.post("/posts", status_code=201, response_model=PostOut)
def create_post(
    body: PostCreate,
    x_username: str = Depends(require_username),
    engine=Depends(get_engine_dep),
):
    with engine.begin() as conn:
        try:
            post = q.create_post(conn, x_username, body.message)
        except q.UserNotFound:
            raise HTTPException(status_code=404, detail="User not found")
    return post


@app.get("/posts")
def list_posts(
    q_param: Optional[str] = Query(default=None, alias="q"),
    username: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    cursor: Optional[str] = Query(default=None),
    engine=Depends(get_engine_dep),
):
    with engine.begin() as conn:
        if cursor is not None:
            after_id = decode_cursor(cursor)
            posts = q.list_posts(conn, q=q_param, username=username, limit=limit, after_id=after_id)
            next_cursor = encode_cursor(posts[-1]["id"]) if len(posts) == limit else None
            return {"posts": [PostOut(**p).model_dump() for p in posts], "next_cursor": next_cursor}
        else:
            posts = q.list_posts(conn, q=q_param, username=username, limit=limit, offset=offset)
            return [PostOut(**p).model_dump() for p in posts]


@app.get("/posts/{post_id}", response_model=PostOut)
def get_post(post_id: int, engine=Depends(get_engine_dep)):
    with engine.begin() as conn:
        post = q.get_post(conn, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int, engine=Depends(get_engine_dep)):
    with engine.begin() as conn:
        deleted = q.delete_post(conn, post_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Post not found")


@app.patch("/posts/{post_id}", response_model=PostOut)
def patch_post(
    post_id: int,
    body: PostPatch,
    x_username: str = Depends(require_username),
    engine=Depends(get_engine_dep),
):
    with engine.begin() as conn:
        post = q.get_post(conn, post_id)
        if post is None:
            raise HTTPException(status_code=404, detail="Post not found")
        if post["username"] != x_username:
            raise HTTPException(status_code=403, detail="Forbidden: not the post author")
        updated = q.update_post_message(conn, post_id, body.message)
    return updated
