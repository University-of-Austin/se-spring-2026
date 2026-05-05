import json
import sys
from sqlalchemy import text
from db import engine, init_db

DATA_FILE = "bbs.json"


def main():
    # Load JSON data
    try:
        with open(DATA_FILE, "r") as f:
            posts = json.load(f)
    except FileNotFoundError:
        print(f"Error: {DATA_FILE} not found.")
        sys.exit(1)

    if not posts:
        print(f"Error: {DATA_FILE} is empty.")
        sys.exit(1)

    # Create tables if they don't exist
    init_db()

    # Check if database already has data
    with engine.connect() as conn:
        user_count = conn.execute(text("SELECT COUNT(*) FROM users")).fetchone()[0]
        post_count = conn.execute(text("SELECT COUNT(*) FROM posts")).fetchone()[0]

        if user_count > 0 or post_count > 0:
            print("Error: bbs.db already has data. Migration aborted to prevent data loss.")
            print("If you want to re-migrate, delete bbs.db first and run again.")
            sys.exit(1)

        # Extract distinct usernames in order of first appearance
        seen = []
        for post in posts:
            if post["username"] not in seen:
                seen.append(post["username"])

        # Insert users
        for username in seen:
            conn.execute(
                text("INSERT INTO users (username) VALUES (:username)"),
                {"username": username},
            )

        # Build a lookup of username -> user_id
        rows = conn.execute(text("SELECT id, username FROM users")).fetchall()
        user_ids = {row[1]: row[0] for row in rows}

        # Insert posts with correct foreign keys, preserving original timestamps
        for post in posts:
            conn.execute(
                text("INSERT INTO posts (user_id, message, timestamp) VALUES (:user_id, :message, :timestamp)"),
                {
                    "user_id": user_ids[post["username"]],
                    "message": post["message"],
                    "timestamp": post["timestamp"],
                },
            )

        conn.commit()

    print(f"Migration complete: {len(seen)} users and {len(posts)} posts imported.")


if __name__ == "__main__":
    main()
