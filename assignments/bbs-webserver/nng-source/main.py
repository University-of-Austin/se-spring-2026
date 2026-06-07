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

import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text

from db import DEFAULT_BOARD, engine, init_db


# ---------- Password / session helpers ----------
# Passwords are hashed with scrypt (stdlib). Stored as "salt$hash" in hex, so
# we don't need a separate salt column and rotating parameters later is a
# matter of adding a prefix to the stored value.

_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P
    )
    return salt.hex() + "$" + digest.hex()


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored or "$" not in stored:
        return False
    salt_hex, digest_hex = stored.split("$", 1)
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P
    )
    return secrets.compare_digest(actual, expected)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def resolve_session(conn, authorization: Optional[str]):
    """Given an 'Authorization: Bearer <token>' header value, return the
    associated user row or None. Tolerant of missing / malformed values."""
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    if not token:
        return None
    row = conn.execute(
        text(
            "SELECT u.id, u.username, u.created_at, u.bio "
            "FROM sessions s JOIN users u ON s.user_id = u.id "
            "WHERE s.token = :t"
        ),
        {"t": token},
    ).fetchone()
    return row

# Disable FastAPI's built-in /docs and /redoc so we can wrap them with our own
# nav strip (so every page can link to every other page).
app = FastAPI(title="BBS Webserver", docs_url=None, redoc_url=None)

# CORS: allow the A4 frontend (Vite dev server on :5173) to talk to us from the
# browser. Without this, browsers block cross-origin fetches even though curl
# and verify_api.py still work. See A4 README for the full story.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
AVATAR_DIR = STATIC_DIR / "avatars"
POST_IMAGE_DIR = STATIC_DIR / "post-images"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
POST_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


# ---------- Frontend pages ----------

# Inline nav strip injected on top of every HTML page. Kept out-of-band from
# the terminal's own styling so it's consistent across Swagger / ReDoc /
# terminal. Fixed position on the top-right so it never covers content.
NAV_HTML = """
<div id="bbs-nav" style="
  position: fixed; top: 8px; right: 8px; z-index: 99999;
  background: rgba(10,14,20,0.92); color: #c0caf5;
  border: 1px solid #565f89; border-radius: 6px;
  padding: 6px 10px; font: 12px/1.4 'JetBrains Mono','Consolas',monospace;
  box-shadow: 0 2px 8px rgba(0,0,0,0.4);">
  <strong style="color:#7aa2f7;">BBS</strong>
  &nbsp;<a href="/" style="color:#9ece6a;text-decoration:none;">terminal</a>
  &nbsp;<a href="/docs" style="color:#e0af68;text-decoration:none;">swagger</a>
  &nbsp;<a href="/redoc" style="color:#bb9af7;text-decoration:none;">redoc</a>
  &nbsp;<a href="/openapi.json" style="color:#7aa2f7;text-decoration:none;">spec</a>
</div>
"""


def inject_nav(html: str) -> str:
    """Inject the nav strip just after <body> of a rendered HTML page."""
    idx = html.lower().find("<body")
    if idx == -1:
        return NAV_HTML + html
    end = html.find(">", idx)
    if end == -1:
        return NAV_HTML + html
    return html[: end + 1] + NAV_HTML + html[end + 1 :]


@app.get("/", include_in_schema=False)
def home() -> HTMLResponse:
    raw = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(inject_nav(raw))


@app.get("/docs", include_in_schema=False)
def custom_docs() -> HTMLResponse:
    resp = get_swagger_ui_html(openapi_url="/openapi.json", title="BBS - Swagger UI")
    html = resp.body.decode("utf-8")
    return HTMLResponse(inject_nav(html))


@app.get("/redoc", include_in_schema=False)
def custom_redoc() -> HTMLResponse:
    resp = get_redoc_html(openapi_url="/openapi.json", title="BBS - ReDoc")
    html = resp.body.decode("utf-8")
    return HTMLResponse(inject_nav(html))


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # Empty favicon to keep browser 404s out of the logs.
    return HTMLResponse("", status_code=204)


# ---------- Request bodies ----------

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)


class UserPatch(BaseModel):
    bio: Optional[str] = Field(None, max_length=200)


class Login(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=1, max_length=128)


import re as _re
BOARD_NAME_PATTERN = r"^[a-z0-9_-]+$"
BOARD_NAME_PATTERN_RE = _re.compile(BOARD_NAME_PATTERN)


class PostCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=500)
    # Board is optional; missing / null / empty string all fall through to
    # the default board. Validation only fires when a non-empty value is
    # supplied, so the common case ("just post this") stays easy.
    board: Optional[str] = Field(
        None, min_length=1, max_length=30, pattern=BOARD_NAME_PATTERN
    )


class PostPatch(BaseModel):
    message: Optional[str] = Field(None, min_length=1, max_length=500)


class DMCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class PasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


# ---------- Image upload helpers (shared by avatars and post images) -----

_IMAGE_MIME_TO_EXT = {
    "image/png":  "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif":  "gif",
}


async def read_image_upload(
    file: UploadFile,
    max_bytes: int,
    label: str = "image",
) -> tuple[bytes, str]:
    """Read an UploadFile into memory, enforce a byte cap, verify the bytes
    look like a real image via Pillow, and return (bytes, file_extension).

    Raises HTTPException on validation failures.
    """
    if file.content_type not in _IMAGE_MIME_TO_EXT:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported {label} type {file.content_type!r}; use PNG, JPG, WebP, or GIF",
        )

    data = bytearray()
    chunk_size = 64 * 1024
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"{label} too large (max {max_bytes // 1000} KB)",
            )

    try:
        from io import BytesIO
        from PIL import Image, UnidentifiedImageError
        img = Image.open(BytesIO(bytes(data)))
        img.verify()
    except (UnidentifiedImageError, Exception) as e:
        raise HTTPException(status_code=400, detail=f"not a valid {label}: {e}")

    return bytes(data), _IMAGE_MIME_TO_EXT[file.content_type]


# ---------- Helpers ----------

def now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")


def fetch_user_row(conn, username: str):
    return conn.execute(
        text("SELECT id, username, created_at, bio, avatar FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()


def user_to_dict(conn, row) -> dict:
    """Shape a user row into the public response. Includes Silver post_count."""
    post_count = conn.execute(
        text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"),
        {"uid": row.id},
    ).scalar_one()
    avatar = getattr(row, "avatar", None)
    return {
        "username": row.username,
        "created_at": row.created_at,
        "bio": row.bio,
        "post_count": post_count,
        "avatar_url": f"/static/avatars/{avatar}" if avatar else None,
    }


def post_row_to_dict(row) -> dict:
    # Silver: always include updated_at (None until the post is edited).
    # Gold: include the board name, the author's avatar URL, and any attached image.
    avatar = getattr(row, "avatar", None)
    image = getattr(row, "image", None)
    return {
        "id": row.id,
        "username": row.username,
        "board": row.board,
        "message": row.message,
        "created_at": row.created_at,
        "updated_at": getattr(row, "updated_at", None),
        "avatar_url": f"/static/avatars/{avatar}" if avatar else None,
        "image_url": f"/static/post-images/{image}" if image else None,
    }


def get_or_create_board(conn, name: str) -> int:
    """Return the id of the board with this name, creating it if missing.
    Board names are normalized to lowercase."""
    name = name.lower()
    row = conn.execute(
        text("SELECT id FROM boards WHERE name = :n"), {"n": name}
    ).fetchone()
    if row:
        return row.id
    result = conn.execute(
        text("INSERT INTO boards (name, created_at) VALUES (:n, :c)"),
        {"n": name, "c": now_iso()},
    )
    return result.lastrowid


# ---------- /users ----------

@app.post("/users", status_code=201)
def create_user(body: UserCreate):
    with engine.begin() as conn:
        existing = fetch_user_row(conn, body.username)
        if existing:
            raise HTTPException(status_code=409, detail="username already exists")
        conn.execute(
            text(
                "INSERT INTO users (username, created_at, bio, password_hash) "
                "VALUES (:u, :c, NULL, :p)"
            ),
            {"u": body.username, "c": now_iso(), "p": hash_password(body.password)},
        )
        row = fetch_user_row(conn, body.username)
        return user_to_dict(conn, row)


# ---------- auth endpoints ----------

@app.post("/login", status_code=200)
def login(body: Login):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, username, password_hash FROM users WHERE username = :u"),
            {"u": body.username},
        ).fetchone()
        if not row or not verify_password(body.password, row.password_hash):
            raise HTTPException(status_code=401, detail="invalid username or password")
        token = new_session_token()
        conn.execute(
            text("INSERT INTO sessions (token, user_id, created_at) VALUES (:t, :uid, :c)"),
            {"t": token, "uid": row.id, "c": now_iso()},
        )
        return {"token": token, "username": row.username}


@app.post("/logout", status_code=204)
def logout(authorization: Optional[str] = Header(default=None, alias="Authorization")):
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM sessions WHERE token = :t"), {"t": parts[1].strip()})
    return None


@app.get("/users")
def list_users():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, username, created_at, bio, avatar FROM users ORDER BY id")
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
def patch_user(
    username: str,
    body: UserPatch,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    with engine.begin() as conn:
        row = fetch_user_row(conn, username)
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        me = resolve_session(conn, authorization)
        if not me:
            raise HTTPException(status_code=401, detail="authentication required")
        if me.username != username:
            raise HTTPException(status_code=403, detail="cannot edit another user's profile")
        if body.bio is not None:
            conn.execute(
                text("UPDATE users SET bio = :b WHERE id = :id"),
                {"b": body.bio, "id": row.id},
            )
        row = fetch_user_row(conn, username)
        return user_to_dict(conn, row)


# ---------- avatar upload / delete (beyond A2 spec; needed by A4 frontend) ----

_AVATAR_MAX_BYTES = 1_000_000  # 1 MB; uses the shared _IMAGE_MIME_TO_EXT.
_POST_IMAGE_MAX_BYTES = 5_000_000  # 5 MB; per-post images can be bigger.


def _require_self(conn, authorization: Optional[str], username: str):
    me = resolve_session(conn, authorization)
    if not me:
        raise HTTPException(status_code=401, detail="authentication required")
    if me.username != username:
        raise HTTPException(status_code=403, detail="cannot modify another user's avatar")
    return me


@app.post("/users/{username}/avatar")
async def upload_avatar(
    username: str,
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    data, ext = await read_image_upload(file, _AVATAR_MAX_BYTES, label="avatar")

    with engine.begin() as conn:
        row = fetch_user_row(conn, username)
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        _require_self(conn, authorization, username)

        filename = f"{row.id}.{ext}"

        # Delete any prior avatar with a different extension so we don't leak.
        for old_ext in _IMAGE_MIME_TO_EXT.values():
            old = AVATAR_DIR / f"{row.id}.{old_ext}"
            if old.exists() and old.name != filename:
                try: old.unlink()
                except Exception: pass

        (AVATAR_DIR / filename).write_bytes(data)
        conn.execute(
            text("UPDATE users SET avatar = :a WHERE id = :id"),
            {"a": filename, "id": row.id},
        )
        row = fetch_user_row(conn, username)
        return user_to_dict(conn, row)


@app.delete("/users/{username}/avatar")
def delete_avatar(
    username: str,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    with engine.begin() as conn:
        row = fetch_user_row(conn, username)
        if not row:
            raise HTTPException(status_code=404, detail="user not found")
        _require_self(conn, authorization, username)

        if row.avatar:
            try: (AVATAR_DIR / row.avatar).unlink()
            except FileNotFoundError: pass

        conn.execute(text("UPDATE users SET avatar = NULL WHERE id = :id"), {"id": row.id})
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
            "SELECT p.id, u.username, u.avatar, b.name AS board, p.message, p.image, p.created_at, p.updated_at "
            "FROM posts p JOIN users u ON p.user_id = u.id "
            "JOIN boards b ON p.board_id = b.id "
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


# ---------- /boards ----------

@app.get("/boards")
def list_boards():
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT b.name, b.created_at, COUNT(p.id) AS post_count "
                "FROM boards b LEFT JOIN posts p ON p.board_id = b.id "
                "GROUP BY b.id ORDER BY b.name"
            )
        ).fetchall()
        return [
            {"name": r.name, "created_at": r.created_at, "post_count": r.post_count}
            for r in rows
        ]


@app.get("/boards/{name}")
def get_board(name: str):
    name = name.lower()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT b.name, b.created_at, COUNT(p.id) AS post_count "
                "FROM boards b LEFT JOIN posts p ON p.board_id = b.id "
                "WHERE b.name = :n GROUP BY b.id"
            ),
            {"n": name},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="board not found")
        return {"name": row.name, "created_at": row.created_at, "post_count": row.post_count}


@app.get("/boards/{name}/posts")
def get_posts_for_board(
    name: str,
    q: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    name = name.lower()
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT id FROM boards WHERE name = :n"), {"n": name}
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="board not found")

        sql = (
            "SELECT p.id, u.username, u.avatar, b.name AS board, p.message, p.image, p.created_at, p.updated_at "
            "FROM posts p JOIN users u ON p.user_id = u.id "
            "JOIN boards b ON p.board_id = b.id "
            "WHERE b.name = :bn"
        )
        params: dict = {"bn": name}
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


# ---------- /posts ----------

@app.post("/posts", status_code=201)
async def create_post(
    message: str = Form(..., min_length=1, max_length=500),
    board: Optional[str] = Form(None, max_length=30),
    image: Optional[UploadFile] = File(None),
    x_username: Optional[str] = Header(default=None, alias="X-Username"),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    """
    Multipart POST. Required field: ``message``. Optional: ``board`` (defaults
    to general) and ``image`` (UploadFile; PNG/JPG/WebP/GIF, up to 5 MB).

    Note: this used to accept a JSON body. Bumped to multipart so the frontend
    can attach an image in the same request. Existing JSON callers (e.g. older
    versions of verify_api.py) will need to send Form fields now.
    """
    if not x_username:
        raise HTTPException(status_code=400, detail="X-Username header required")

    # Normalize empty-string board to "no board specified".
    board_name = (board or "").strip().lower() or DEFAULT_BOARD
    if not BOARD_NAME_PATTERN_RE.match(board_name):
        raise HTTPException(
            status_code=422,
            detail=f"invalid board name {board_name!r} (lowercase letters, digits, _ or -)",
        )

    # Validate + read the image up front (before any DB writes), so we don't
    # half-create a post then fail.
    image_bytes: Optional[bytes] = None
    image_ext: Optional[str] = None
    if image is not None and (image.filename or image.content_type):
        image_bytes, image_ext = await read_image_upload(
            image, _POST_IMAGE_MAX_BYTES, label="post image"
        )

    with engine.begin() as conn:
        user = fetch_user_row(conn, x_username)
        if not user:
            raise HTTPException(status_code=404, detail="user not found")
        me = resolve_session(conn, authorization)
        if not me:
            raise HTTPException(status_code=401, detail="authentication required")
        if me.username != x_username:
            raise HTTPException(
                status_code=403, detail="X-Username does not match authenticated user"
            )

        board_id = get_or_create_board(conn, board_name)
        created = now_iso()
        result = conn.execute(
            text(
                "INSERT INTO posts (user_id, board_id, message, created_at) "
                "VALUES (:uid, :bid, :m, :c)"
            ),
            {"uid": user.id, "bid": board_id, "m": message, "c": created},
        )
        pid = result.lastrowid

        image_filename: Optional[str] = None
        if image_bytes is not None and image_ext is not None:
            image_filename = f"{pid}.{image_ext}"
            (POST_IMAGE_DIR / image_filename).write_bytes(image_bytes)
            conn.execute(
                text("UPDATE posts SET image = :i WHERE id = :id"),
                {"i": image_filename, "id": pid},
            )

        avatar = getattr(user, "avatar", None)
        return {
            "id": pid,
            "username": user.username,
            "board": board_name,
            "message": message,
            "created_at": created,
            "updated_at": None,
            "avatar_url": f"/static/avatars/{avatar}" if avatar else None,
            "image_url": f"/static/post-images/{image_filename}" if image_filename else None,
        }


@app.get("/posts")
def list_posts(
    q: Optional[str] = None,
    username: Optional[str] = None,
    board: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    with engine.connect() as conn:
        sql = (
            "SELECT p.id, u.username, u.avatar, b.name AS board, p.message, p.image, p.created_at, p.updated_at "
            "FROM posts p JOIN users u ON p.user_id = u.id "
            "JOIN boards b ON p.board_id = b.id "
            "WHERE 1=1"
        )
        params: dict = {}
        if q:
            sql += " AND p.message LIKE :q"
            params["q"] = f"%{q}%"
        if username:
            sql += " AND u.username = :un"
            params["un"] = username
        if board:
            sql += " AND b.name = :bn"
            params["bn"] = board.lower()
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
                "SELECT p.id, u.username, u.avatar, b.name AS board, p.message, p.image, p.created_at, p.updated_at "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                "JOIN boards b ON p.board_id = b.id "
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
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    # Ownership policy: authenticated user must be the original author.
    # X-Username is still required by the A2 spec and must match the session.
    if not x_username:
        raise HTTPException(status_code=400, detail="X-Username header required")

    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT p.id, u.username, u.avatar, b.name AS board, p.message, p.image, p.created_at, p.updated_at "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                "JOIN boards b ON p.board_id = b.id "
                "WHERE p.id = :id"
            ),
            {"id": post_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="post not found")

        me = resolve_session(conn, authorization)
        if not me:
            raise HTTPException(status_code=401, detail="authentication required")
        if me.username != x_username:
            raise HTTPException(
                status_code=403, detail="X-Username does not match authenticated user"
            )
        if row.username != x_username:
            raise HTTPException(status_code=403, detail="only the author can edit this post")

        if body.message is not None:
            conn.execute(
                text("UPDATE posts SET message = :m, updated_at = :u WHERE id = :id"),
                {"m": body.message, "u": now_iso(), "id": post_id},
            )

        row = conn.execute(
            text(
                "SELECT p.id, u.username, u.avatar, b.name AS board, p.message, p.image, p.created_at, p.updated_at "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                "JOIN boards b ON p.board_id = b.id "
                "WHERE p.id = :id"
            ),
            {"id": post_id},
        ).fetchone()
        return post_row_to_dict(row)


@app.delete("/posts/{post_id}", status_code=204)
def delete_post(
    post_id: int,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT p.id, p.image, u.username FROM posts p "
                "JOIN users u ON p.user_id = u.id WHERE p.id = :id"
            ),
            {"id": post_id},
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="post not found")

        me = resolve_session(conn, authorization)
        if not me:
            raise HTTPException(status_code=401, detail="authentication required")
        if me.username != row.username:
            raise HTTPException(status_code=403, detail="only the author can delete this post")

        # Clean up the attached image file if any.
        if row.image:
            try: (POST_IMAGE_DIR / row.image).unlink()
            except FileNotFoundError: pass

        conn.execute(text("DELETE FROM posts WHERE id = :id"), {"id": post_id})
    return None


# ---------- DMs (beyond A2 spec; A4 frontend feature) -------------------

def _require_authed(conn, authorization: Optional[str]):
    me = resolve_session(conn, authorization)
    if not me:
        raise HTTPException(status_code=401, detail="authentication required")
    return me


def _dm_row_to_dict(row, my_id: int) -> dict:
    """Shape a messages row for the API response. `my_id` is the current
    user's id; we use it to set `from_me` so the client doesn't have to
    compare usernames."""
    return {
        "id": row.id,
        "from_username": row.from_username,
        "to_username": row.to_username,
        "from_me": row.from_id == my_id,
        "message": row.message,
        "created_at": row.created_at,
        "read_at": row.read_at,
    }


@app.get("/dms")
def list_dm_conversations(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    """One row per conversation partner with the latest message + an unread count."""
    with engine.begin() as conn:
        me = _require_authed(conn, authorization)
        # Latest message per partner.
        rows = conn.execute(
            text("""
                WITH paired AS (
                    SELECT m.*,
                           CASE WHEN m.sender_id = :me THEN m.recipient_id
                                ELSE m.sender_id END AS partner_id
                    FROM messages m
                    WHERE m.sender_id = :me OR m.recipient_id = :me
                ),
                ranked AS (
                    SELECT p.*, ROW_NUMBER() OVER (
                        PARTITION BY p.partner_id ORDER BY p.id DESC
                    ) AS rn
                    FROM paired p
                )
                SELECT r.id, r.message, r.created_at, r.read_at,
                       r.sender_id, r.recipient_id,
                       u.username AS partner_username,
                       u.avatar   AS partner_avatar,
                       (SELECT COUNT(*) FROM messages m2
                        WHERE m2.sender_id = r.partner_id
                          AND m2.recipient_id = :me
                          AND m2.read_at IS NULL) AS unread_count
                FROM ranked r
                JOIN users u ON u.id = r.partner_id
                WHERE r.rn = 1
                ORDER BY r.id DESC
            """),
            {"me": me.id},
        ).fetchall()

        return [
            {
                "partner": {
                    "username": r.partner_username,
                    "avatar_url": (
                        f"/static/avatars/{r.partner_avatar}" if r.partner_avatar else None
                    ),
                },
                "last_message": {
                    "message": r.message,
                    "created_at": r.created_at,
                    "from_me": r.sender_id == me.id,
                    "read_at": r.read_at,
                },
                "unread_count": int(r.unread_count or 0),
            }
            for r in rows
        ]


@app.get("/dms/{username}")
def get_dm_thread(
    username: str,
    limit: int = Query(100, ge=1, le=500),
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    """Fetch the full conversation between the current user and {username}.

    Side effect: marks all messages FROM {username} TO me as read.
    """
    with engine.begin() as conn:
        me = _require_authed(conn, authorization)
        partner = fetch_user_row(conn, username)
        if not partner:
            raise HTTPException(status_code=404, detail="user not found")
        if partner.username == me.username:
            raise HTTPException(status_code=400, detail="cannot DM yourself")

        rows = conn.execute(
            text("""
                SELECT m.id, m.message, m.created_at, m.read_at,
                       m.sender_id    AS from_id,
                       us.username    AS from_username,
                       ur.username    AS to_username
                FROM messages m
                JOIN users us ON us.id = m.sender_id
                JOIN users ur ON ur.id = m.recipient_id
                WHERE (m.sender_id = :me AND m.recipient_id = :them)
                   OR (m.sender_id = :them AND m.recipient_id = :me)
                ORDER BY m.id ASC
                LIMIT :lim
            """),
            {"me": me.id, "them": partner.id, "lim": limit},
        ).fetchall()

        # Mark incoming unread as read.
        conn.execute(
            text(
                "UPDATE messages SET read_at = :now "
                "WHERE sender_id = :them AND recipient_id = :me AND read_at IS NULL"
            ),
            {"now": now_iso(), "them": partner.id, "me": me.id},
        )

        partner_avatar = getattr(partner, "avatar", None)
        return {
            "partner": {
                "username": partner.username,
                "avatar_url": (
                    f"/static/avatars/{partner_avatar}" if partner_avatar else None
                ),
            },
            "messages": [_dm_row_to_dict(r, me.id) for r in rows],
        }


@app.post("/dms/{username}", status_code=201)
def send_dm(
    username: str,
    body: DMCreate,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    with engine.begin() as conn:
        me = _require_authed(conn, authorization)
        partner = fetch_user_row(conn, username)
        if not partner:
            raise HTTPException(status_code=404, detail="user not found")
        if partner.username == me.username:
            raise HTTPException(status_code=400, detail="cannot DM yourself")

        created = now_iso()
        result = conn.execute(
            text(
                "INSERT INTO messages (sender_id, recipient_id, message, created_at) "
                "VALUES (:s, :r, :m, :c)"
            ),
            {"s": me.id, "r": partner.id, "m": body.message, "c": created},
        )
        return {
            "id": result.lastrowid,
            "from_username": me.username,
            "to_username": partner.username,
            "from_me": True,
            "message": body.message,
            "created_at": created,
            "read_at": None,
        }


# ---------- Password change (settings page) -----------------------------

@app.patch("/users/{username}/password", status_code=200)
def change_password(
    username: str,
    body: PasswordChange,
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
):
    with engine.begin() as conn:
        me = _require_authed(conn, authorization)
        if me.username != username:
            raise HTTPException(
                status_code=403, detail="cannot change another user's password"
            )

        row = conn.execute(
            text("SELECT id, password_hash FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if not row or not verify_password(body.current_password, row.password_hash):
            raise HTTPException(status_code=401, detail="current password is incorrect")

        conn.execute(
            text("UPDATE users SET password_hash = :p WHERE id = :id"),
            {"p": hash_password(body.new_password), "id": row.id},
        )
        # Invalidate all sessions other than the current one. Simplest: drop
        # everything except the bearer token in the Authorization header.
        parts = (authorization or "").split(None, 1)
        current_token = parts[1].strip() if len(parts) == 2 else ""
        if current_token:
            conn.execute(
                text("DELETE FROM sessions WHERE user_id = :id AND token != :t"),
                {"id": row.id, "t": current_token},
            )
        return {"ok": True}
