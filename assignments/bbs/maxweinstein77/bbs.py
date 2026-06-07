import json
import sys
from datetime import datetime

DATA_FILE = "bbs.json"


def load_posts():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_posts(posts):
    with open(DATA_FILE, "w") as f:
        json.dump(posts, f, indent=2)


def post_message(username, message):
    posts = load_posts()
    posts.append({
        "username": username,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    })
    save_posts(posts)
    print("Posted.")


def read_posts():
    posts = load_posts()
    if not posts:
        print("No posts yet.")
        return
    for p in posts:
        ts = datetime.fromisoformat(p["timestamp"]).strftime("%Y-%m-%d %H:%M")
        print(f"[{ts}] {p['username']}: {p['message']}")


def list_users():
    posts = load_posts()
    seen = []
    for p in posts:
        if p["username"] not in seen:
            seen.append(p["username"])
    for username in seen:
        print(username)


def search_posts(keyword):
    posts = load_posts()
    results = [p for p in posts if keyword.lower() in p["message"].lower()]
    if not results:
        print("No matching posts found.")
        return
    for p in results:
        ts = datetime.fromisoformat(p["timestamp"]).strftime("%Y-%m-%d %H:%M")
        print(f"[{ts}] {p['username']}: {p['message']}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python bbs.py <command> [args]")
        print("Commands: post, read, users, search")
        sys.exit(1)

    command = sys.argv[1]

    if command == "post":
        if len(sys.argv) < 4:
            print("Usage: python bbs.py post <username> <message>")
            sys.exit(1)
        post_message(sys.argv[2], sys.argv[3])

    elif command == "read":
        read_posts()

    elif command == "users":
        list_users()

    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python bbs.py search <keyword>")
            sys.exit(1)
        search_posts(sys.argv[2])

    else:
        print(f"Unknown command: {command}")
        print("Commands: post, read, users, search")
        sys.exit(1)


if __name__ == "__main__":
    main()
