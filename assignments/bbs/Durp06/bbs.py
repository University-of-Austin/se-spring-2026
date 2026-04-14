"""BBS – Part A: JSON-backed bulletin board system."""

import json
import sys
from datetime import datetime

from display import (
    fmt_board, fmt_dim, fmt_err, fmt_ok, fmt_post, fmt_search_hit,
    fmt_user, print_banner, print_header, print_profile, print_usage,
)

POSTS_FILE = "bbs.json"
USERS_FILE = "bbs_users.json"


# ── Persistence ─────────────────────────────────────────────────

def _load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []


def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_posts():
    return _load_json(POSTS_FILE, [])


def save_posts(posts):
    _save_json(POSTS_FILE, posts)


def load_users():
    return _load_json(USERS_FILE, {})


def save_users(users):
    _save_json(USERS_FILE, users)


def ensure_user(username):
    users = load_users()
    if username not in users:
        users[username] = {
            "joined": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "bio": "",
        }
        save_users(users)
    return users[username]


# ── Commands ────────────────────────────────────────────────────

def cmd_post(username, board, message, reply_to=None):
    ensure_user(username)
    posts = load_posts()
    posts.append({
        "id": len(posts) + 1,
        "username": username,
        "board": board,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "reply_to": reply_to,
    })
    save_posts(posts)
    print(fmt_ok("Posted."))


def _fmt_ts(ts):
    return datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")


def _print_threads(posts_list):
    if not posts_list:
        print(fmt_dim("No posts yet."))
        return

    roots, children = [], {}
    for p in posts_list:
        if p.get("reply_to") is None:
            roots.append(p)
        else:
            children.setdefault(p["reply_to"], []).append(p)

    def walk(post, depth=0):
        ts = _fmt_ts(post["timestamp"])
        board = post.get("board", "general")
        print(fmt_post(ts, board, post["id"], post["username"], post["message"], depth))
        for child in children.get(post["id"], []):
            walk(child, depth + 1)

    for r in roots:
        walk(r)


def cmd_read(board=None):
    posts = load_posts()
    if board:
        posts = [p for p in posts if p.get("board", "general") == board]
        print_header(f"Board: {board}")
    else:
        print_banner()
    _print_threads(posts)
    print()


def cmd_users():
    users = load_users()
    print_header("Users")
    if not users:
        print(fmt_dim("No users yet."))
        return
    for name in sorted(users):
        print(fmt_user(name))
    print()


def cmd_boards():
    posts = load_posts()
    boards = sorted({p.get("board", "general") for p in posts})
    print_header("Boards")
    if not boards:
        print(fmt_dim("No boards yet."))
        return
    for b in boards:
        count = sum(1 for p in posts if p.get("board", "general") == b)
        print(fmt_board(b, count))
    print()


def cmd_search(keyword):
    posts = load_posts()
    kw = keyword.lower()
    hits = [p for p in posts if kw in p["message"].lower()]
    print_header(f'Search: "{keyword}"')
    if not hits:
        print(fmt_dim("No posts found."))
        return
    for p in hits:
        ts = _fmt_ts(p["timestamp"])
        board = p.get("board", "general")
        print(fmt_search_hit(ts, board, p["username"], p["message"]))
    print()


def cmd_profile(username):
    users = load_users()
    if username not in users:
        print(fmt_err(f"User '{username}' not found."))
        return
    u = users[username]
    posts = load_posts()
    count = sum(1 for p in posts if p["username"] == username)
    print_profile(username, _fmt_ts(u["joined"]), count, u.get("bio", ""))


def cmd_bio(username, text):
    ensure_user(username)
    users = load_users()
    users[username]["bio"] = text
    save_users(users)
    print(fmt_dim("Bio updated."))


# ── CLI dispatch ────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    if not args:
        print_usage("bbs.py")
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
        posts = load_posts()
        parent = next((p for p in posts if p["id"] == reply_id), None)
        if not parent:
            print(fmt_err(f"Post #{reply_id} not found."))
            sys.exit(1)
        cmd_post(args[2], parent.get("board", "general"), args[3], reply_to=reply_id)
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
        print_usage("bbs.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
