"""BBS Part C: Migration from JSON to SQLite.

Reads bbs.json (and optionally bbs_users.json) and populates the SQLite database.
Uses a clean-slate approach: wipes existing DB data before importing.

Usage:
    python migrate.py              # Reads bbs.json, writes to bbs.db
    python migrate.py other.json   # Reads other.json instead
"""

import json
import os
import sys
from datetime import datetime

if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from db import engine, init_db
from sqlalchemy import text


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def migrate(json_path="bbs.json", users_path="bbs_users.json"):
    init_db()

    posts_data = load_json(json_path, [])
    users_data = load_json(users_path, {})

    if not posts_data:
        print(f"No posts found in {json_path}. Nothing to migrate.")
        return

    with engine.begin() as conn:
        # Clean slate — wipe existing data in FK order
        for table in ["reactions", "votes", "attachments", "messages", "mod_actions",
                       "sessions", "achievements", "high_scores", "posts", "boards", "users"]:
            conn.execute(text(f"DELETE FROM {table}"))

        # Extract distinct usernames from posts
        all_usernames = set(p["username"] for p in posts_data)
        # Also include users from bbs_users.json
        all_usernames.update(users_data.keys())

        # Insert users
        uid_map = {}
        for username in sorted(all_usernames):
            info = users_data.get(username, {})
            joined = info.get("joined", datetime.now().isoformat())
            bio = info.get("bio", "")
            conn.execute(
                text("INSERT INTO users (username, bio, joined) VALUES (:u, :b, :j)"),
                {"u": username, "b": bio, "j": joined},
            )
            row = conn.execute(text("SELECT last_insert_rowid()")).fetchone()
            uid_map[username] = row[0]

        # Extract distinct boards
        bid_map = {}
        all_boards = set(p.get("board", "general") for p in posts_data)
        for board_name in sorted(all_boards):
            conn.execute(text("INSERT INTO boards (name) VALUES (:n)"), {"n": board_name})
            row = conn.execute(text("SELECT last_insert_rowid()")).fetchone()
            bid_map[board_name] = row[0]

        # Insert posts, remapping IDs for reply_to
        old_to_new = {}
        for p in posts_data:
            username = p["username"]
            board = p.get("board", "general")
            reply_to = old_to_new.get(p.get("reply_to"))

            conn.execute(
                text("""INSERT INTO posts (user_id, board_id, message, timestamp, reply_to)
                         VALUES (:uid, :bid, :msg, :ts, :rt)"""),
                {
                    "uid": uid_map[username],
                    "bid": bid_map[board],
                    "msg": p["message"],
                    "ts": p["timestamp"],
                    "rt": reply_to,
                },
            )
            new_id = conn.execute(text("SELECT last_insert_rowid()")).fetchone()[0]
            old_to_new[p.get("id")] = new_id

        print(f"Migration complete:")
        print(f"  {len(uid_map)} users")
        print(f"  {len(bid_map)} boards")
        print(f"  {len(old_to_new)} posts")
        print(f"Data migrated from {json_path} → bbs.db")


if __name__ == "__main__":
    json_path = sys.argv[1] if len(sys.argv) > 1 else "bbs.json"
    migrate(json_path)
