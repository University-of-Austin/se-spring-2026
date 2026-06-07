#!/usr/bin/env python3
"""
bbs.py — Part A: Bulletin Board System with JSON file storage.

All posts are persisted to bbs.json as a flat list of objects.
Design decision: a single top-level array makes the file easy to
inspect with `cat` and trivial to append to without re-serialising
a complex structure.
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

BBS_FILE = "bbs.json"


# ──────────────────────────────────────────────
# Storage helpers
# ──────────────────────────────────────────────

def load_posts() -> list[dict]:
    """Return all posts from disk, or an empty list if the file is new."""
    path = Path(BBS_FILE)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as fh:
        try:
            return json.load(fh)
        except json.JSONDecodeError as e:
            print(f"Error: {BBS_FILE} is not valid JSON ({e}).")
            print("The file may be corrupted. Rename or delete it to start fresh.")
            sys.exit(1)


def save_posts(posts: list[dict]) -> None:
    """Atomically overwrite bbs.json using a temp file + os.replace."""
    dir_ = str(Path(BBS_FILE).parent)
    with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False,
                                     suffix=".tmp", encoding="utf-8") as tmp:
        json.dump(posts, tmp, indent=2, ensure_ascii=False)
    os.replace(tmp.name, BBS_FILE)


# ──────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────

def cmd_post(username: str, message: str) -> None:
    """Append a new post and persist."""
    if not message.strip():
        print("Error: message cannot be empty.")
        return
    posts = load_posts()
    posts.append(
        {
            "username": username,
            "message": message,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_posts(posts)
    print("Posted.")


def cmd_read() -> None:
    """Print every post in chronological order."""
    posts = load_posts()
    if not posts:
        print("No posts yet.")
        return
    for p in posts:
        # Display as "YYYY-MM-DD HH:MM"
        ts = p["timestamp"][:16].replace("T", " ")
        print(f"[{ts}] {p['username']}: {p['message']}")


def cmd_users() -> None:
    """Print the sorted, deduplicated list of usernames."""
    posts = load_posts()
    users = sorted({p["username"] for p in posts})
    if not users:
        print("No users yet.")
        return
    for u in users:
        print(u)


def cmd_search(keyword: str) -> None:
    """
    Linear scan through every post looking for a case-insensitive match
    in either the username or the message body.

    NOTE: This loads the entire file into memory and iterates O(n).
    For large datasets this is untenable — exactly why Part B exists.
    """
    posts = load_posts()
    kw = keyword.lower()
    results = [
        p for p in posts
        if kw in p["message"].lower() or kw in p["username"].lower()
    ]
    if not results:
        print("No results found.")
        return
    for p in results:
        ts = p["timestamp"][:16].replace("T", " ")
        print(f"[{ts}] {p['username']}: {p['message']}")


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

def usage() -> None:
    print("Usage:")
    print("  python bbs.py post <username> <message>")
    print("  python bbs.py read")
    print("  python bbs.py users")
    print("  python bbs.py search <keyword>")


def main() -> None:
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "post":
        if len(sys.argv) < 4:
            print("Error: post requires <username> and <message>.")
            sys.exit(1)
        cmd_post(sys.argv[2], " ".join(sys.argv[3:]))

    elif cmd == "read":
        cmd_read()

    elif cmd == "users":
        cmd_users()

    elif cmd == "search":
        if len(sys.argv) < 3:
            print("Error: search requires a <keyword>.")
            sys.exit(1)
        cmd_search(" ".join(sys.argv[2:]))

    else:
        print(f"Unknown command: '{cmd}'")
        usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
