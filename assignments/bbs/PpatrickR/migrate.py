"""Migrate posts from bbs.json into the SQLite database (bbs.db).

Edge-case behavior:
  - Duplicate usernames in JSON: each distinct username gets one row in the
    users table; all their posts reference that single row.
  - Running against a non-empty database: existing users are reused (looked up
    by username).  Posts are inserted unconditionally, so running the migration
    twice will create duplicate posts.  Delete bbs.db first if you want a
    clean import.
"""

import json
import sys

from sqlalchemy import text
from db import engine, init_db

JSON_FILE = "bbs.json"


def migrate():
    with open(JSON_FILE, "r") as f:
        posts = json.load(f)

    if not posts:
        print("No posts found in bbs.json.")
        return

    init_db()

    with engine.begin() as conn:
        # Build a username -> user_id cache so we only hit the DB once per user.
        user_ids = {}

        # Find the earliest timestamp per user to use as their join date.
        earliest = {}
        for post in posts:
            name = post["username"]
            ts = post["timestamp"]
            if name not in earliest or ts < earliest[name]:
                earliest[name] = ts

        for post in posts:
            username = post["username"]

            if username not in user_ids:
                # Check if the user already exists in the database.
                row = conn.execute(
                    text("SELECT id FROM users WHERE username = :username"),
                    {"username": username},
                ).fetchone()

                if row:
                    user_ids[username] = row[0]
                else:
                    result = conn.execute(
                        text("INSERT INTO users (username, joined) VALUES (:username, :joined)"),
                        {"username": username, "joined": earliest[username]},
                    )
                    user_ids[username] = result.lastrowid

            conn.execute(
                text(
                    "INSERT INTO posts (user_id, message, timestamp) "
                    "VALUES (:user_id, :message, :timestamp)"
                ),
                {
                    "user_id": user_ids[username],
                    "message": post["message"],
                    "timestamp": post["timestamp"],
                },
            )

    print(f"Migrated {len(posts)} posts from {len(user_ids)} users.")


if __name__ == "__main__":
    migrate()
