from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional


from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import text

from db import engine, init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="BBS Webserver", lifespan=lifespan)


# ---------- models ----------

USERNAME_PATTERN = r"^[a-zA-Z0-9_]+$"
BOARD_NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"



class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=USERNAME_PATTERN)


class UserPatch(BaseModel):
    bio: str = Field(max_length=200)


class PostCreate(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class PostPatch(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class BoardCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40, pattern=BOARD_NAME_PATTERN)


# ---------- helpers ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")


def user_row(conn, username: str):
    return conn.execute(
        text("SELECT id, username, join_date, bio FROM users WHERE username = :u"),
        {"u": username},
    ).mappings().first()


def board_row(conn, name: str):
    return conn.execute(
        text("SELECT id, name FROM boards WHERE name = :n"),
        {"n": name},
    ).mappings().first()


def user_response(conn, row) -> dict:
    pc = conn.execute(
        text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"),
        {"uid": row["id"]},
    ).scalar_one()
    return {
        "username": row["username"],
        "created_at": row["join_date"],
        "bio": row["bio"],
        "post_count": pc,
    }


def post_response(row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "message": row["message"],
        "created_at": row["timestamp"],
        "updated_at": row["updated_at"],
        "board": row["board"],
    }


POST_SELECT = (
    "SELECT p.id AS id, u.username AS username, p.message AS message, "
    "p.timestamp AS timestamp, p.updated_at AS updated_at, b.name AS board "
    "FROM posts p "
    "JOIN users u ON u.id = p.user_id "
    "JOIN boards b ON b.id = p.board_id"
)


# ---------- /users ----------

@app.post("/users", status_code=201)
def create_user(body: UserCreate) -> dict:
    created_at = now_iso()
    with engine.begin() as conn:
        existing = user_row(conn, body.username)
        if existing is not None:
            raise HTTPException(status_code=409, detail="username already exists")
        conn.execute(
            text(
                "INSERT INTO users (username, join_date, post_count, bio) "
                "VALUES (:u, :d, 0, '')"
            ),
            {"u": body.username, "d": created_at},
        )
        row = user_row(conn, body.username)
        return user_response(conn, row)


@app.get("/users")
def list_users() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, username, join_date, bio FROM users ORDER BY id")
        ).mappings().all()
        return [user_response(conn, r) for r in rows]


@app.get("/users/{username}")
def get_user(username: str) -> dict:
    with engine.connect() as conn:
        row = user_row(conn, username)
        if row is None:
            raise HTTPException(status_code=404, detail="user not found")
        return user_response(conn, row)


@app.patch("/users/{username}")
def patch_user(username: str, body: UserPatch) -> dict:
    with engine.begin() as conn:
        row = user_row(conn, username)
        if row is None:
            raise HTTPException(status_code=404, detail="user not found")
        conn.execute(
            text("UPDATE users SET bio = :b WHERE id = :uid"),
            {"b": body.bio, "uid": row["id"]},
        )
        row = user_row(conn, username)
        return user_response(conn, row)


@app.get("/users/{username}/posts")
def get_user_posts(username: str) -> list[dict]:
    with engine.connect() as conn:
        if user_row(conn, username) is None:
            raise HTTPException(status_code=404, detail="user not found")
        rows = conn.execute(
            text(POST_SELECT + " WHERE u.username = :u ORDER BY p.id"),
            {"u": username},
        ).mappings().all()
    return [post_response(r) for r in rows]


# ---------- /posts ----------

def _insert_post(conn, user_id: int, board_id: int, message: str, created_at: str) -> int:
    next_bpid = conn.execute(
        text(
            "SELECT COALESCE(MAX(board_post_id), 0) + 1 "
            "FROM posts WHERE board_id = :b"
        ),
        {"b": board_id},
    ).scalar_one()
    result = conn.execute(
        text(
            "INSERT INTO posts "
            "(user_id, board_id, board_post_id, parent_id, message, timestamp) "
            "VALUES (:uid, :bid, :bpid, NULL, :m, :t)"
        ),
        {
            "uid": user_id,
            "bid": board_id,
            "bpid": next_bpid,
            "m": message,
            "t": created_at,
        },
    )
    conn.execute(
        text("UPDATE users SET post_count = post_count + 1 WHERE id = :uid"),
        {"uid": user_id},
    )
    return result.lastrowid


@app.post("/posts", status_code=201)
def create_post(
    body: PostCreate,
    x_username: Optional[str] = Header(default=None, alias="X-Username"),
) -> dict:
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header required")
    created_at = now_iso()
    with engine.begin() as conn:
        urow = user_row(conn, x_username)
        if urow is None:
            raise HTTPException(status_code=404, detail="user not found")
        brow = board_row(conn, "general")
        pid = _insert_post(conn, urow["id"], brow["id"], body.message, created_at)
    return {
        "id": pid,
        "username": x_username,
        "message": body.message,
        "created_at": created_at,
        "updated_at": None,
        "board": brow["name"],
    }


@app.get("/posts")
def list_posts(
    q: Optional[str] = None,
    username: Optional[str] = None,
    board: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    where: list[str] = []
    params: dict = {"limit": limit, "offset": offset}
    if q is not None:
        where.append("p.message LIKE :needle")
        params["needle"] = f"%{q}%"
    if username is not None:
        where.append("u.username = :uname")
        params["uname"] = username
    if board is not None:
        where.append("b.name = :bname")
        params["bname"] = board
    sql = POST_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY p.id LIMIT :limit OFFSET :offset"
    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [post_response(r) for r in rows]


@app.patch("/posts/{post_id}")
def patch_post(
    post_id: int,
    body: PostPatch,
    x_username: Optional[str] = Header(default=None, alias="X-Username"),
) -> dict:
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header required")
    updated_at = now_iso()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT p.id AS id, u.username AS username "
                "FROM posts p JOIN users u ON u.id = p.user_id "
                "WHERE p.id = :pid"
            ),
            {"pid": post_id},
        ).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="post not found")
        if row["username"] != x_username:
            raise HTTPException(status_code=403, detail="only the author may edit this post")
        conn.execute(
            text("UPDATE posts SET message = :m, updated_at = :t WHERE id = :pid"),
            {"m": body.message, "t": updated_at, "pid": post_id},
        )
        new_row = conn.execute(
            text(POST_SELECT + " WHERE p.id = :pid"),
            {"pid": post_id},
        ).mappings().first()
        return post_response(new_row)


@app.get("/posts/{post_id}")
def get_post(post_id: int) -> dict:
    with engine.connect() as conn:
        row = conn.execute(
            text(POST_SELECT + " WHERE p.id = :pid"),
            {"pid": post_id},
        ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="post not found")
    return post_response(row)


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    x_username: Optional[str] = Header(default=None, alias="X-Username"),
) -> Response:
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header required")
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT p.user_id AS user_id, u.username AS username "
                "FROM posts p JOIN users u ON u.id = p.user_id "
                "WHERE p.id = :pid"
            ),
            {"pid": post_id},
        ).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="post not found")
        if row["username"] != x_username:
            raise HTTPException(status_code=403, detail="only the author may delete this post")
        conn.execute(text("DELETE FROM posts WHERE id = :pid"), {"pid": post_id})
        conn.execute(
            text(
                "UPDATE users SET post_count = MAX(post_count - 1, 0) "
                "WHERE id = :uid"
            ),
            {"uid": row["user_id"]},
        )
    return Response(status_code=204)


# ---------- /boards ----------

@app.post("/boards", status_code=201)
def create_board(body: BoardCreate) -> dict:
    with engine.begin() as conn:
        if board_row(conn, body.name) is not None:
            raise HTTPException(status_code=409, detail="board already exists")
        conn.execute(
            text("INSERT INTO boards (name) VALUES (:n)"),
            {"n": body.name},
        )
    return {"name": body.name}


@app.get("/boards")
def list_boards() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM boards ORDER BY id")
        ).mappings().all()
    return [{"name": r["name"]} for r in rows]


@app.get("/boards/{name}/posts")
def list_board_posts(
    name: str,
    q: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    with engine.connect() as conn:
        if board_row(conn, name) is None:
            raise HTTPException(status_code=404, detail="board not found")
        where = ["b.name = :bname"]
        params: dict = {"bname": name, "limit": limit, "offset": offset}
        if q is not None:
            where.append("p.message LIKE :needle")
            params["needle"] = f"%{q}%"
        sql = (
            POST_SELECT
            + " WHERE " + " AND ".join(where)
            + " ORDER BY p.id LIMIT :limit OFFSET :offset"
        )
        rows = conn.execute(text(sql), params).mappings().all()
    return [post_response(r) for r in rows]


@app.post("/boards/{name}/posts", status_code=201)
def create_board_post(
    name: str,
    body: PostCreate,
    x_username: Optional[str] = Header(default=None, alias="X-Username"),
) -> dict:
    if x_username is None:
        raise HTTPException(status_code=400, detail="X-Username header required")
    created_at = now_iso()
    with engine.begin() as conn:
        urow = user_row(conn, x_username)
        if urow is None:
            raise HTTPException(status_code=404, detail="user not found")
        brow = board_row(conn, name)
        if brow is None:
            raise HTTPException(status_code=404, detail="board not found")
        pid = _insert_post(conn, urow["id"], brow["id"], body.message, created_at)
    return {
        "id": pid,
        "username": x_username,
        "message": body.message,
        "created_at": created_at,
        "updated_at": None,
        "board": brow["name"],
    }
