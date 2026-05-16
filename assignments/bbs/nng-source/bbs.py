import json
import sys
from datetime import datetime

from display import (
    fmt_board_line, fmt_error, fmt_info, fmt_post_line, fmt_posted,
    fmt_search_line, fmt_user_line, print_profile, print_section_header,
    print_usage, print_welcome,
)

DATA_FILE = "bbs.json"
USERS_FILE = "bbs_users.json"


def load_data(filepath, default=None):
    if default is None:
        default = []
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_data(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def load_posts():
    return load_data(DATA_FILE, [])


def save_posts(posts):
    save_data(DATA_FILE, posts)


def load_users():
    return load_data(USERS_FILE, {})


def save_users(users):
    save_data(USERS_FILE, users)


def get_or_create_user(username):
    users = load_users()
    if username not in users:
        users[username] = {
            "joined": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "bio": "",
        }
        save_users(users)
    return users[username]


def post_message(username, board, message, reply_to=None):
    get_or_create_user(username)
    posts = load_posts()
    post = {
        "id": len(posts) + 1,
        "username": username,
        "board": board,
        "message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "reply_to": reply_to,
    }
    posts.append(post)
    save_posts(posts)
    print(fmt_posted())


def format_timestamp(ts):
    dt = datetime.fromisoformat(ts)
    return dt.strftime("%Y-%m-%d %H:%M")


def print_threaded(posts_list):
    if not posts_list:
        print(fmt_info("No posts yet."))
        return

    top_level = []
    replies_map = {}
    for p in posts_list:
        rid = p.get("reply_to")
        if rid is None:
            top_level.append(p)
        else:
            replies_map.setdefault(rid, []).append(p)

    def print_thread(post, indent=0):
        ts = format_timestamp(post["timestamp"])
        board = post.get("board", "general")
        print(fmt_post_line(ts, board, post["id"], post["username"], post["message"], indent))
        for reply in replies_map.get(post["id"], []):
            print_thread(reply, indent + 1)

    for p in top_level:
        print_thread(p)


def read_posts(board=None):
    posts = load_posts()
    if board:
        posts = [p for p in posts if p.get("board", "general") == board]
        print_section_header(f"Board: {board}")
    else:
        print_welcome()
    print_threaded(posts)
    print()


def list_users():
    users = load_users()
    print_section_header("Users")
    if not users:
        print(fmt_info("No users yet."))
        return
    for u in sorted(users.keys()):
        print(fmt_user_line(u))
    print()


def list_boards():
    posts = load_posts()
    boards = sorted(set(p.get("board", "general") for p in posts))
    print_section_header("Boards")
    if not boards:
        print(fmt_info("No boards yet."))
        return
    for b in boards:
        count = sum(1 for p in posts if p.get("board", "general") == b)
        print(fmt_board_line(b, count))
    print()


def search_posts(keyword):
    posts = load_posts()
    keyword_lower = keyword.lower()
    results = [p for p in posts if keyword_lower in p["message"].lower()]
    print_section_header(f"Search: \"{keyword}\"")
    if not results:
        print(fmt_info("No posts found."))
        return
    for p in results:
        ts = format_timestamp(p["timestamp"])
        board = p.get("board", "general")
        print(fmt_search_line(ts, board, p["username"], p["message"]))
    print()


def show_profile(username):
    users = load_users()
    if username not in users:
        print(fmt_error(f"User '{username}' not found."))
        return
    user = users[username]
    posts = load_posts()
    post_count = sum(1 for p in posts if p["username"] == username)
    joined = format_timestamp(user["joined"])
    bio = user.get("bio", "")
    print_profile(username, joined, post_count, bio)


def set_bio(username, bio_text):
    get_or_create_user(username)
    users = load_users()
    users[username]["bio"] = bio_text
    save_users(users)
    print(fmt_info("Bio updated."))


def main():
    if len(sys.argv) < 2:
        print_usage("bbs.py")
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
        posts = load_posts()
        parent = next((p for p in posts if p["id"] == reply_to), None)
        if not parent:
            print(fmt_error(f"Post #{reply_to} not found."))
            sys.exit(1)
        post_message(sys.argv[3], parent.get("board", "general"), sys.argv[4], reply_to=reply_to)
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
    else:
        print_usage("bbs.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
