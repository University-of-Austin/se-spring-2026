import json
import sys
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent / "bbs.json"


def load_posts():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_posts(posts):
    with open(DATA_FILE, "w") as f:
        json.dump(posts, f, indent=2)


def format_post(post):
    ts = datetime.fromisoformat(post["timestamp"])
    return f"[{ts.strftime('%Y-%m-%d %H:%M')}] {post['username']}: {post['message']}"


def cmd_post(username, message):
    posts = load_posts()
    posts.append({
        "username": username,
        "message": message,
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
    })
    save_posts(posts)
    print("Posted.")


def cmd_read():
    for post in load_posts():
        print(format_post(post))


def cmd_users():
    seen = set()
    for post in load_posts():
        seen.add(post["username"])
    for username in seen:
        print(username)


def cmd_search(keyword):
    keyword_lower = keyword.lower()
    for post in load_posts():
        if keyword_lower in post["message"].lower():
            print(format_post(post))


def main():
    if len(sys.argv) < 2:
        print("Usage: python bbs.py <command> [args]")
        print("Commands: post <username> <message>, read, users, search <keyword>")
        sys.exit(1)

    command = sys.argv[1]

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
        sys.exit(1)


if __name__ == "__main__":
    main()
