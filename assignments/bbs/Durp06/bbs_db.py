"""BBS – Part B: SQLite-backed bulletin board system."""

import sys
from datetime import datetime

from sqlalchemy import text

from db import engine, init_db
from display import (
    fmt_board, fmt_dim, fmt_err, fmt_ok, fmt_post, fmt_search_hit,
    fmt_user, print_banner, print_header, print_profile, print_usage,
)


# ── Helpers ─────────────────────────────────────────────────────

def _get_or_create_user(conn, username):
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"), {"u": username},
    ).fetchone()
    if row:
        return row[0]
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return conn.execute(
        text("INSERT INTO users (username, joined) VALUES (:u, :j)"),
        {"u": username, "j": ts},
    ).lastrowid


def _get_or_create_board(conn, name):
    row = conn.execute(
        text("SELECT id FROM boards WHERE name = :n"), {"n": name},
    ).fetchone()
    if row:
        return row[0]
    return conn.execute(
        text("INSERT INTO boards (name) VALUES (:n)"), {"n": name},
    ).lastrowid


def _fmt_ts(ts):
    return datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")


# ── Commands ────────────────────────────────────────────────────

def cmd_post(username, board_name, message, reply_to=None):
    with engine.begin() as conn:
        uid = _get_or_create_user(conn, username)
        bid = _get_or_create_board(conn, board_name)
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if reply_to is not None:
            parent = conn.execute(
                text("SELECT id FROM posts WHERE id = :id"), {"id": reply_to},
            ).fetchone()
            if not parent:
                print(fmt_err(f"Post #{reply_to} not found."))
                sys.exit(1)
        conn.execute(
            text(
                "INSERT INTO posts (user_id, board_id, message, timestamp, reply_to) "
                "VALUES (:uid, :bid, :msg, :ts, :rt)"
            ),
            {"uid": uid, "bid": bid, "msg": message, "ts": ts, "rt": reply_to},
        )
    print(fmt_ok("Posted."))


def cmd_read(board_name=None):
    q = (
        "SELECT p.id, u.username, b.name, p.message, p.timestamp, p.reply_to "
        "FROM posts p "
        "JOIN users u ON p.user_id = u.id "
        "JOIN boards b ON p.board_id = b.id "
    )
    params = {}
    if board_name:
        q += "WHERE b.name = :board "
        params["board"] = board_name
    q += "ORDER BY p.id"

    with engine.connect() as conn:
        rows = conn.execute(text(q), params).fetchall()

    if board_name:
        print_header(f"Board: {board_name}")
    else:
        print_banner()

    if not rows:
        print(fmt_dim("No posts yet."))
        print()
        return

    roots, children = [], {}
    for pid, user, board, msg, ts, reply_to in rows:
        post = {"id": pid, "username": user, "board": board,
                "message": msg, "timestamp": ts, "reply_to": reply_to}
        if reply_to is None:
            roots.append(post)
        else:
            children.setdefault(reply_to, []).append(post)

    def walk(post, depth=0):
        ts = _fmt_ts(post["timestamp"])
        print(fmt_post(ts, post["board"], post["id"], post["username"],
                        post["message"], depth))
        for child in children.get(post["id"], []):
            walk(child, depth + 1)

    for r in roots:
        walk(r)
    print()


def cmd_users():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT username FROM users ORDER BY username")
        ).fetchall()
    print_header("Users")
    if not rows:
        print(fmt_dim("No users yet."))
        return
    for (name,) in rows:
        print(fmt_user(name))
    print()


def cmd_boards():
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT b.name, COUNT(p.id) "
                "FROM boards b LEFT JOIN posts p ON b.id = p.board_id "
                "GROUP BY b.name ORDER BY b.name"
            )
        ).fetchall()
    print_header("Boards")
    if not rows:
        print(fmt_dim("No boards yet."))
        return
    for name, count in rows:
        print(fmt_board(name, count))
    print()


def cmd_search(keyword):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT u.username, b.name, p.message, p.timestamp "
                "FROM posts p "
                "JOIN users u ON p.user_id = u.id "
                "JOIN boards b ON p.board_id = b.id "
                "WHERE p.message LIKE :kw "
                "ORDER BY p.id"
            ),
            {"kw": f"%{keyword}%"},
        ).fetchall()
    print_header(f'Search: "{keyword}"')
    if not rows:
        print(fmt_dim("No posts found."))
        return
    for user, board, msg, ts in rows:
        print(fmt_search_hit(_fmt_ts(ts), board, user, msg))
    print()


def cmd_profile(username):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, username, bio, joined FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if not row:
            print(fmt_err(f"User '{username}' not found."))
            return
        uid, uname, bio, joined = row
        count = conn.execute(
            text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"), {"uid": uid},
        ).fetchone()[0]
    print_profile(uname, _fmt_ts(joined), count, bio)


def cmd_bio(username, bio_text):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM users WHERE username = :u"), {"u": username},
        ).fetchone()
        if not row:
            _get_or_create_user(conn, username)
        conn.execute(
            text("UPDATE users SET bio = :bio WHERE username = :u"),
            {"bio": bio_text, "u": username},
        )
    print(fmt_dim("Bio updated."))


# ── CLI dispatch ────────────────────────────────────────────────

def main():
    init_db()
    args = sys.argv[1:]
    if not args:
        print_usage("bbs_db.py")
        sys.exit(1)

    cmd = args[0]

    if cmd == "post" and len(args) >= 4:
        cmd_post(args[1], args[2], args[3])
    elif cmd == "reply" and len(args) >= 4:
        try:
            reply_id = int(args[1])
        except ValueError:
            print(fmt_err("post_id must be a number."))
            sys.exit(1)
        with engine.connect() as conn:
            parent = conn.execute(
                text(
                    "SELECT b.name FROM posts p "
                    "JOIN boards b ON p.board_id = b.id "
                    "WHERE p.id = :id"
                ),
                {"id": reply_id},
            ).fetchone()
        if not parent:
            print(fmt_err(f"Post #{reply_id} not found."))
            sys.exit(1)
        cmd_post(args[2], parent[0], args[3], reply_to=reply_id)
    elif cmd == "read":
        cmd_read(args[1] if len(args) >= 2 else None)
    elif cmd == "users":
        cmd_users()
    elif cmd == "boards":
        cmd_boards()
    elif cmd == "search" and len(args) >= 2:
        cmd_search(args[1])
    elif cmd == "profile" and len(args) >= 2:
        cmd_profile(args[1])
    elif cmd == "bio" and len(args) >= 3:
        cmd_bio(args[1], args[2])
    else:
        print_usage("bbs_db.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
