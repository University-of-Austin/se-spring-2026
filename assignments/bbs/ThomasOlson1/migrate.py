import json
import os
import sys
from datetime import datetime
from sqlalchemy import text
from db import engine, init_db

BBS_DATA_DIR = "bbs_data"
META_FILE = os.path.join(BBS_DATA_DIR, "meta.json")
BOARDS_DIR = os.path.join(BBS_DATA_DIR, "boards")
BBS_DB = "bbs.db"
DEFAULT_BOARD = "general"


def now_timestamp():
    return datetime.now().replace(microsecond=0).isoformat()


# ---------------------------------------------------------------------------
# Loaders — support both the new per-board structure and the legacy flat file
# ---------------------------------------------------------------------------

def load_new_structure():
    """Load from bbs_data/boards/*.json + bbs_data/meta.json.

    Returns (boards_dict, users_list) where boards_dict maps board name to a
    list of post dicts (with board-local id and parent_id).
    """
    if not os.path.exists(BOARDS_DIR):
        return None, None

    users = []
    if os.path.exists(META_FILE):
        with open(META_FILE, "r", encoding="utf-8") as f:
            meta = json.load(f)
        users = meta.get("users", [])

    boards = {}
    for fname in sorted(os.listdir(BOARDS_DIR)):
        if not fname.endswith(".json"):
            continue
        board_name = fname[:-5]
        with open(os.path.join(BOARDS_DIR, fname), "r", encoding="utf-8") as f:
            data = json.load(f)
        boards[board_name] = data.get("posts", [])

    return boards, users


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    force = "--force" in sys.argv[1:]

    if os.path.exists(BBS_DB):
        if not force:
            print(f"Error: {BBS_DB} already exists. Remove it or rerun with --force to recreate.")
            sys.exit(1)
        os.remove(BBS_DB)
    init_db()

    # Prefer the new per-board structure; fall back to legacy flat file
    boards, users = load_new_structure()
    
    if boards is None:
        print(f"Error: no data found. Expected {BOARDS_DIR}/.")
        sys.exit(1)

    print(f"Migrating from {BOARDS_DIR} ...")

    user_ids: dict[str, int] = {}
    board_ids: dict[str, int] = {}
    # Maps (board_name, board_local_id) -> sqlite posts.id so we can resolve parent_id
    local_to_sqlite: dict[tuple, int] = {}
    total_posts = 0

    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))

        # Insert users from meta first (preserves join_date and bio)
        for profile in users:
            username = profile.get("username")
            if not username:
                continue
            conn.execute(
                text(
                    "INSERT OR IGNORE INTO users (username, join_date, post_count, bio) "
                    "VALUES (:username, :join_date, 0, :bio)"
                ),
                {
                    "username": username,
                    "join_date": profile.get("join_date", now_timestamp()),
                    "bio": profile.get("bio", ""),
                },
            )
            user_ids[username] = conn.execute(
                text("SELECT id FROM users WHERE username = :username"),
                {"username": username},
            ).scalar_one()

        for board_name, posts in sorted(boards.items()):
            # Ensure board row exists
            conn.execute(
                text("INSERT OR IGNORE INTO boards (name) VALUES (:board)"),
                {"board": board_name},
            )
            board_ids[board_name] = conn.execute(
                text("SELECT id FROM boards WHERE name = :board"),
                {"board": board_name},
            ).scalar_one()
            board_id = board_ids[board_name]

            # Insert posts in board-local id order so parents always precede replies
            for post in sorted(posts, key=lambda p: p.get("id", 0)):
                username = post.get("username")
                message = post.get("message")
                timestamp = post.get("timestamp")
                if not username or not message or not timestamp:
                    print(f"  Skipping invalid post in board '{board_name}'.")
                    continue

                # Ensure user exists (handles posts whose user wasn't in meta)
                if username not in user_ids:
                    conn.execute(
                        text(
                            "INSERT OR IGNORE INTO users (username, join_date, post_count, bio) "
                            "VALUES (:username, :join_date, 0, '')"
                        ),
                        {"username": username, "join_date": timestamp},
                    )
                    user_ids[username] = conn.execute(
                        text("SELECT id FROM users WHERE username = :username"),
                        {"username": username},
                    ).scalar_one()

                user_id = user_ids[username]
                conn.execute(
                    text("UPDATE users SET post_count = post_count + 1 WHERE id = :user_id"),
                    {"user_id": user_id},
                )

                board_local_id = post.get("id")
                local_parent_id = post.get("parent_id")

                # Resolve board-local parent_id to the SQLite global id
                sqlite_parent_id = None
                if local_parent_id is not None:
                    sqlite_parent_id = local_to_sqlite.get((board_name, local_parent_id))

                result = conn.execute(
                    text(
                        "INSERT INTO posts (user_id, board_id, board_post_id, parent_id, message, timestamp, upvotes, downvotes) "
                        "VALUES (:user_id, :board_id, :board_post_id, :parent_id, :message, :timestamp, :upvotes, :downvotes)"
                    ),
                    {
                        "user_id": user_id,
                        "board_id": board_id,
                        "board_post_id": board_local_id,
                        "parent_id": sqlite_parent_id,
                        "message": message,
                        "timestamp": timestamp,
                        "upvotes": post.get("upvotes", 0),
                        "downvotes": post.get("downvotes", 0),
                    },
                )

                sqlite_id = result.lastrowid
                if board_local_id is not None:
                    local_to_sqlite[(board_name, board_local_id)] = sqlite_id
                total_posts += 1

    print(f"  {total_posts} posts migrated.")

    # Migrate votes so daily-limit and duplicate checks stay consistent after migration
    votes_file = os.path.join(BBS_DATA_DIR, "votes.json")
    vote_count = 0
    if os.path.exists(votes_file):
        with open(votes_file, "r", encoding="utf-8") as f:
            votes_data = json.load(f)
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys = ON"))
            for username, user_votes in votes_data.items():
                uid = user_ids.get(username)
                if uid is None:
                    continue
                for v in user_votes:
                    board_name = v.get("board")
                    local_id = v.get("post_id")
                    vote_type = v.get("type")
                    date = v.get("date")
                    if not all([board_name, local_id is not None, vote_type, date]):
                        continue
                    sqlite_pid = local_to_sqlite.get((board_name, local_id))
                    if sqlite_pid is None:
                        continue
                    conn.execute(
                        text(
                            "INSERT OR IGNORE INTO votes (user_id, post_id, vote_type, date) "
                            "VALUES (:uid, :pid, :vtype, :date)"
                        ),
                        {"uid": uid, "pid": sqlite_pid, "vtype": vote_type, "date": date},
                    )
                    vote_count += 1
        print(f"  {vote_count} votes migrated.")

    print(f"Migration complete. {BBS_DB} ready.")


if __name__ == "__main__":
    main()
