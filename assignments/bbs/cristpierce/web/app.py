"""FastAPI web frontend for the BBS.

Run with: uvicorn web.app:app --reload
"""

import os
import sys
import uuid

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import markdown as md
from markupsafe import Markup
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text

from db import engine, init_db
import services
from web.auth import get_db, get_current_user, require_user, require_admin
from web.websocket import manager

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="BBS Bustin'")

WEB_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(WEB_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=os.path.join(WEB_DIR, "templates"))


# ---------------------------------------------------------------------------
# Jinja2 filters
# ---------------------------------------------------------------------------

def markdown_to_html(text_content):
    if not text_content:
        return ""
    html = md.markdown(
        text_content,
        extensions=["fenced_code", "codehilite", "tables", "nl2br"],
        extension_configs={"codehilite": {"css_class": "highlight", "guess_lang": False}},
    )
    return Markup(html)


def timeago(ts):
    if not ts:
        return ""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(ts)
        diff = datetime.now() - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            m = seconds // 60
            return f"{m}m ago"
        if seconds < 86400:
            h = seconds // 3600
            return f"{h}h ago"
        d = seconds // 86400
        if d < 30:
            return f"{d}d ago"
        return ts[:10]
    except (ValueError, TypeError):
        return ts[:16] if ts else ""


def format_ts(ts):
    if not ts:
        return ""
    return ts[:16].replace("T", " ")


templates.env.filters["markdown"] = markdown_to_html
templates.env.filters["timeago"] = timeago
templates.env.filters["format_ts"] = format_ts


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _ctx(request, conn, **extra):
    """Build common template context."""
    user = get_current_user(request, conn)
    unread = 0
    if user:
        unread = services.count_unread(conn, user["id"])
    return {"request": request, "user": user, "unread": unread, **extra}


def _render(request, template_name, conn, **extra):
    """Render a template with common context. Works across Starlette versions."""
    ctx = _ctx(request, conn, **extra)
    return templates.TemplateResponse(request, template_name, ctx)


def _build_tree(posts):
    children = {}
    roots = []
    for p in posts:
        if p.get("reply_to") is None:
            roots.append(p)
        else:
            children.setdefault(p["reply_to"], []).append(p)
    return roots, children


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request, conn=Depends(get_db)):
    boards = services.list_boards(conn)
    posts = services.get_posts(conn, sort_mode="new")
    recent = [p for p in posts if not p.get("reply_to")][:20]
    return _render(request, "home.html", conn, boards=boards, recent=recent)


@app.get("/board/{name}", response_class=HTMLResponse)
def board_view(name: str, request: Request, sort: str = "default", conn=Depends(get_db)):
    boards = services.list_boards(conn)
    posts = services.get_posts(conn, board_name=name, sort_mode=sort)
    roots, children = _build_tree(posts)
    return _render(request, "board.html", conn, board_name=name, boards=boards, roots=roots, children=children, sort=sort)


@app.get("/thread/{post_id}", response_class=HTMLResponse)
def thread_view(post_id: int, request: Request, conn=Depends(get_db)):
    post = services.get_post_by_id(conn, post_id)
    if not post:
        return RedirectResponse("/", status_code=302)
    # Get all posts in same board to build thread context
    all_posts = services.get_posts(conn, board_name=post["board"])
    # Find the root of this thread
    root_id = post_id
    while True:
        p = services.get_post_by_id(conn, root_id)
        if not p or p.get("reply_to") is None:
            break
        root_id = p["reply_to"]
    # Build tree from all posts, filter to this thread
    roots, children = _build_tree(all_posts)
    root_post = next((r for r in roots if r["id"] == root_id), post)
    attachments = services.get_attachments(conn, post_id)
    return _render(request, "thread.html", conn, post=root_post, children=children, attachments=attachments)


@app.get("/profile/{username}", response_class=HTMLResponse)
def profile_view(username: str, request: Request, conn=Depends(get_db)):
    profile = services.get_user_profile(conn, username)
    if not profile:
        return RedirectResponse("/", status_code=302)
    return _render(request, "profile.html", conn, profile=profile)


@app.get("/inbox", response_class=HTMLResponse)
def inbox_view(request: Request, conn=Depends(get_db)):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse("/login", status_code=302)
    msgs = services.get_inbox(conn, user["id"])
    sent = services.get_sent(conn, user["id"])
    services.mark_read(conn, user["id"])
    users = services.list_users(conn)
    return _render(request, "inbox.html", conn, messages=msgs, sent=sent, all_users=users)


@app.get("/leaderboard", response_class=HTMLResponse)
def leaderboard_view(request: Request, game: str = None, conn=Depends(get_db)):
    games_list = ["trivia", "hangman", "numguess"]
    entries = services.get_leaderboard(conn, game=game, limit=20)
    return _render(request, "leaderboard.html", conn, entries=entries, games=games_list, current_game=game)


@app.get("/admin", response_class=HTMLResponse)
def admin_panel(request: Request, conn=Depends(get_db)):
    user = get_current_user(request, conn)
    if not user or user["role"] not in ("admin", "mod"):
        return RedirectResponse("/", status_code=302)
    users = services.list_users(conn)
    mod_log = services.get_mod_log(conn, limit=20)
    # Simple analytics
    total_posts = conn.execute(text("SELECT COUNT(*) FROM posts")).fetchone()[0]
    total_users = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
    total_boards = conn.execute(text("SELECT COUNT(*) FROM boards")).fetchone()[0]
    return _render(request, "admin.html", conn, all_users=users, mod_log=mod_log,
                   stats={"posts": total_posts, "users": total_users, "boards": total_boards})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, conn=Depends(get_db)):
    user = get_current_user(request, conn)
    if user:
        return RedirectResponse("/", status_code=302)
    return _render(request, "login.html", conn)


# ---------------------------------------------------------------------------
# Auth actions
# ---------------------------------------------------------------------------

@app.post("/login")
def login_submit(request: Request, username: str = Form(...), conn=Depends(get_db)):
    username = username.strip().lower()
    if not username or len(username) > 30:
        return RedirectResponse("/login", status_code=302)
    uid = services.get_or_create_user(conn, username)
    # Check if banned
    profile = services.get_user_profile(conn, username)
    if profile and profile.get("is_banned"):
        return RedirectResponse("/login", status_code=302)
    token = services.create_session(conn, uid)
    response = RedirectResponse("/", status_code=302)
    response.set_cookie("bbs_session", token, httponly=True, max_age=7 * 86400)
    return response


@app.post("/logout")
def logout(request: Request, conn=Depends(get_db)):
    token = request.cookies.get("bbs_session")
    if token:
        services.expire_session(conn, token)
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("bbs_session")
    return response


# ---------------------------------------------------------------------------
# Post actions
# ---------------------------------------------------------------------------

@app.post("/post")
async def create_post(
    request: Request,
    board: str = Form(...),
    message: str = Form(...),
    scheduled_at: str = Form(None),
    attachment: UploadFile = File(None),
    conn=Depends(get_db),
):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse("/login", status_code=302)
    uid = user["id"]
    bid = services.get_or_create_board(conn, board.strip().lower())
    sa = scheduled_at if scheduled_at and scheduled_at.strip() else None
    post_id = services.create_post(conn, uid, bid, message, scheduled_at=sa)
    # Handle attachment
    if attachment and attachment.filename:
        content = await attachment.read()
        if len(content) <= 5 * 1024 * 1024:  # 5MB limit
            ext = os.path.splitext(attachment.filename)[1]
            safe_name = f"{uuid.uuid4().hex}{ext}"
            filepath = os.path.join(UPLOAD_DIR, safe_name)
            with open(filepath, "wb") as f:
                f.write(content)
            services.add_attachment(conn, post_id, attachment.filename, f"/static/uploads/{safe_name}",
                                   attachment.content_type or "")
    services.check_achievements(conn, uid)
    return RedirectResponse(f"/board/{board.strip().lower()}", status_code=302)


@app.post("/reply/{post_id}")
def create_reply(post_id: int, request: Request, message: str = Form(...), conn=Depends(get_db)):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse("/login", status_code=302)
    parent = services.get_post_by_id(conn, post_id)
    if not parent:
        return RedirectResponse("/", status_code=302)
    if parent.get("is_locked"):
        return RedirectResponse(f"/thread/{post_id}", status_code=302)
    uid = user["id"]
    bid = services.get_or_create_board(conn, parent["board"])
    services.create_post(conn, uid, bid, message, reply_to=post_id)
    services.check_achievements(conn, uid)
    return RedirectResponse(f"/thread/{post_id}", status_code=302)


@app.post("/vote/{post_id}")
def vote(post_id: int, request: Request, value: int = Form(...), conn=Depends(get_db)):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse("/login", status_code=302)
    services.cast_vote(conn, user["id"], post_id, value)
    services.check_achievements(conn, user["id"])
    referer = request.headers.get("referer", "/")
    return RedirectResponse(referer, status_code=302)


@app.post("/react/{post_id}")
def react(post_id: int, request: Request, emoji: str = Form(...), conn=Depends(get_db)):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse("/login", status_code=302)
    services.add_reaction(conn, user["id"], post_id, emoji)
    services.check_achievements(conn, user["id"])
    referer = request.headers.get("referer", "/")
    return RedirectResponse(referer, status_code=302)


@app.post("/pin/{post_id}")
def pin_post(post_id: int, request: Request, conn=Depends(get_db)):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse("/login", status_code=302)
    services.pin_post(conn, post_id)
    referer = request.headers.get("referer", "/")
    return RedirectResponse(referer, status_code=302)


# ---------------------------------------------------------------------------
# Profile actions
# ---------------------------------------------------------------------------

@app.post("/profile/bio")
def update_bio(request: Request, bio: str = Form(...), conn=Depends(get_db)):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse("/login", status_code=302)
    services.update_bio(conn, user["username"], bio)
    return RedirectResponse(f"/profile/{user['username']}", status_code=302)


@app.post("/profile/avatar")
def update_avatar(request: Request, avatar: str = Form(...), conn=Depends(get_db)):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse("/login", status_code=302)
    # Limit to 10 lines, 40 chars each
    lines = avatar.split("\n")[:10]
    clean = "\n".join(line[:40] for line in lines)
    services.update_avatar(conn, user["username"], clean)
    return RedirectResponse(f"/profile/{user['username']}", status_code=302)


# ---------------------------------------------------------------------------
# DM actions
# ---------------------------------------------------------------------------

@app.post("/dm")
async def send_dm(request: Request, recipient: str = Form(...), body: str = Form(...), conn=Depends(get_db)):
    user = get_current_user(request, conn)
    if not user:
        return RedirectResponse("/login", status_code=302)
    rid = services.require_user(conn, recipient)
    if not rid:
        return RedirectResponse("/inbox", status_code=302)
    services.send_dm(conn, user["id"], rid, body)
    services.check_achievements(conn, user["id"])
    # WebSocket notification
    await manager.notify(rid, "dm", f"New message from {user['username']}")
    return RedirectResponse("/inbox", status_code=302)


# ---------------------------------------------------------------------------
# Admin actions
# ---------------------------------------------------------------------------

@app.post("/admin/ban/{username}")
def ban_user(username: str, request: Request, reason: str = Form(""), conn=Depends(get_db)):
    admin = get_current_user(request, conn)
    if not admin or admin["role"] not in ("admin", "mod"):
        return RedirectResponse("/", status_code=302)
    target_id = services.require_user(conn, username)
    if target_id:
        services.ban_user(conn, admin["id"], target_id, reason)
    return RedirectResponse("/admin", status_code=302)


@app.post("/admin/unban/{username}")
def unban_user(username: str, request: Request, conn=Depends(get_db)):
    admin = get_current_user(request, conn)
    if not admin or admin["role"] not in ("admin", "mod"):
        return RedirectResponse("/", status_code=302)
    target_id = services.require_user(conn, username)
    if target_id:
        services.unban_user(conn, admin["id"], target_id)
    return RedirectResponse("/admin", status_code=302)


@app.post("/admin/lock/{post_id}")
def lock_thread(post_id: int, request: Request, conn=Depends(get_db)):
    admin = get_current_user(request, conn)
    if not admin or admin["role"] not in ("admin", "mod"):
        return RedirectResponse("/", status_code=302)
    services.lock_post(conn, post_id)
    return RedirectResponse("/admin", status_code=302)


@app.post("/admin/delete/{post_id}")
def delete_post_admin(post_id: int, request: Request, conn=Depends(get_db)):
    admin = get_current_user(request, conn)
    if not admin or admin["role"] not in ("admin", "mod"):
        return RedirectResponse("/", status_code=302)
    services.delete_post(conn, post_id)
    services.log_mod_action(conn, admin["id"], admin["id"], "delete_post", f"Post #{post_id}")
    return RedirectResponse("/admin", status_code=302)


@app.post("/admin/role/{username}")
def set_role(username: str, request: Request, role: str = Form(...), conn=Depends(get_db)):
    admin = get_current_user(request, conn)
    if not admin or admin["role"] != "admin":
        return RedirectResponse("/", status_code=302)
    target_id = services.require_user(conn, username)
    if target_id and role in ("user", "mod", "admin"):
        services.set_user_role(conn, target_id, role)
    return RedirectResponse("/admin", status_code=302)


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.cookies.get("bbs_session")
    if not token:
        await websocket.close()
        return
    with engine.begin() as conn:
        user_id = services.validate_session(conn, token)
    if not user_id:
        await websocket.close()
        return
    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
