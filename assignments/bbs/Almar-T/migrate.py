#!/usr/bin/env python3
"""
Migration script: JSON → SQLite

Reads bbs.json and populates bbs.db with the same data, normalizing
usernames into the users table and linking posts via foreign keys.

Behavior: If bbs.db already contains data, this script WIPES all
tables and rebuilds from bbs.json. This ensures the database is always
an exact mirror of the JSON source after migration. Reactions, DMs,
and thread relationships (which don't exist in the JSON format) are
cleared since they have no JSON equivalent.
"""

import json
import os
import sys
from sqlalchemy import text
from db import engine, init_db

JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bbs.json")


def migrate():
    # --- Load JSON ---
    if not os.path.exists(JSON_FILE):
        print(f"Error: {JSON_FILE} not found. Nothing to migrate.")
        sys.exit(1)

    with open(JSON_FILE, "r") as f:
        posts = json.load(f)

    if not posts:
        print("bbs.json is empty. Nothing to migrate.")
        return

    # --- Ensure tables exist ---
    init_db()

    with engine.connect() as conn:
        # --- Wipe existing data (order matters for foreign keys) ---
        conn.execute(text("DELETE FROM reactions"))
        conn.execute(text("DELETE FROM messages"))
        conn.execute(text("DELETE FROM posts"))
        conn.execute(text("DELETE FROM users"))

        # --- Extract distinct usernames (preserving first-appearance order) ---
        seen = []
        for post in posts:
            if post["username"] not in seen:
                seen.append(post["username"])

        # --- Insert users and build a username → id lookup ---
        user_id_map = {}
        for username in seen:
            conn.execute(
                text("INSERT INTO users (username, created_at) VALUES (:username, :created_at)"),
                {"username": username, "created_at": posts[0]["timestamp"]},
            )
            result = conn.execute(
                text("SELECT id FROM users WHERE username = :username"),
                {"username": username},
            )
            user_id_map[username] = result.fetchone()[0]

        # --- Insert posts with correct foreign keys ---
        for post in posts:
            conn.execute(
                text("""
                    INSERT INTO posts (user_id, message, timestamp, parent_id)
                    VALUES (:user_id, :message, :timestamp, NULL)
                """),
                {
                    "user_id": user_id_map[post["username"]],
                    "message": post["message"],
                    "timestamp": post["timestamp"],
                },
            )

        conn.commit()

    print(f"Migrated {len(seen)} users and {len(posts)} posts from bbs.json to bbs.db.")


if __name__ == "__main__":
    migrate()
