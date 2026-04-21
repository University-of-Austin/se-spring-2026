import re
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field, validator

from db import (
    init_db,
    create_user, get_user, get_all_users, update_user_bio, delete_user,
    create_post, get_post, get_posts, get_user_posts, get_thread,
    update_post_message, delete_post,
    create_board, get_board, get_all_boards,
    create_reaction, get_reactions, delete_reaction,
    VALID_REACTIONS,
)

app = FastAPI()


@app.on_event("startup")
def startup():
    init_db()


# ── Pydantic models ───────────────────────────────────────────────

class CreateUser(BaseModel):
    username: str = Field(min_length=3, max_length=20)

    @validator("username")
    def username_allowed_chars(cls, v):
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("username: only letters, digits, and underscores allowed")
        return v


class CreatePost(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    board: Optional[str] = None
    parent_id: Optional[int] = None


class UpdateBio(BaseModel):
    bio: str = Field(max_length=200)


class UpdateMessage(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class CreateBoard(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: Optional[str] = None

    @validator("name")
    def name_allowed_chars(cls, v):
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("name: only letters, digits, underscores, and dashes allowed")
        return v


class CreateReaction(BaseModel):
    kind: str

    @validator("kind")
    def kind_must_be_valid(cls, v):
        if v not in VALID_REACTIONS:
            raise ValueError(f"kind must be one of: {', '.join(sorted(VALID_REACTIONS))}")
        return v


# ── User endpoints ────────────────────────────────────────────────

@app.post("/users", status_code=201)
def post_users(body: CreateUser):
    user = create_user(body.username)
    if user is None:
        raise HTTPException(status_code=409, detail="Username already exists")
    return user


@app.get("/users")
def list_users():
    return get_all_users()


@app.get("/users/{username}")
def get_single_user(username: str):
    user = get_user(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.patch("/users/{username}")
def patch_user(username: str, body: UpdateBio):
    user = update_user_bio(username, body.bio)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users/{username}/posts")
def get_posts_by_user(username: str):
    user = get_user(username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return get_user_posts(username)


@app.delete("/users/{username}", status_code=204)
def delete_single_user(username: str, request: Request):
    x_username = request.headers.get("x-username")
    if x_username is None:
        raise HTTPException(status_code=400, detail="Missing X-Username header")
    caller = get_user(x_username)
    if caller is None:
        raise HTTPException(status_code=404, detail="User not found")
    if x_username != username:
        raise HTTPException(status_code=403, detail="You can only delete your own account")
    if not delete_user(username):
        raise HTTPException(status_code=404, detail="User not found")
    return Response(status_code=204)


# ── Post endpoints ────────────────────────────────────────────────

@app.post("/posts", status_code=201)
def post_posts(body: CreatePost, request: Request):
    x_username = request.headers.get("x-username")
    if x_username is None:
        raise HTTPException(status_code=400, detail="Missing X-Username header")
    user = get_user(x_username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    result = create_post(x_username, body.message, board=body.board, parent_id=body.parent_id)
    if isinstance(result, dict) and result.get("_error") == "board_not_found":
        raise HTTPException(status_code=404, detail="Board not found")
    if isinstance(result, dict) and result.get("_error") == "parent_not_found":
        raise HTTPException(status_code=404, detail="Parent post not found")
    return result


@app.get("/posts")
def list_posts(
    q: Optional[str] = None,
    username: Optional[str] = None,
    board: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    cursor: Optional[str] = None,
    include_replies: bool = False,
):
    result = get_posts(
        q=q, username=username, board=board,
        limit=limit, offset=offset, cursor=cursor,
        include_replies=include_replies,
    )
    # If cursor was used, return envelope; otherwise return bare array for backwards compat
    if cursor is not None:
        return result
    return result["posts"]


@app.get("/posts/{post_id}")
def get_single_post(post_id: int):
    post = get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@app.get("/posts/{post_id}/thread")
def get_post_thread(post_id: int):
    thread = get_thread(post_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return thread


@app.patch("/posts/{post_id}")
def patch_post(post_id: int, body: UpdateMessage, request: Request):
    x_username = request.headers.get("x-username")
    if x_username is None:
        raise HTTPException(status_code=400, detail="Missing X-Username header")
    user = get_user(x_username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    post = get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["username"] != x_username:
        raise HTTPException(status_code=403, detail="You can only edit your own posts")
    return update_post_message(post_id, body.message)


@app.delete("/posts/{post_id}", status_code=204)
def delete_single_post(post_id: int, request: Request):
    x_username = request.headers.get("x-username")
    if x_username is None:
        raise HTTPException(status_code=400, detail="Missing X-Username header")
    user = get_user(x_username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    post = get_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["username"] != x_username:
        raise HTTPException(status_code=403, detail="You can only delete your own posts")
    if not delete_post(post_id):
        raise HTTPException(status_code=404, detail="Post not found")
    return Response(status_code=204)


# ── Board endpoints ───────────────────────────────────────────────

@app.post("/boards", status_code=201)
def post_boards(body: CreateBoard):
    board = create_board(body.name, body.description)
    if board is None:
        raise HTTPException(status_code=409, detail="Board already exists")
    return board


@app.get("/boards")
def list_boards():
    return get_all_boards()


@app.get("/boards/{name}")
def get_single_board(name: str):
    board = get_board(name)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return board


@app.get("/boards/{name}/posts")
def get_board_posts(
    name: str,
    q: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    cursor: Optional[str] = None,
    include_replies: bool = False,
):
    board = get_board(name)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    result = get_posts(
        q=q, board=name, limit=limit, offset=offset, cursor=cursor,
        include_replies=include_replies,
    )
    if cursor is not None:
        return result
    return result["posts"]


# ── Reaction endpoints ────────────────────────────────────────────

@app.post("/posts/{post_id}/reactions", status_code=201)
def post_reaction(post_id: int, body: CreateReaction, request: Request):
    x_username = request.headers.get("x-username")
    if x_username is None:
        raise HTTPException(status_code=400, detail="Missing X-Username header")
    user = get_user(x_username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    result = create_reaction(post_id, x_username, body.kind)
    if result.get("_error") == "post_not_found":
        raise HTTPException(status_code=404, detail="Post not found")
    return result


@app.get("/posts/{post_id}/reactions")
def list_reactions(post_id: int):
    reactions = get_reactions(post_id)
    if reactions is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return reactions


@app.delete("/posts/{post_id}/reactions/{username}", status_code=204)
def delete_user_reaction(post_id: int, username: str, request: Request):
    x_username = request.headers.get("x-username")
    if x_username is None:
        raise HTTPException(status_code=400, detail="Missing X-Username header")
    caller = get_user(x_username)
    if caller is None:
        raise HTTPException(status_code=404, detail="User not found")
    if x_username != username:
        raise HTTPException(status_code=403, detail="You can only delete your own reactions")
    result = delete_reaction(post_id, username)
    if result is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if not result:
        raise HTTPException(status_code=404, detail="No reactions found for this user on this post")
    return Response(status_code=204)
