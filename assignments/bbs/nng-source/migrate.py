import json
import sys

from sqlalchemy import text

from db import engine, init_db

DATA_FILE = "bbs.json"
USERS_FILE = "bbs_users.json"


def migrate():
    try:
        with open(DATA_FILE, "r") as f:
            posts = json.load(f)
    except FileNotFoundError:
        print(f"Error: {DATA_FILE} not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: {DATA_FILE} is not valid JSON.")
        sys.exit(1)

    # Load user profiles if they exist
    user_profiles = {}
    try:
        with open(USERS_FILE, "r") as f:
            user_profiles = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    if not posts:
        print("No posts to migrate.")
        return

    init_db()

    users_added = 0
    boards_added = 0
    posts_added = 0
    posts_skipped = 0

    with engine.begin() as conn:
        # Ensure users exist (get or create)
        usernames = sorted(set(p["username"] for p in posts))
        user_id_map = {}
        for username in usernames:
            row = conn.execute(
                text("SELECT id FROM users WHERE username = :username"),
                {"username": username},
            ).fetchone()
            if row:
                user_id_map[username] = row[0]
            else:
                profile = user_profiles.get(username, {})
                joined = profile.get("joined", posts[0]["timestamp"])
                bio = profile.get("bio", "")
                result = conn.execute(
                    text("INSERT INTO users (username, joined, bio) VALUES (:username, :joined, :bio)"),
                    {"username": username, "joined": joined, "bio": bio},
                )
                user_id_map[username] = result.lastrowid
                users_added += 1

        # Ensure boards exist (get or create)
        board_names = sorted(set(p.get("board", "general") for p in posts))
        board_id_map = {}
        for board_name in board_names:
            row = conn.execute(
                text("SELECT id FROM boards WHERE name = :name"),
                {"name": board_name},
            ).fetchone()
            if row:
                board_id_map[board_name] = row[0]
            else:
                result = conn.execute(
                    text("INSERT INTO boards (name) VALUES (:name)"),
                    {"name": board_name},
                )
                board_id_map[board_name] = result.lastrowid
                boards_added += 1

        # Insert posts, skipping duplicates
        # A post is a duplicate if same username + message + timestamp already exists
        old_to_new = {}
        for p in posts:
            board = p.get("board", "general")
            existing = conn.execute(
                text(
                    "SELECT p.id FROM posts p "
                    "JOIN users u ON p.user_id = u.id "
                    "WHERE u.username = :username "
                    "AND p.message = :message "
                    "AND p.timestamp = :timestamp"
                ),
                {
                    "username": p["username"],
                    "message": p["message"],
                    "timestamp": p["timestamp"],
                },
            ).fetchone()

            if existing:
                old_id = p.get("id")
                if old_id is not None:
                    old_to_new[old_id] = existing[0]
                posts_skipped += 1
                continue

            reply_to = p.get("reply_to")
            new_reply_to = old_to_new.get(reply_to) if reply_to is not None else None

            result = conn.execute(
                text(
                    "INSERT INTO posts (user_id, board_id, message, timestamp, reply_to) "
                    "VALUES (:user_id, :board_id, :message, :timestamp, :reply_to)"
                ),
                {
                    "user_id": user_id_map[p["username"]],
                    "board_id": board_id_map[board],
                    "message": p["message"],
                    "timestamp": p["timestamp"],
                    "reply_to": new_reply_to,
                },
            )
            old_id = p.get("id")
            if old_id is not None:
                old_to_new[old_id] = result.lastrowid
            posts_added += 1

    print(f"Migration complete: {posts_added} posts added, {posts_skipped} skipped (already exist).")
    print(f"  Users: {users_added} new, {len(usernames) - users_added} existing")
    print(f"  Boards: {boards_added} new, {len(board_names) - boards_added} existing")


if __name__ == "__main__":
    migrate()
