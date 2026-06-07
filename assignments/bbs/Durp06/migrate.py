"""BBS – Part C: Migrate JSON data into SQLite.

Running this script reads bbs.json (and optionally bbs_users.json) and
inserts the data into bbs.db.  The database is wiped first so the
migration is idempotent — running it twice produces the same result.
"""

import json
import sys

from sqlalchemy import text

from db import engine, init_db


def migrate():
    try:
        with open("bbs.json") as f:
            posts = json.load(f)
    except FileNotFoundError:
        print("Error: bbs.json not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Error: bbs.json is not valid JSON.")
        sys.exit(1)

    if not posts:
        print("No posts to migrate.")
        return

    # Optional user-profile file
    user_profiles: dict = {}
    try:
        with open("bbs_users.json") as f:
            user_profiles = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    init_db()

    with engine.begin() as conn:
        # Wipe existing data for a clean migration
        conn.execute(text("DELETE FROM posts"))
        conn.execute(text("DELETE FROM boards"))
        conn.execute(text("DELETE FROM users"))

        # Build user rows
        usernames = sorted({p["username"] for p in posts})
        uid_map: dict[str, int] = {}
        for uname in usernames:
            profile = user_profiles.get(uname, {})
            joined = profile.get("joined", posts[0]["timestamp"])
            bio = profile.get("bio", "")
            rid = conn.execute(
                text("INSERT INTO users (username, joined, bio) VALUES (:u, :j, :b)"),
                {"u": uname, "j": joined, "b": bio},
            ).lastrowid
            uid_map[uname] = rid

        # Build board rows
        board_names = sorted({p.get("board", "general") for p in posts})
        bid_map: dict[str, int] = {}
        for bname in board_names:
            rid = conn.execute(
                text("INSERT INTO boards (name) VALUES (:n)"), {"n": bname},
            ).lastrowid
            bid_map[bname] = rid

        # Insert posts, mapping old ids to new ids for reply_to references
        old_to_new: dict[int, int] = {}
        for p in posts:
            board = p.get("board", "general")
            reply_to = p.get("reply_to")
            new_reply = old_to_new.get(reply_to) if reply_to is not None else None
            rid = conn.execute(
                text(
                    "INSERT INTO posts (user_id, board_id, message, timestamp, reply_to) "
                    "VALUES (:uid, :bid, :msg, :ts, :rt)"
                ),
                {
                    "uid": uid_map[p["username"]],
                    "bid": bid_map[board],
                    "msg": p["message"],
                    "ts": p["timestamp"],
                    "rt": new_reply,
                },
            ).lastrowid
            old_id = p.get("id")
            if old_id is not None:
                old_to_new[old_id] = rid

    print(f"Migration complete: {len(posts)} posts, {len(usernames)} users, {len(board_names)} boards.")


if __name__ == "__main__":
    migrate()
