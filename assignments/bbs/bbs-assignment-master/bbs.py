"""
BBS - Bulletin Board System (Part A: JSON File Storage)
Usage:
    python bbs.py post <username> <message>
    python bbs.py read
    python bbs.py users
    python bbs.py search <keyword>
"""

import sys
import json
import os
from datetime import datetime

BBS_FILE = "bbs.json"


def load_posts():
    if not os.path.exists(BBS_FILE):
        return []
    with open(BBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_posts(posts):
    with open(BBS_FILE, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2)


def cmd_post(username, message):
    posts = load_posts()
    posts.append({
        "username": username,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    })
    save_posts(posts)
    print("Posted.")


def cmd_read():
    posts = load_posts()
    if not posts:
        print("No messages yet.")
        return
    for post in posts:
        ts = post["timestamp"].replace("T", " ")[:16]
        print(f"[{ts}] {post['username']}: {post['message']}")


def cmd_users():
    posts = load_posts()
    seen = []
    seen_set = set()
    for post in posts:
        uname = post["username"]
        if uname not in seen_set:
            seen_set.add(uname)
            seen.append(uname)
    if not seen:
        print("No users yet.")
        return
    for uname in seen:
        print(uname)


def cmd_search(keyword):
    posts = load_posts()
    keyword_lower = keyword.lower()
    found = False
    for post in posts:
        if keyword_lower in post["message"].lower():
            ts = post["timestamp"].replace("T", " ")[:16]
            print(f"[{ts}] {post['username']}: {post['message']}")
            found = True
    if not found:
        print(f"No posts matching '{keyword}'.")


def print_usage():
    print("BBS - Bulletin Board System (JSON version)")
    print()
    print("Usage:")
    print("  python bbs.py post <username> <message>")
    print("  python bbs.py read")
    print("  python bbs.py users")
    print("  python bbs.py search <keyword>")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "post":
        if len(sys.argv) < 4:
            print("Usage: python bbs.py post <username> <message>")
            sys.exit(1)
        cmd_post(sys.argv[2], sys.argv[3])

    elif cmd == "read":
        cmd_read()

    elif cmd == "users":
        cmd_users()

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Usage: python bbs.py search <keyword>")
            sys.exit(1)
        cmd_search(sys.argv[2])

    else:
        print(f"Unknown command: {cmd}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
