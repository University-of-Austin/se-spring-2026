import json
import sys
from datetime import datetime

DATA_FILE = "bbs.json"


def load_posts():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


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
        print(f"[{p['timestamp']}] {p['username']}: {p['message']}")


def users():
    posts = load_posts()
    seen = []
    for p in posts:
        if p["username"] not in seen:
            seen.append(p["username"])
    for name in seen:
        print(name)


def search(keyword):
    posts = load_posts()
    for p in posts:
        if keyword.lower() in p["message"].lower():
            print(f"[{p['timestamp']}] {p['username']}: {p['message']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bbs.py <command> [args]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "post":
        if len(sys.argv) < 4:
            print("Usage: python bbs.py post <username> <message>")
            sys.exit(1)
        post(sys.argv[2], " ".join(sys.argv[3:]))
    elif command == "read":
        read()
    elif command == "users":
        users()
    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python bbs.py search <keyword>")
            sys.exit(1)
        search(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
