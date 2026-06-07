import json
import os
import sys

from sqlalchemy import text
from db import engine, init_db

JSON_FILE = "bbs.json"


def migrate():
    init_db()

    if not os.path.exists(JSON_FILE):
        print(f"No {JSON_FILE} file found. Nothing to migrate — create some posts with bbs.py first.")
        sys.exit(0)

    with open(JSON_FILE, "r") as f:
        posts = json.load(f)

    unique_usernames = []
    for p in posts:
        if p["username"] not in unique_usernames:
            unique_usernames.append(p["username"])

    user_ids = {}
    with engine.begin() as conn:
        for username in unique_usernames:
            row = conn.execute(
                text("SELECT id FROM users WHERE username = :username"),
                {"username": username}
            ).fetchone()
            if row is None:
                conn.execute(
                    text("INSERT INTO users (username) VALUES (:username)"),
                    {"username": username}
                )
                row = conn.execute(
                    text("SELECT id FROM users WHERE username = :username"),
                    {"username": username}
                ).fetchone()
            user_ids[username] = row[0]

        for p in posts:
            user_id = user_ids[p["username"]]
            existing = conn.execute(
                text(
                    "SELECT id FROM posts "
                    "WHERE user_id = :user_id AND timestamp = :timestamp"
                ),
                {"user_id": user_id, "timestamp": p["timestamp"]}
            ).fetchone()
            if existing is not None:
                continue
            conn.execute(
                text(
                    "INSERT INTO posts (user_id, message, timestamp) "
                    "VALUES (:user_id, :message, :timestamp)"
                ),
                {
                    "user_id": user_id,
                    "message": p["message"],
                    "timestamp": p["timestamp"],
                }
            )

    print(f"Migrated {len(unique_usernames)} users and {len(posts)} posts.")


if __name__ == "__main__":
    migrate()
