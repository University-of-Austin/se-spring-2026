#!/usr/bin/env python3
"""
BBS (Bulletin Board System) - JSON File Storage Version

A command-line bulletin board that stores all data in a flat JSON file.
Supports posting messages, reading the board, listing users, and searching.
"""

import json
import sys
import os
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bbs.json")


def load_posts():
    """Load all posts from the JSON file. Returns an empty list if the file doesn't exist."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_posts(posts):
    """Write the full posts list back to the JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(posts, f, indent=2)


def cmd_post(username, message):
    """Append a new post with the current timestamp."""
    posts = load_posts()
    posts.append({
        "username": username,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    })
    save_posts(posts)
    print("Posted.")


def cmd_read():
    """Display all posts in chronological order."""
    posts = load_posts()
    if not posts:
        print("No posts yet.")
        return
    for post in posts:
        ts = datetime.fromisoformat(post["timestamp"]).strftime("%Y-%m-%d %H:%M")
        print(f"[{ts}] {post['username']}: {post['message']}")


def cmd_users():
    """List every unique username that has posted, in the order they first appeared."""
    posts = load_posts()
    seen = []
    for post in posts:
        if post["username"] not in seen:
            seen.append(post["username"])
    for user in seen:
        print(user)


def cmd_search(keyword):
    """Find posts containing the keyword (case-insensitive)."""
    posts = load_posts()
    keyword_lower = keyword.lower()
    matches = [p for p in posts if keyword_lower in p["message"].lower()]
    if not matches:
        print("No matching posts found.")
        return
    for post in matches:
        ts = datetime.fromisoformat(post["timestamp"]).strftime("%Y-%m-%d %H:%M")
        print(f"[{ts}] {post['username']}: {post['message']}")


def print_usage():
    print("Usage:")
    print("  python bbs.py post <username> <message>   - Post a message")
    print("  python bbs.py read                        - Read all messages")
    print("  python bbs.py users                       - List all users")
    print('  python bbs.py search <keyword>            - Search posts by keyword')


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "post":
        if len(sys.argv) < 4:
            print("Usage: python bbs.py post <username> <message>")
            sys.exit(1)
        cmd_post(sys.argv[2], sys.argv[3])

    elif command == "read":
        cmd_read()

    elif command == "users":
        cmd_users()

    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python bbs.py search <keyword>")
            sys.exit(1)
        cmd_search(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
