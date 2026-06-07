from __future__ import annotations

import argparse
from pathlib import Path

from app_paths import default_backup_path, default_export_path, get_data_dir, get_db_path, get_json_path
from bbs_db_format import escape_display_text, format_post, format_profile, format_threaded_posts
from bbs_db_store import (
    backup_database,
    create_board,
    create_post,
    create_reply,
    export_posts_to_json,
    get_profile,
    list_boards,
    list_users,
    read_all_posts,
    read_posts,
    search_posts,
    set_initial_pin,
    set_bio,
    update_user_pin,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SQLite-backed BBS")
    subparsers = parser.add_subparsers(dest="command", required=True)

    post_parser = subparsers.add_parser("post", help="Post a message")
    post_parser.add_argument("arguments", nargs="+")

    subparsers.add_parser("read", help="Read all messages")

    read_board_parser = subparsers.add_parser("read-board", help="Read one board")
    read_board_parser.add_argument("board")
    subparsers.add_parser("users", help="List all users")
    subparsers.add_parser("boards", help="List boards")

    create_board_parser = subparsers.add_parser("create-board", help="Create a board")
    create_board_parser.add_argument("board")

    search_parser = subparsers.add_parser("search", help="Search posts by keyword")
    search_parser.add_argument("keyword")

    reply_parser = subparsers.add_parser("reply", help="Reply to a post")
    reply_parser.add_argument("username")
    reply_parser.add_argument("post_id", type=int)
    reply_parser.add_argument("message")

    profile_parser = subparsers.add_parser("profile", help="Show a user profile")
    profile_parser.add_argument("username")

    set_bio_parser = subparsers.add_parser("set-bio", help="Set a user bio")
    set_bio_parser.add_argument("username")
    set_bio_parser.add_argument("bio")

    init_pin_parser = subparsers.add_parser("init-pin", help="Set the initial PIN for a setup-required account")
    init_pin_parser.add_argument("username")
    init_pin_parser.add_argument("pin")

    change_pin_parser = subparsers.add_parser("change-pin", help="Change a user's PIN")
    change_pin_parser.add_argument("username")
    change_pin_parser.add_argument("current_pin")
    change_pin_parser.add_argument("new_pin")

    export_parser = subparsers.add_parser("export-json", help="Export posts to a JSON file")
    export_parser.add_argument("destination", nargs="?", default=str(default_export_path()))

    backup_parser = subparsers.add_parser("backup", help="Copy the SQLite database to a backup file")
    backup_parser.add_argument("destination", nargs="?", default=str(default_backup_path()))

    subparsers.add_parser("paths", help="Show the active data and storage paths")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "post":
            if len(args.arguments) == 2:
                username, message = args.arguments
                created_board, board_slug = create_post(username, message)
            elif len(args.arguments) == 3:
                username, board, message = args.arguments
                created_board, board_slug = create_post(username, message, board)
            else:
                parser.error("post expects '<username> <message>' or '<username> <board> <message>'")

            if created_board and board_slug != "general":
                print(f"Created board {board_slug}.")
            print("Posted.")
        elif args.command == "reply":
            try:
                create_reply(args.username, args.post_id, args.message)
            except ValueError as error:
                parser.exit(1, f"{error}\n")
            print("Posted.")
        elif args.command == "read":
            for post in read_all_posts():
                print(format_post(post))
        elif args.command == "read-board":
            for line in format_threaded_posts(read_posts(args.board)):
                print(line)
        elif args.command == "users":
            for username in list_users():
                print(escape_display_text(username))
        elif args.command == "boards":
            for board in list_boards():
                print(board)
        elif args.command == "create-board":
            created, board_slug = create_board(args.board)
            if created:
                print(f"Created board {board_slug}.")
            else:
                print(f"Board {board_slug} already exists.")
        elif args.command == "search":
            for post in search_posts(args.keyword):
                print(format_post(post))
        elif args.command == "profile":
            profile = get_profile(args.username)
            if profile is None:
                parser.exit(1, f"User {args.username} does not exist.\n")
            print(format_profile(profile))
        elif args.command == "set-bio":
            try:
                set_bio(args.username, args.bio)
            except ValueError as error:
                parser.exit(1, f"{error}\n")
            print("Bio updated.")
        elif args.command == "init-pin":
            try:
                set_initial_pin(args.username, args.pin)
            except ValueError as error:
                parser.exit(1, f"{error}\n")
            print("PIN initialized.")
        elif args.command == "change-pin":
            try:
                update_user_pin(args.username, args.current_pin, args.new_pin)
            except ValueError as error:
                parser.exit(1, f"{error}\n")
            print("PIN updated.")
        elif args.command == "export-json":
            path = export_posts_to_json(Path(args.destination))
            print(f"Exported posts to {path}")
        elif args.command == "backup":
            path = backup_database(Path(args.destination))
            print(f"Backed up database to {path}")
        elif args.command == "paths":
            print(f"Data directory: {get_data_dir()}")
            print(f"SQLite database: {get_db_path()}")
            print(f"JSON file: {get_json_path()}")
        else:
            parser.error(f"Unsupported command: {args.command}")
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
