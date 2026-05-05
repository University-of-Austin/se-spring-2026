import json
import sys
from pathlib import Path

from sqlalchemy import text

from db import engine, init_db

JSON_FILE = Path(__file__).with_name("bbs.json")


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def migrate():
    try:
        with JSON_FILE.open(encoding="utf-8") as f:
            posts = json.load(f)
    except FileNotFoundError:
        die(f"{JSON_FILE.name} not found.")
    except json.JSONDecodeError:
        die(f"Invalid JSON in {JSON_FILE.name}.")

    if not isinstance(posts, list):
        die(f"{JSON_FILE.name} must contain a list of posts.")

    init_db()

    if not posts:
        print("No posts to migrate.")
        return

    with engine.begin() as conn:
        if conn.execute(text("SELECT COUNT(*) FROM users")).scalar():
            die("bbs.db already contains data. Delete bbs.db and retry.")

        user_first_seen = {}
        for p in posts:
            name = p["username"].lower()
            if name not in user_first_seen:
                user_first_seen[name] = p["timestamp"]
        conn.execute(
            text("INSERT INTO users (username, created_at) VALUES (:username, :created_at)"),
            [{"username": u, "created_at": ts} for u, ts in user_first_seen.items()],
        )

        rows = conn.execute(text("SELECT id, username FROM users"))
        user_ids = {row.username: row.id for row in rows}

        conn.execute(
            text("""
                INSERT INTO posts (user_id, message, timestamp)
                VALUES (:user_id, :message, :ts)
            """),
            [
                {"user_id": user_ids[p["username"].lower()], "message": p["message"], "ts": p["timestamp"]}
                for p in posts
            ],
        )

    print(f"Migrated {len(posts)} posts from {len(user_first_seen)} users.")


if __name__ == "__main__":
    migrate()
