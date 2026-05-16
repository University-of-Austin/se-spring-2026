from __future__ import annotations

import argparse
import json
from datetime import datetime

from app_paths import ensure_data_dir, get_json_path
from bbs_db_format import escape_display_text


def load_posts() -> list[dict[str, str]]:
    data_file = get_json_path()
    if not data_file.exists():
        return []

    return json.loads(data_file.read_text(encoding="utf-8"))


def save_posts(posts: list[dict[str, str]]) -> None:
    ensure_data_dir()
    get_json_path().write_text(json.dumps(posts, indent=2) + "\n", encoding="utf-8")


def format_post(post: dict[str, str]) -> str:
    timestamp = datetime.fromisoformat(post["timestamp"]).strftime("%Y-%m-%d %H:%M")
    return f"[{timestamp}] {escape_display_text(post['username'])}: {escape_display_text(post['message'])}"


def post_message(username: str, message: str) -> None:
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


def read_messages() -> None:
    for post in load_posts():
        print(format_post(post))


def list_users() -> None:
    seen: set[str] = set()
    for post in load_posts():
        username = post["username"]
        if username in seen:
            continue
        seen.add(username)
        print(escape_display_text(username))


def search_messages(keyword: str) -> None:
    needle = keyword.casefold()
    for post in load_posts():
        if needle in post["message"].casefold():
            print(format_post(post))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Simple JSON-backed BBS")
    subparsers = parser.add_subparsers(dest="command", required=True)

    post_parser = subparsers.add_parser("post", help="Post a message")
    post_parser.add_argument("username")
    post_parser.add_argument("message")

    subparsers.add_parser("read", help="Read all messages")
    subparsers.add_parser("users", help="List all users")

    search_parser = subparsers.add_parser("search", help="Search posts by keyword")
    search_parser.add_argument("keyword")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "post":
        post_message(args.username, args.message)
    elif args.command == "read":
        read_messages()
    elif args.command == "users":
        list_users()
    elif args.command == "search":
        search_messages(args.keyword)
    else:
        parser.error(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
