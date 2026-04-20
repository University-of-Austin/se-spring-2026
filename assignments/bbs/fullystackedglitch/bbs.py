import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent / "bbs.json"


def load():
    if not DATA_FILE.exists():
        return []
    with open(DATA_FILE) as f:
        return json.load(f)


def save(posts):
    with open(DATA_FILE, "w") as f:
        json.dump(posts, f, indent=2)


def fmt(post):
    dt = datetime.fromisoformat(post["when"])
    return f"[{dt.strftime('%Y-%m-%d %H:%M')}] {post['username']}: {post['text']}"


def cmd_post(args):
    posts = load()
    posts.append({"username": args.username, "when": datetime.now().isoformat(), "text": args.message})
    save(posts)
    print("Posted.")


def cmd_read(args):
    for post in load():
        print(fmt(post))


def cmd_users(args):
    seen = set()
    users = []
    for post in load():
        u = post["username"]
        if u not in seen:
            seen.add(u)
            users.append(u)
    for u in sorted(users):
        print(u)


def cmd_search(args):
    kw = args.keyword.lower()
    for post in load():
        if kw in post["text"].lower():
            print(fmt(post))


def main():
    parser = argparse.ArgumentParser(description="BBS - JSON file storage")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("post")
    p.add_argument("username")
    p.add_argument("message")
    p.set_defaults(func=cmd_post)

    r = sub.add_parser("read")
    r.set_defaults(func=cmd_read)

    u = sub.add_parser("users")
    u.set_defaults(func=cmd_users)

    s = sub.add_parser("search")
    s.add_argument("keyword")
    s.set_defaults(func=cmd_search)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
