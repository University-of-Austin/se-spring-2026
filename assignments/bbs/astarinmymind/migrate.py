"""
Migration script: moves data from bbs.json to bbs.db

Usage:
    python migrate.py          # Migrate (fails if bbs.db exists)
    python migrate.py --force  # Overwrite existing database
"""

import json
import os
import sys

from sqlalchemy import text

from db import engine, init_db


def main():
    # Parse --force flag
    force = "--force" in sys.argv

    # Check if bbs.json exists
    if not os.path.exists("bbs.json"):
        print("Error: bbs.json not found")
        sys.exit(1)

    # Check if bbs.db already exists
    if os.path.exists("bbs.db"):
        if not force:
            print("Error: bbs.db already exists. Use --force to overwrite.")
            sys.exit(1)
        else:
            os.remove("bbs.db")

    # Initialize database (creates tables)
    init_db()

    # Read posts from JSON
    with open("bbs.json", "r") as f:
        posts = json.load(f)

    # Track unique users and their IDs
    user_ids = {}

    with engine.connect() as conn:
        # First pass: create all unique users
        for post in posts:
            username = post["username"]
            if username not in user_ids:
                result = conn.execute(
                    text("INSERT INTO users (username) VALUES (:username)"),
                    {"username": username}
                )
                user_ids[username] = result.lastrowid
        conn.commit()

        # Second pass: insert all posts with correct user_id
        for post in posts:
            user_id = user_ids[post["username"]]
            conn.execute(
                text("""
                    INSERT INTO posts (user_id, message, timestamp)
                    VALUES (:user_id, :message, :timestamp)
                """),
                {
                    "user_id": user_id,
                    "message": post["message"],
                    "timestamp": post["timestamp"]
                }
            )
        conn.commit()

    print(f"Migrated {len(posts)} posts from {len(user_ids)} users.")


if __name__ == "__main__":
    main()
