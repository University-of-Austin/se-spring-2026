"""
migrate.py - Migrate data from bbs.json to bbs.db (SQLite).

Behavior:
- Reads every post from bbs.json.
- For each distinct username, inserts a row into `users` using INSERT OR IGNORE
  so existing users are left untouched (no duplicates).
- For posts, checks whether an identical (username, message, timestamp) triple
  already exists in the database before inserting. If it does, the post is
  skipped. This makes the script safe to run multiple times (idempotent).
- If bbs.json does not exist, the script exits with an informative message.

Why idempotent? Re-running a migration should never corrupt data. This choice
means you can safely migrate a partial JSON file, add more posts to it, and
migrate again without duplicating earlier entries.
"""

import json
import os
import sys

from sqlalchemy import text

from db import engine, init_db

BBS_FILE = "bbs.json"


def main():
    if not os.path.exists(BBS_FILE):
        print(f"Error: '{BBS_FILE}' not found. Run bbs.py to create it first.")
        sys.exit(1)

    with open(BBS_FILE, "r", encoding="utf-8") as f:
        posts = json.load(f)

    if not posts:
        print("bbs.json is empty -- nothing to migrate.")
        return

    init_db()

    inserted_users = 0
    skipped_users = 0
    inserted_posts = 0
    skipped_posts = 0

    with engine.begin() as conn:
        for post in posts:
            username = post["username"]
            message = post["message"]
            timestamp = post["timestamp"]

            # Use the post's original timestamp as the user's join date if we
            # have to create the user, falling back to the earliest post seen.
            result = conn.execute(
                text("""
                    INSERT OR IGNORE INTO users (username, created_at)
                    VALUES (:u, :ts)
                """),
                {"u": username, "ts": timestamp},
            )
            if result.rowcount:
                inserted_users += 1
            else:
                skipped_users += 1

            # Fetch user id (always present after INSERT OR IGNORE)
            user_id = conn.execute(
                text("SELECT id FROM users WHERE username = :u"),
                {"u": username},
            ).scalar()

            # Check for duplicate post (same user, message, timestamp)
            exists = conn.execute(
                text("""
                    SELECT 1 FROM posts
                    WHERE user_id = :uid
                      AND message   = :msg
                      AND timestamp = :ts
                    LIMIT 1
                """),
                {"uid": user_id, "msg": message, "ts": timestamp},
            ).fetchone()

            if exists:
                skipped_posts += 1
                continue

            conn.execute(
                text("""
                    INSERT INTO posts (user_id, message, timestamp, parent_id)
                    VALUES (:uid, :msg, :ts, NULL)
                """),
                {"uid": user_id, "msg": message, "ts": timestamp},
            )
            inserted_posts += 1

    print(f"Migration complete.")
    print(f"  Users - inserted: {inserted_users}, skipped (already existed): {skipped_users}")
    print(f"  Posts - inserted: {inserted_posts}, skipped (already existed): {skipped_posts}")


if __name__ == "__main__":
    main()
