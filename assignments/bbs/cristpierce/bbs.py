"""BBS Part A: JSON file storage.

A standalone command-line BBS that stores all data in bbs.json and bbs_users.json.
Supports boards, threaded replies, user profiles, and search.

Usage:
    python bbs.py post <username> <board> <message>
    python bbs.py read [board]
    python bbs.py reply <post_id> <username> <message>
    python bbs.py users
    python bbs.py boards
    python bbs.py search <keyword>
    python bbs.py profile <username>
    python bbs.py bio <username> <text>
"""

import json
import sys
from datetime import datetime

DATA_FILE = "bbs.json"
USERS_FILE = "bbs_users.json"


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_posts():
    return _load_json(DATA_FILE, [])


def save_posts(posts):
    _save_json(DATA_FILE, posts)


def load_users():
    return _load_json(USERS_FILE, {})


def save_users(users):
    _save_json(USERS_FILE, users)


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

def ensure_user(username):
    users = load_users()
    if username not in users:
        users[username] = {
            "joined": datetime.now().isoformat(),
            "bio": "",
        }
        save_users(users)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_post(username, board, message):
    ensure_user(username)
    posts = load_posts()
    post_id = max((p["id"] for p in posts), default=0) + 1
    posts.append({
        "id": post_id,
        "username": username,
        "board": board,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "reply_to": None,
    })
    save_posts(posts)
    print("Posted.")


def cmd_reply(post_id, username, message):
    ensure_user(username)
    posts = load_posts()
    parent = next((p for p in posts if p["id"] == post_id), None)
    if parent is None:
        print(f"Error: post #{post_id} not found.")
        return
    new_id = max((p["id"] for p in posts), default=0) + 1
    posts.append({
        "id": new_id,
        "username": username,
        "board": parent["board"],
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "reply_to": post_id,
    })
    save_posts(posts)
    print("Posted.")


def _build_thread_tree(posts):
    """Organize posts into a tree structure by reply_to."""
    children = {}
    roots = []
    for p in posts:
        pid = p.get("reply_to")
        if pid is None:
            roots.append(p)
        else:
            children.setdefault(pid, []).append(p)
    return roots, children


def _print_threads(posts, roots, children, indent=0):
    for post in roots:
        ts = post["timestamp"][:16].replace("T", " ")
        prefix = "  " * indent
        print(f"{prefix}[{ts}] {post['username']}: {post['message']}")
        kids = children.get(post["id"], [])
        if kids:
            _print_threads(posts, kids, children, indent + 1)


def cmd_read(board=None):
    posts = load_posts()
    if board:
        posts = [p for p in posts if p.get("board") == board]
    if not posts:
        print("No posts." if not board else f"No posts in board '{board}'.")
        return
    roots, children = _build_thread_tree(posts)
    _print_threads(posts, roots, children)


def cmd_users():
    posts = load_posts()
    usernames = sorted(set(p["username"] for p in posts))
    if not usernames:
        print("No users.")
        return
    for u in usernames:
        print(u)


def cmd_boards():
    posts = load_posts()
    board_names = sorted(set(p.get("board", "general") for p in posts))
    if not board_names:
        print("No boards.")
        return
    for b in board_names:
        count = sum(1 for p in posts if p.get("board") == b)
        print(f"  [{b}] ({count} posts)")


def cmd_search(keyword):
    posts = load_posts()
    keyword_lower = keyword.lower()
    matches = [p for p in posts if keyword_lower in p["message"].lower()]
    if not matches:
        print(f"No posts matching '{keyword}'.")
        return
    for post in matches:
        ts = post["timestamp"][:16].replace("T", " ")
        print(f"[{ts}] {post['username']}: {post['message']}")


def cmd_profile(username):
    users = load_users()
    posts = load_posts()
    if username not in users:
        print(f"User '{username}' not found.")
        return
    info = users[username]
    post_count = sum(1 for p in posts if p["username"] == username)
    print(f"═══ Profile: {username} ═══")
    print(f"  Joined:  {info['joined'][:10]}")
    print(f"  Posts:   {post_count}")
    if info.get("bio"):
        print(f"  Bio:     {info['bio']}")


def cmd_bio(username, text):
    ensure_user(username)
    users = load_users()
    users[username]["bio"] = text
    save_users(users)
    print("Bio updated.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python bbs.py <command> [args...]")
        print("Commands: post, read, reply, users, boards, search, profile, bio")
        return

    cmd = args[0].lower()

    if cmd == "post":
        if len(args) < 4:
            print("Usage: python bbs.py post <username> <board> <message>")
            return
        cmd_post(args[1], args[2], " ".join(args[3:]))

    elif cmd == "read":
        board = args[1] if len(args) > 1 else None
        cmd_read(board)

    elif cmd == "reply":
        if len(args) < 4:
            print("Usage: python bbs.py reply <post_id> <username> <message>")
            return
        try:
            post_id = int(args[1])
        except ValueError:
            print("Error: post_id must be an integer.")
            return
        cmd_reply(post_id, args[2], " ".join(args[3:]))

    elif cmd == "users":
        cmd_users()

    elif cmd == "boards":
        cmd_boards()

    elif cmd == "search":
        if len(args) < 2:
            print("Usage: python bbs.py search <keyword>")
            return
        cmd_search(" ".join(args[1:]))

    elif cmd == "profile":
        if len(args) < 2:
            print("Usage: python bbs.py profile <username>")
            return
        cmd_profile(args[1])

    elif cmd == "bio":
        if len(args) < 3:
            print("Usage: python bbs.py bio <username> <text>")
            return
        cmd_bio(args[1], " ".join(args[2:]))

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: post, read, reply, users, boards, search, profile, bio")


if __name__ == "__main__":
    main()
