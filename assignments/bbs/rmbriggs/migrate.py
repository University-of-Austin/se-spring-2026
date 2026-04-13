import json
import sys
from pathlib import Path

from sqlalchemy import text

from db import engine, init_db

JSON_FILE = Path(__file__).parent / "bbs.json"


def migrate():
    if not JSON_FILE.exists():
        print("Error: bbs.json not found.")
        sys.exit(1)

    with open(JSON_FILE, "r") as f:
        posts = json.load(f)

    if not posts:
        print("bbs.json is empty — nothing to migrate.")
        return

    init_db()

    users_migrated = 0
    posts_migrated = 0
    posts_skipped = 0

    with engine.begin() as conn:
        for post in posts:
            username = post["username"]
            message = post["message"]
            timestamp = post["timestamp"]

            # Insert user if not already present
            result = conn.execute(
                text("INSERT OR IGNORE INTO users (username) VALUES (:u)"),
                {"u": username},
            )
            if result.rowcount > 0:
                users_migrated += 1

            # Look up user_id
            user_id = conn.execute(
                text("SELECT id FROM users WHERE username = :u"),
                {"u": username},
            ).fetchone().id

            # Skip if a post with the same username + timestamp already exists
            exists = conn.execute(
                text("""
                    SELECT 1 FROM posts p JOIN users u ON p.user_id = u.id
                    WHERE u.username = :u AND p.timestamp = :ts AND p.message = :msg
                """),
                {"u": username, "ts": timestamp, "msg": message},
            ).fetchone()

            if exists:
                posts_skipped += 1
                continue

            conn.execute(
                text("""
                    INSERT INTO posts (user_id, message, timestamp, parent_id)
                    VALUES (:uid, :msg, :ts, NULL)
                """),
                {"uid": user_id, "msg": message, "ts": timestamp},
            )
            posts_migrated += 1

    print(f"Migrated {users_migrated} users, {posts_migrated} posts ({posts_skipped} skipped as duplicates).")


if __name__ == "__main__":
    migrate()
