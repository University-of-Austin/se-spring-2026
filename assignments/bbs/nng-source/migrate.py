import json
import sys

from db import init_db
from bbs_db import bulk_insert

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

    if not posts:
        print("No posts to migrate.")
        return

    user_profiles = {}
    try:
        with open(USERS_FILE, "r") as f:
            user_profiles = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    init_db()

    added, skipped, new_users, existing_users, new_boards, existing_boards = bulk_insert(posts, user_profiles)
    print(f"Migration complete: {added} posts added, {skipped} skipped (already exist).")
    print(f"  Users: {new_users} new, {existing_users} existing")
    print(f"  Boards: {new_boards} new, {existing_boards} existing")


if __name__ == "__main__":
    migrate()
