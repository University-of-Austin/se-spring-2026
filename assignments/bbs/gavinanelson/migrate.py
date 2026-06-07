from __future__ import annotations

import argparse
import json
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from app_paths import get_db_path, get_json_path
from sqlalchemy import text

from db import engine, init_db


def load_json_posts(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError("bbs.json does not exist.")

    payload = json.loads(path.read_text())
    if not isinstance(payload, list):
        raise ValueError("bbs.json must contain a list of posts.")
    return payload


def database_has_data() -> bool:
    init_db()
    with engine.begin() as connection:
        users_count = int(connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one())
        posts_count = int(connection.execute(text("SELECT COUNT(*) FROM posts")).scalar_one())
        board_rows = connection.execute(
            text("SELECT slug FROM boards ORDER BY id ASC")
        ).fetchall()

        if users_count > 0 or posts_count > 0:
            return True
        if not board_rows:
            return False
        return any(str(row.slug) != "general" for row in board_rows)
    return False


def migrate_posts(posts: list[dict[str, object]]) -> tuple[int, int]:
    if not posts:
        return 0, 0

    user_first_seen: OrderedDict[str, str] = OrderedDict()
    for post in posts:
        username = str(post["username"])
        timestamp = str(post["timestamp"])
        user_first_seen.setdefault(username, timestamp)

    board_created_at = str(posts[0]["timestamp"])
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT OR IGNORE INTO boards (slug, name, created_at)
                VALUES (:slug, :name, :created_at)
                """
            ),
            {"slug": "general", "name": "General", "created_at": board_created_at},
        )
        board_id = connection.execute(
            text("SELECT id FROM boards WHERE slug = :slug"),
            {"slug": "general"},
        ).scalar_one()

        user_ids: dict[str, int] = {}
        for username, joined_at in user_first_seen.items():
            connection.execute(
                text(
                    """
                    INSERT INTO users (username, joined_at, bio)
                    VALUES (:username, :joined_at, :bio)
                    """
                ),
                {"username": username, "joined_at": joined_at, "bio": ""},
            )
            user_ids[username] = int(
                connection.execute(
                    text("SELECT id FROM users WHERE username = :username"),
                    {"username": username},
                ).scalar_one()
            )

        post_count = 0
        for post in posts:
            connection.execute(
                text(
                    """
                    INSERT INTO posts (user_id, board_id, parent_post_id, message, timestamp)
                    VALUES (:user_id, :board_id, :parent_post_id, :message, :timestamp)
                    """
                ),
                {
                    "user_id": user_ids[str(post["username"])],
                    "board_id": int(board_id),
                    "parent_post_id": None,
                    "message": str(post["message"]),
                    "timestamp": str(post["timestamp"]),
                },
            )
            post_count += 1

    return len(user_first_seen), post_count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Migrate bbs.json to bbs.db")
    parser.add_argument(
        "--source",
        default=str(get_json_path()),
        help="Path to the source JSON file",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    source_path = Path(args.source).expanduser().resolve()

    try:
        posts = load_json_posts(source_path)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error

    if database_has_data():
        raise SystemExit(f"{get_db_path()} already contains data; remove it before migrating.")

    users_migrated, posts_migrated = migrate_posts(posts)
    if posts_migrated == 0:
        print(f"No posts found in {source_path.name}; created an empty {get_db_path().name}.")
    else:
        print(
            f"Migrated {users_migrated} users and {posts_migrated} posts from {source_path.name} to {get_db_path().name}."
        )


if __name__ == "__main__":
    main()
