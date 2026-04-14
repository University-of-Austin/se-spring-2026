import json
import sys
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).with_name("bbs.json")


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def load_posts():
    try:
        with DATA_FILE.open(encoding="utf-8") as f:
            posts = json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        die(f"Invalid JSON in {DATA_FILE.name}.")

    if not isinstance(posts, list):
        die(f"{DATA_FILE.name} must contain a list of posts.")

    return posts


def save_posts(posts):
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2)
        f.write("\n")


def fmt_post(post):
    ts = datetime.fromisoformat(post["timestamp"])
    return f"[{ts:%Y-%m-%d %H:%M}] {post['username']}: {post['message']}"


def cmd_post(args):
    if len(args) != 2:
        die("Usage: bbs.py post <username> <message>")
    username, message = args[0].lower(), args[1]
    posts = load_posts()
    posts.append({
        "username": username,
        "message": message,
        "timestamp": datetime.now().replace(microsecond=0).isoformat(),
    })
    save_posts(posts)
    print("Posted.")


def cmd_read(args):
    if args:
        die("Usage: bbs.py read")
    for post in load_posts():
        print(fmt_post(post))


def cmd_users(args):
    if args:
        die("Usage: bbs.py users")
    for username in dict.fromkeys(p["username"] for p in load_posts()):
        print(username)


def cmd_search(args):
    if len(args) != 1:
        die("Usage: bbs.py search <keyword>")
    keyword = args[0].lower()
    for post in load_posts():
        if keyword in post["message"].lower():
            print(fmt_post(post))


def cmd_usage(_args):
    print("Usage: bbs.py <command> [args]")
    print()
    print("Commands:")
    print("  post <username> <message>   Post a message")
    print("  read                        Read all messages")
    print("  users                       List all users")
    print("  search <keyword>            Search posts by keyword")


commands = {
    "post": cmd_post,
    "read": cmd_read,
    "users": cmd_users,
    "search": cmd_search,
}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd and cmd not in commands:
        die(f"Unknown command: {cmd}. Run with no arguments for usage.")
    commands.get(cmd, cmd_usage)(sys.argv[2:])
