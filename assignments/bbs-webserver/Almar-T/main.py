"""
main.py - FastAPI BBS webserver (gold tier).

Endpoints
  bronze:
    POST   /users                            create a user
    GET    /users                            list users
    GET    /users/{username}                 one user
    GET    /users/{username}/posts           that user's posts
    POST   /posts                            create a post (X-Username header)
    GET    /posts                            list posts (?q=, ?limit=, ?offset=, ?username=)
    GET    /posts/{id}                       one post
    DELETE /posts/{id}                       hard-delete a post

  silver:
    PATCH  /users/{username}                 update bio
    PATCH  /posts/{id}                       edit message (author-only)

  gold (reactions):
    POST   /posts/{id}/reactions             add a reaction
    DELETE /posts/{id}/reactions/{username}  remove that user's reactions
    GET    /posts/{id}/reactions             list reactions on a post

  gold (boards):
    POST   /boards                           create a board
    GET    /boards                           list boards
    GET    /boards/{name}/posts              posts in a board

Implementation notes
  - Response shapes are enforced by Pydantic response_model: FastAPI
    strips anything not declared in the model, so we can't accidentally
    leak DB columns to clients.
  - SQL-column -> API-field renames happen in the SELECT itself
    (`p.timestamp AS created_at`, `r.emoji AS kind`). The A1 CLI still
    reads rows by their original column names.
  - Each handler runs inside a single SQLAlchemy connection;
    `engine.begin()` wraps mutations in a transaction.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from db import engine, init_db

USERNAME_PATTERN = r"^[a-zA-Z0-9_]+$"
BOARD_NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"


# ---------------------------------------------------------------------------
# Pydantic — request bodies
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=USERNAME_PATTERN)


class UserPatch(BaseModel):
    bio: Optional[str] = Field(default=None, max_length=200)


class PostCreate(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    board: Optional[str] = Field(
        default=None, min_length=1, max_length=50, pattern=BOARD_NAME_PATTERN
    )


class PostPatch(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class ReactionCreate(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=USERNAME_PATTERN)
    kind: str = Field(min_length=1, max_length=20)


class BoardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50, pattern=BOARD_NAME_PATTERN)
    description: Optional[str] = Field(default="", max_length=200)


# ---------------------------------------------------------------------------
# Pydantic — response models (spec-exact shapes)
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    username: str
    created_at: str
    bio: str = ""
    post_count: int


class PostOut(BaseModel):
    id: int
    username: str
    message: str
    created_at: str
    updated_at: Optional[str] = None
    board: str


class ReactionOut(BaseModel):
    post_id: int
    username: str
    kind: str


class BoardOut(BaseModel):
    name: str
    description: str = ""
    created_at: str


# ---------------------------------------------------------------------------
# Lifespan — schema migrations run on app startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="BBS Webserver", lifespan=lifespan)


# ---------------------------------------------------------------------------
# Data helpers — fetchers + "require X or 404" guards
# ---------------------------------------------------------------------------

def _now_iso():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _fetch_user(conn, username):
    """Return a user mapping with post_count, or None."""
    return conn.execute(text("""
        SELECT id,
               username,
               created_at,
               COALESCE(bio, '') AS bio,
               (SELECT COUNT(*) FROM posts WHERE user_id = users.id) AS post_count
        FROM users
        WHERE username = :u
    """), {"u": username}).mappings().first()


def _require_user(conn, username):
    row = _fetch_user(conn, username)
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return row


def _require_post_exists(conn, post_id):
    row = conn.execute(
        text("SELECT 1 FROM posts WHERE id = :id"), {"id": post_id}
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="post not found")


def _fetch_board(conn, name):
    return conn.execute(text("""
        SELECT name, COALESCE(description, '') AS description, created_at
        FROM boards
        WHERE name = :n
    """), {"n": name}).mappings().first()


def _require_board(conn, name):
    row = _fetch_board(conn, name)
    if not row:
        raise HTTPException(status_code=404, detail="board not found")
    return row


# Base SELECT used by every list/get-post endpoint. Column aliases
# (`p.timestamp AS created_at`) match PostOut field names so the
# mapping rows serialize directly.
POST_BASE_SQL = """
    SELECT p.id,
           u.username,
           p.message,
           p.timestamp  AS created_at,
           p.updated_at,
           p.board
    FROM posts p
    JOIN users u ON u.id = p.user_id
"""


def _select_posts(conn, *, where="", params=None, q=None, limit, offset):
    """Run POST_BASE_SQL with optional extra WHERE + q search + pagination.

    `where` and `params` are the caller's authored clause + bindings;
    user input only ever reaches the query through :name placeholders.
    """
    clauses = []
    bind = dict(params or {})
    bind["lim"] = limit
    bind["off"] = offset
    if where:
        clauses.append(where)
    if q:
        clauses.append("p.message LIKE :q")
        bind["q"] = f"%{q}%"
    full_where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = POST_BASE_SQL + full_where + " ORDER BY p.id DESC LIMIT :lim OFFSET :off"
    return conn.execute(text(sql), bind).mappings().all()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

@app.post("/users", status_code=201, response_model=UserOut)
def create_user(body: UserCreate):
    with engine.begin() as conn:
        if _fetch_user(conn, body.username):
            raise HTTPException(status_code=409, detail="username already exists")
        conn.execute(
            text("INSERT INTO users (username, bio, created_at) VALUES (:u, '', :t)"),
            {"u": body.username, "t": _now_iso()},
        )
        return _fetch_user(conn, body.username)


@app.get("/users", response_model=List[UserOut])
def list_users():
    # Single GROUP BY query avoids the N+1 pattern of SELECT-then-count-per-user.
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT u.username,
                   u.created_at,
                   COALESCE(u.bio, '') AS bio,
                   COUNT(p.id) AS post_count
            FROM users u
            LEFT JOIN posts p ON p.user_id = u.id
            GROUP BY u.id
            ORDER BY u.id
        """)).mappings().all()


@app.get("/users/{username}", response_model=UserOut)
def get_user(username: str):
    with engine.connect() as conn:
        return _require_user(conn, username)


@app.get("/users/{username}/posts", response_model=List[PostOut])
def list_user_posts(
    username: str,
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    with engine.connect() as conn:
        _require_user(conn, username)
        return _select_posts(
            conn,
            where="u.username = :au",
            params={"au": username},
            q=q, limit=limit, offset=offset,
        )


@app.patch("/users/{username}", response_model=UserOut)
def patch_user(username: str, body: UserPatch):
    with engine.begin() as conn:
        _require_user(conn, username)
        # PATCH contract: missing / null `bio` is a no-op; explicit ""
        # clears the bio.
        if body.bio is not None:
            conn.execute(
                text("UPDATE users SET bio = :b WHERE username = :u"),
                {"b": body.bio, "u": username},
            )
        return _fetch_user(conn, username)


# ---------------------------------------------------------------------------
# Posts
# ---------------------------------------------------------------------------

@app.post("/posts", status_code=201, response_model=PostOut)
def create_post(
    body: PostCreate,
    x_username: Optional[str] = Header(default=None, alias="X-Username"),
):
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header required")

    with engine.begin() as conn:
        author = _require_user(conn, x_username)
        board = body.board or "general"
        _require_board(conn, board)

        result = conn.execute(
            text("""
                INSERT INTO posts (user_id, message, timestamp, parent_id, board)
                VALUES (:uid, :msg, :ts, NULL, :board)
            """),
            {"uid": author["id"], "msg": body.message, "ts": _now_iso(), "board": board},
        )
        return conn.execute(
            text(POST_BASE_SQL + " WHERE p.id = :id"), {"id": result.lastrowid}
        ).mappings().first()


@app.get("/posts", response_model=List[PostOut])
def list_posts(
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    username: Optional[str] = Query(default=None),
):
    with engine.connect() as conn:
        return _select_posts(
            conn,
            where="u.username = :au" if username else "",
            params={"au": username} if username else None,
            q=q, limit=limit, offset=offset,
        )


@app.get("/posts/{post_id}", response_model=PostOut)
def get_post(post_id: int):
    with engine.connect() as conn:
        row = conn.execute(
            text(POST_BASE_SQL + " WHERE p.id = :id"), {"id": post_id}
        ).mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail="post not found")
        return row


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int):
    with engine.begin() as conn:
        _require_post_exists(conn, post_id)
        # Cascading cleanup — no orphan reaction rows pointing at dead posts.
        conn.execute(text("DELETE FROM reactions WHERE post_id = :id"), {"id": post_id})
        conn.execute(text("DELETE FROM posts WHERE id = :id"), {"id": post_id})


@app.patch("/posts/{post_id}", response_model=PostOut)
def patch_post(
    post_id: int,
    body: PostPatch,
    x_username: Optional[str] = Header(default=None, alias="X-Username"),
):
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header required")

    with engine.begin() as conn:
        owner = conn.execute(text("""
            SELECT u.username AS author
            FROM posts p JOIN users u ON u.id = p.user_id
            WHERE p.id = :id
        """), {"id": post_id}).mappings().first()
        if not owner:
            raise HTTPException(status_code=404, detail="post not found")
        if owner["author"] != x_username:
            raise HTTPException(status_code=403, detail="only the author can edit this post")

        conn.execute(
            text("UPDATE posts SET message = :m, updated_at = :t WHERE id = :id"),
            {"m": body.message, "t": _now_iso(), "id": post_id},
        )
        return conn.execute(
            text(POST_BASE_SQL + " WHERE p.id = :id"), {"id": post_id}
        ).mappings().first()


# ---------------------------------------------------------------------------
# Reactions (gold)
# ---------------------------------------------------------------------------

@app.post("/posts/{post_id}/reactions", status_code=201, response_model=ReactionOut)
def create_reaction(post_id: int, body: ReactionCreate):
    with engine.begin() as conn:
        _require_post_exists(conn, post_id)
        author = _require_user(conn, body.username)
        try:
            conn.execute(
                text("""
                    INSERT INTO reactions (post_id, user_id, emoji)
                    VALUES (:pid, :uid, :k)
                """),
                {"pid": post_id, "uid": author["id"], "k": body.kind},
            )
        except IntegrityError:
            # UNIQUE(post_id, user_id, emoji) — same (user, kind) twice on one post.
            raise HTTPException(status_code=409, detail="reaction already exists")
        return {"post_id": post_id, "username": body.username, "kind": body.kind}


@app.delete("/posts/{post_id}/reactions/{username}", status_code=204)
def delete_reaction(post_id: int, username: str):
    with engine.begin() as conn:
        _require_post_exists(conn, post_id)
        author = _require_user(conn, username)
        result = conn.execute(
            text("DELETE FROM reactions WHERE post_id = :pid AND user_id = :uid"),
            {"pid": post_id, "uid": author["id"]},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="no reactions to delete")


@app.get("/posts/{post_id}/reactions", response_model=List[ReactionOut])
def list_reactions(post_id: int):
    with engine.connect() as conn:
        _require_post_exists(conn, post_id)
        return conn.execute(text("""
            SELECT r.post_id,
                   u.username,
                   r.emoji AS kind
            FROM reactions r
            JOIN users u ON u.id = r.user_id
            WHERE r.post_id = :pid
            ORDER BY r.id
        """), {"pid": post_id}).mappings().all()


# ---------------------------------------------------------------------------
# Boards (gold)
# ---------------------------------------------------------------------------

@app.post("/boards", status_code=201, response_model=BoardOut)
def create_board(body: BoardCreate):
    with engine.begin() as conn:
        if _fetch_board(conn, body.name):
            raise HTTPException(status_code=409, detail="board already exists")
        conn.execute(
            text("INSERT INTO boards (name, description, created_at) VALUES (:n, :d, :t)"),
            {"n": body.name, "d": body.description or "", "t": _now_iso()},
        )
        return _fetch_board(conn, body.name)


@app.get("/boards", response_model=List[BoardOut])
def list_boards():
    with engine.connect() as conn:
        return conn.execute(text("""
            SELECT name,
                   COALESCE(description, '') AS description,
                   created_at
            FROM boards
            ORDER BY name
        """)).mappings().all()


@app.get("/boards/{name}/posts", response_model=List[PostOut])
def list_board_posts(
    name: str,
    q: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    with engine.connect() as conn:
        _require_board(conn, name)
        return _select_posts(
            conn,
            where="p.board = :b",
            params={"b": name},
            q=q, limit=limit, offset=offset,
        )
