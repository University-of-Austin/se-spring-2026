import json
import sys
from datetime import datetime

from sqlalchemy import text

from db import engine, init_db
from display import (
    fmt_board_line, fmt_error, fmt_info, fmt_post_line, fmt_posted,
    fmt_search_line, fmt_user_line, print_profile, print_section_header,
    print_usage, print_welcome,
)


def get_or_create_user(conn, username):
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    ).fetchone()
    if row:
        return row[0]
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    result = conn.execute(
        text("INSERT INTO users (username, joined) VALUES (:username, :joined)"),
        {"username": username, "joined": ts},
    )
    return result.lastrowid


def get_or_create_board(conn, board_name):
    row = conn.execute(
        text("SELECT id FROM boards WHERE name = :name"),
        {"name": board_name},
    ).fetchone()
    if row:
        return row[0]
    result = conn.execute(
        text("INSERT INTO boards (name) VALUES (:name)"),
        {"name": board_name},
    )
    return result.lastrowid


def post_message(username, board_name, message, reply_to=None):
    with engine.begin() as conn:
        user_id = get_or_create_user(conn, username)
        board_id = get_or_create_board(conn, board_name)
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if reply_to is not None:
            parent = conn.execute(
                text("SELECT id FROM posts WHERE id = :id"),
                {"id": reply_to},
            ).fetchone()
            if not parent:
                print(fmt_error(f"Post #{reply_to} not found."))
                sys.exit(1)
        conn.execute(
            text(
                "INSERT INTO posts (user_id, board_id, message, timestamp, reply_to) "
                "VALUES (:user_id, :board_id, :message, :timestamp, :reply_to)"
            ),
            {
                "user_id": user_id,
                "board_id": board_id,
                "message": message,
                "timestamp": ts,
                "reply_to": reply_to,
            },
        )
    print(fmt_posted())


def format_timestamp(ts):
    dt = datetime.fromisoformat(ts)
    return dt.strftime("%Y-%m-%d %H:%M")


def read_posts(board_name=None):
    query = (
        "SELECT p.id, u.username, b.name, p.message, p.timestamp, p.reply_to "
        "FROM posts p "
        "JOIN users u ON p.user_id = u.id "
        "JOIN boards b ON p.board_id = b.id "
    )
    params = {}
    if board_name:
        query += "WHERE b.name = :board "
        params["board"] = board_name
    query += "ORDER BY p.id"

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    if board_name:
        print_section_header(f"Board: {board_name}")
    else:
        print_welcome()

    if not rows:
        print(fmt_info("No posts yet."))
        print()
        return

    top_level = []
    replies_map = {}
    for row in rows:
        pid, username, board, message, timestamp, reply_to = row
        post = {
            "id": pid,
            "username": username,
            "board": board,
            "message": message,
            "timestamp": timestamp,
            "reply_to": reply_to,
        }
        if reply_to is None:
            top_level.append(post)
        else:
            replies_map.setdefault(reply_to, []).append(post)

    def print_thread(post, indent=0):
        ts = format_timestamp(post["timestamp"])
        print(fmt_post_line(ts, post["board"], post["id"], post["username"], post["message"], indent))
        for reply in replies_map.get(post["id"], []):
            print_thread(reply, indent + 1)

    for p in top_level:
        print_thread(p)
    print()


def list_users():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT username FROM users ORDER BY username")
        ).fetchall()
    print_section_header("Users")
    if not rows:
        print(fmt_info("No users yet."))
        return
    for row in rows:
        print(fmt_user_line(row[0]))
    print()


def list_boards():
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT b.name, COUNT(p.id) "
                "FROM boards b LEFT JOIN posts p ON b.id = p.board_id "
                "GROUP BY b.name ORDER BY b.name"
            )
        ).fetchall()
    print_section_header("Boards")
    if not rows:
        print(fmt_info("No boards yet."))
        return
    for row in rows:
        print(fmt_board_line(row[0], row[1]))
    print()


def search_posts(keyword):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT u.username, b.name, p.message, p.timestamp "
                "FROM posts p "
                "JOIN users u ON p.user_id = u.id "
                "JOIN boards b ON p.board_id = b.id "
                "WHERE p.message LIKE :keyword "
                "ORDER BY p.id"
            ),
            {"keyword": f"%{keyword}%"},
        ).fetchall()

    print_section_header(f"Search: \"{keyword}\"")
    if not rows:
        print(fmt_info("No posts found."))
        return
    for row in rows:
        username, board, message, timestamp = row
        ts = format_timestamp(timestamp)
        print(fmt_search_line(ts, board, username, message))
    print()


def show_profile(username):
    with engine.connect() as conn:
        user = conn.execute(
            text("SELECT id, username, bio, joined FROM users WHERE username = :username"),
            {"username": username},
        ).fetchone()
        if not user:
            print(fmt_error(f"User '{username}' not found."))
            return
        user_id, uname, bio, joined = user
        post_count = conn.execute(
            text("SELECT COUNT(*) FROM posts WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).fetchone()[0]
    joined_fmt = format_timestamp(joined)
    print_profile(uname, joined_fmt, post_count, bio)


def set_bio(username, bio_text):
    with engine.begin() as conn:
        user = conn.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": username},
        ).fetchone()
        if not user:
            get_or_create_user(conn, username)
        conn.execute(
            text("UPDATE users SET bio = :bio WHERE username = :username"),
            {"bio": bio_text, "username": username},
        )
    print(fmt_info("Bio updated."))


def export_db(filepath):
    with engine.connect() as conn:
        # Export posts
        rows = conn.execute(
            text(
                "SELECT p.id, u.username, b.name, p.message, p.timestamp, p.reply_to "
                "FROM posts p "
                "JOIN users u ON p.user_id = u.id "
                "JOIN boards b ON p.board_id = b.id "
                "ORDER BY p.id"
            )
        ).fetchall()

        posts = []
        for row in rows:
            pid, username, board, message, timestamp, reply_to = row
            posts.append({
                "id": pid,
                "username": username,
                "board": board,
                "message": message,
                "timestamp": timestamp,
                "reply_to": reply_to,
            })

        # Export user profiles
        user_rows = conn.execute(
            text("SELECT username, joined, bio FROM users ORDER BY username")
        ).fetchall()

        users = {}
        for row in user_rows:
            username, joined, bio = row
            users[username] = {"joined": joined, "bio": bio or ""}

    data = {"posts": posts, "users": users}
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    print(fmt_info(f"Exported {len(posts)} posts and {len(users)} users to {filepath}"))


def bulk_insert(posts, user_profiles=None):
    """Insert posts into DB, skipping duplicates. Returns (added, skipped, new_users, new_boards) counts."""
    if user_profiles is None:
        user_profiles = {}

    posts_added = 0
    posts_skipped = 0
    users_added = 0
    boards_added = 0

    with engine.begin() as conn:
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
                {"username": p["username"], "message": p["message"], "timestamp": p["timestamp"]},
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

    return posts_added, posts_skipped, users_added, len(usernames) - users_added, boards_added, len(board_names) - boards_added


def import_db(filepath):
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(fmt_error(f"{filepath} not found."))
        sys.exit(1)
    except json.JSONDecodeError:
        print(fmt_error(f"{filepath} is not valid JSON."))
        sys.exit(1)

    posts = data.get("posts", [])
    user_profiles = data.get("users", {})

    if not posts:
        print(fmt_info("No posts to import."))
        return

    added, skipped, new_users, existing_users, new_boards, existing_boards = bulk_insert(posts, user_profiles)
    print(fmt_info(f"Import complete: {added} posts added, {skipped} skipped (already exist)."))
    print(fmt_info(f"  Users: {new_users} new, {existing_users} existing"))
    print(fmt_info(f"  Boards: {new_boards} new, {existing_boards} existing"))


def main():
    init_db()

    if len(sys.argv) < 2:
        print_usage("bbs_db.py")
        sys.exit(1)

    command = sys.argv[1]

    if command == "post" and len(sys.argv) >= 5:
        post_message(sys.argv[2], sys.argv[3], sys.argv[4])
    elif command == "reply" and len(sys.argv) >= 5:
        try:
            reply_to = int(sys.argv[2])
        except ValueError:
            print(fmt_error("post_id must be a number."))
            sys.exit(1)
        with engine.connect() as conn:
            parent = conn.execute(
                text(
                    "SELECT b.name FROM posts p "
                    "JOIN boards b ON p.board_id = b.id "
                    "WHERE p.id = :id"
                ),
                {"id": reply_to},
            ).fetchone()
        if not parent:
            print(fmt_error(f"Post #{reply_to} not found."))
            sys.exit(1)
        post_message(sys.argv[3], parent[0], sys.argv[4], reply_to=reply_to)
    elif command == "read":
        board = sys.argv[2] if len(sys.argv) >= 3 else None
        read_posts(board)
    elif command == "users":
        list_users()
    elif command == "boards":
        list_boards()
    elif command == "search" and len(sys.argv) >= 3:
        search_posts(sys.argv[2])
    elif command == "profile" and len(sys.argv) >= 3:
        show_profile(sys.argv[2])
    elif command == "bio" and len(sys.argv) >= 4:
        set_bio(sys.argv[2], sys.argv[3])
    elif command == "export":
        filepath = sys.argv[2] if len(sys.argv) >= 3 else "export.json"
        export_db(filepath)
    elif command == "import" and len(sys.argv) >= 3:
        import_db(sys.argv[2])
    else:
        print_usage("bbs_db.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
