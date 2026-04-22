import sys
import json
import os
from datetime import datetime

DATA_FILE = "bbs.json"


def load_posts():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_posts(posts):
    with open(DATA_FILE, "w") as f:
        json.dump(posts, f, indent=2)


def post(username, message):
    posts = load_posts()
    posts.append({
        "username": username,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })
    save_posts(posts)
    print("Posted.")


def read():
    posts = load_posts()
    for p in posts:
        dt = datetime.fromisoformat(p["timestamp"])
        print(f"[{dt.strftime('%Y-%m-%d %H:%M')}] {p['username']}: {p['message']}")


def users():
    posts = load_posts()
    for name in sorted(set(p["username"] for p in posts)):
        print(name)


def search(keyword):
    posts = load_posts()
    keyword_lower = keyword.lower()
    for p in posts:
        if keyword_lower in p["message"].lower():
            dt = datetime.fromisoformat(p["timestamp"])
            print(f"[{dt.strftime('%Y-%m-%d %H:%M')}] {p['username']}: {p['message']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bbs.py <command> [args]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "post" and len(sys.argv) >= 4:
        post(sys.argv[2], " ".join(sys.argv[3:]))
    elif command == "read":
        read()
    elif command == "users":
        users()
    elif command == "search" and len(sys.argv) >= 3:
        search(sys.argv[2])
    else:
        print("Usage: python bbs.py <command> [args]")
        sys.exit(1)
