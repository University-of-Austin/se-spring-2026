import json
import math
import os
import shutil
import sys
from datetime import datetime, timedelta

BBS_DATA_DIR = "bbs_data"
META_FILE = os.path.join(BBS_DATA_DIR, "meta.json")
BOARDS_DIR = os.path.join(BBS_DATA_DIR, "boards")
VOTES_FILE = os.path.join(BBS_DATA_DIR, "votes.json")
LEGACY_BBS_JSON = "bbs.json"
DEFAULT_BOARD = "general"
TRENDING_VIEW = "trending"
DAILY_VOTE_LIMIT = 5


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _board_file(board_name: str) -> str:
    return os.path.join(BOARDS_DIR, f"{board_name}.json")


def _write_board_file(board_name: str, posts: list):
    os.makedirs(BOARDS_DIR, exist_ok=True)
    with open(_board_file(board_name), "w", encoding="utf-8") as f:
        json.dump({"posts": posts}, f, indent=2, ensure_ascii=False)


def _write_meta_file(meta: dict):
    os.makedirs(BBS_DATA_DIR, exist_ok=True)
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def load_board(board_name: str) -> list:
    """Load posts from a board file, enriched with board name for display."""
    path = _board_file(board_name)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    posts = data.get("posts", [])
    for post in posts:
        post["board"] = board_name
    return posts


def save_board(board_name: str, posts: list):
    """Save posts to a board file (strips the transient board field)."""
    clean = [{k: v for k, v in p.items() if k != "board"} for p in posts]
    _write_board_file(board_name, clean)


def list_board_names() -> list:
    if not os.path.exists(BOARDS_DIR):
        return []
    return sorted(f[:-5] for f in os.listdir(BOARDS_DIR) if f.endswith(".json"))


def load_meta() -> dict:
    if not os.path.exists(META_FILE):
        return {"users": []}
    with open(META_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_meta(meta: dict):
    _write_meta_file(meta)


def load_votes() -> dict:
    if not os.path.exists(VOTES_FILE):
        return {}
    with open(VOTES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_votes(votes: dict):
    os.makedirs(BBS_DATA_DIR, exist_ok=True)
    with open(VOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(votes, f, indent=2, ensure_ascii=False)


def check_and_record_vote(username: str, board: str, post_id: int, vote_type: str):
    """Enforces one-vote-per-post and daily limit. Returns an error string or None."""
    today = datetime.now().date().isoformat()
    votes = load_votes()
    user_votes = votes.get(username, [])

    for v in user_votes:
        if v["board"] == board and v["post_id"] == post_id:
            return "Error: you have already voted on this post."

    today_count = sum(1 for v in user_votes if v["date"] == today)
    if today_count >= DAILY_VOTE_LIMIT:
        return f"Error: {username} has reached the daily vote limit ({DAILY_VOTE_LIMIT}/day)."

    user_votes.append({"board": board, "post_id": post_id, "type": vote_type, "date": today})
    votes[username] = user_votes
    save_votes(votes)
    return None


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def find_user(meta: dict, username: str):
    for user in meta["users"]:
        if user.get("username") == username:
            return user
    return None


def get_or_create_user(meta: dict, username: str) -> dict:
    user = find_user(meta, username)
    if user:
        return user
    user = {
        "username": username,
        "join_date": now_timestamp(),
        "post_count": 0,
        "bio": "",
    }
    meta["users"].append(user)
    return user


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------

def now_timestamp() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def ensure_board_allowed(board: str):
    if board and board.lower() == TRENDING_VIEW:
        print(f"Error: '{TRENDING_VIEW}' is a reserved trending view and cannot be used as a board.")
        sys.exit(1)


def next_post_id(posts: list) -> int:
    if not posts:
        return 1
    return max(p.get("id", 0) for p in posts) + 1


def format_post(post: dict, indent: int = 0) -> str:
    timestamp = datetime.fromisoformat(post["timestamp"]).strftime("%Y-%m-%d %H:%M")
    board = post.get("board", DEFAULT_BOARD)
    post_id = post.get("id")
    upvotes = post.get("upvotes", 0)
    downvotes = post.get("downvotes", 0)
    votes_text = f" ({upvotes}↑/{downvotes}↓)"
    prefix = "  " * indent
    line = f"{prefix}[{post_id}] [{board}] {post['username']}: {post['message']}{votes_text}"
    width = shutil.get_terminal_size(fallback=(100, 20)).columns
    if width > len(line) + len(timestamp) + 1:
        spacer = " " * (width - len(line) - len(timestamp))
        return f"{line}{spacer}{timestamp}"
    return f"{line} {timestamp}"


def build_thread_map(posts: list) -> tuple:
    posts_by_id = {p["id"]: p for p in posts}
    children: dict = {p["id"]: [] for p in posts}
    roots = []
    for post in posts:
        parent_id = post.get("parent_id")
        if parent_id and parent_id in posts_by_id:
            children[parent_id].append(post)
        else:
            roots.append(post)
    for child_list in children.values():
        child_list.sort(key=lambda p: p["timestamp"])
    roots.sort(key=lambda p: p["timestamp"])
    return roots, children


def print_thread(post: dict, children: dict, indent: int = 0):
    print(format_post(post, indent))
    for child in children.get(post["id"], []):
        print_thread(child, children, indent + 1)


def count_descendants(post_id: int, children: dict) -> int:
    total = 0
    for child in children.get(post_id, []):
        total += 1 + count_descendants(child["id"], children)
    return total


def _score_board_roots(posts: list) -> tuple[list, dict]:
    """Return (scored_roots, children) for a single board's posts.

    scored_roots is a list of (score, root_post) sorted descending.
    children is the board-local thread map needed to print the threads.
    """
    cutoff = datetime.now() - timedelta(days=7)
    roots, children = build_thread_map(posts)
    scored = []
    for root in roots:
        if datetime.fromisoformat(root["timestamp"]) < cutoff:
            continue
        reply_count = count_descendants(root["id"], children)
        score = root.get("upvotes", 0) - root.get("downvotes", 0) + reply_count * 5
        scored.append((score, root))
    scored.sort(key=lambda x: (-x[0], x[1]["timestamp"]))
    return scored, children


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def command_post(args):
    if len(args) < 1:
        print("Usage: python bbs.py post <username> [--board <board>] <message>")
        sys.exit(1)
    username = args[0]
    board = DEFAULT_BOARD
    message = None

    if len(args) >= 3 and args[1] in ("--board", "-b"):
        board = args[2]
        message = " ".join(args[3:]) if len(args) > 3 else input("Message: ").strip()
    elif len(args) == 2:
        message = args[1]
    elif len(args) == 1:
        message = input("Message: ").strip()
    else:
        board = args[1]
        message = " ".join(args[2:])

    ensure_board_allowed(board)
    if not message:
        print("Error: message cannot be empty.")
        sys.exit(1)

    posts = load_board(board)
    posts.append({
        "id": next_post_id(posts),
        "username": username,
        "message": message,
        "timestamp": now_timestamp(),
        "parent_id": None,
        "upvotes": 0,
        "downvotes": 0,
    })
    save_board(board, posts)

    meta = load_meta()
    user = get_or_create_user(meta, username)
    user["post_count"] += 1
    save_meta(meta)
    print("Posted.")


def command_reply(args):
    if len(args) < 2:
        print("Usage: python bbs.py reply <username> [--board <board>] <message_id> <message>")
        sys.exit(1)
    username = args[0]
    board = DEFAULT_BOARD
    parent_index = 1

    if len(args) >= 4 and args[1] in ("--board", "-b"):
        board = args[2]
        parent_index = 3

    if board.lower() == TRENDING_VIEW:
        print(f"Error: '{TRENDING_VIEW}' is a reserved trending view and cannot be replied to.")
        sys.exit(1)

    if len(args) > parent_index:
        try:
            parent_id = int(args[parent_index])
        except ValueError:
            print("Error: message_id must be a number.")
            sys.exit(1)
    else:
        print("Usage: python bbs.py reply <username> [--board <board>] <message_id> <message>")
        sys.exit(1)

    message = " ".join(args[parent_index + 1:]) if len(args) > parent_index + 1 else input("Message: ").strip()
    if not message:
        print("Error: message cannot be empty.")
        sys.exit(1)

    posts = load_board(board)
    parent = next((p for p in posts if p.get("id") == parent_id), None)
    if not parent:
        print(f"Error: message {parent_id} not found in board {board}.")
        sys.exit(1)

    posts.append({
        "id": next_post_id(posts),
        "username": username,
        "message": message,
        "timestamp": now_timestamp(),
        "parent_id": parent_id,
        "upvotes": 0,
        "downvotes": 0,
    })
    save_board(board, posts)

    meta = load_meta()
    user = get_or_create_user(meta, username)
    user["post_count"] += 1
    save_meta(meta)
    print("Replied.")


def command_read(args):
    if len(args) > 1:
        print("Usage: python bbs.py read [board]")
        sys.exit(1)
    board = args[0] if args else None
    if board and board.lower() == TRENDING_VIEW:
        command_trending([])
        return
    if board:
        posts = load_board(board)
        posts.sort(key=lambda p: p["timestamp"])
        roots, children = build_thread_map(posts)
        for root in roots:
            print_thread(root, children)
    else:
        for board_name in list_board_names():
            posts = load_board(board_name)
            posts.sort(key=lambda p: p["timestamp"])
            roots, children = build_thread_map(posts)
            if roots:
                print(f"--- {board_name} ---")
                for root in roots:
                    print_thread(root, children)


def command_users():
    meta = load_meta()
    all_usernames = {u["username"] for u in meta["users"]}
    for board_name in list_board_names():
        for post in load_board(board_name):
            all_usernames.add(post["username"])
    for username in sorted(all_usernames):
        print(username)


def command_boards():
    board_names = list_board_names()
    if not board_names:
        print("No boards yet.")
        return
    for board_name in board_names:
        posts = load_board(board_name)
        print(f"{board_name} ({len(posts)} posts)")


def command_search(args):
    if len(args) == 0:
        print("Usage: python bbs.py search <keyword> [board]")
        sys.exit(1)
    if len(args) > 2:
        print("Usage: python bbs.py search <keyword> [board]")
        sys.exit(1)
    keyword = args[0].lower()
    board = args[1] if len(args) == 2 else None
    if board:
        ensure_board_allowed(board)
    boards_to_search = [board] if board else list_board_names()
    results = []
    for board_name in boards_to_search:
        for post in load_board(board_name):
            if keyword in post["message"].lower():
                results.append(post)
    results.sort(key=lambda p: p["timestamp"])
    for post in results:
        print(format_post(post))


def command_upvote(args):
    if len(args) != 3:
        print("Usage: python bbs.py upvote <username> <board> <message_id>")
        sys.exit(1)
    username, board = args[0], args[1]
    if board.lower() == TRENDING_VIEW:
        print(f"Error: '{TRENDING_VIEW}' is a computed view and cannot be voted on directly.")
        sys.exit(1)
    try:
        post_id = int(args[2])
    except ValueError:
        print("Error: message_id must be a number.")
        sys.exit(1)
    posts = load_board(board)
    post = next((p for p in posts if p.get("id") == post_id), None)
    if not post:
        print(f"Error: message {post_id} not found in board {board}.")
        sys.exit(1)
    error = check_and_record_vote(username, board, post_id, "up")
    if error:
        print(error)
        sys.exit(1)
    post["upvotes"] += 1
    save_board(board, posts)
    print("Upvoted.")


def command_downvote(args):
    if len(args) != 3:
        print("Usage: python bbs.py downvote <username> <board> <message_id>")
        sys.exit(1)
    username, board = args[0], args[1]
    if board.lower() == TRENDING_VIEW:
        print(f"Error: '{TRENDING_VIEW}' is a computed view and cannot be voted on directly.")
        sys.exit(1)
    try:
        post_id = int(args[2])
    except ValueError:
        print("Error: message_id must be a number.")
        sys.exit(1)
    posts = load_board(board)
    post = next((p for p in posts if p.get("id") == post_id), None)
    if not post:
        print(f"Error: message {post_id} not found in board {board}.")
        sys.exit(1)
    error = check_and_record_vote(username, board, post_id, "down")
    if error:
        print(error)
        sys.exit(1)
    post["downvotes"] += 1
    save_board(board, posts)
    print("Downvoted.")


def command_trending(args):
    if len(args) > 1:
        print("Usage: python bbs.py trending [board]")
        sys.exit(1)
    board = args[0] if args else None
    if board and board.lower() == TRENDING_VIEW:
        print(f"Error: '{TRENDING_VIEW}' is not a real board. Use python bbs.py trending instead.")
        sys.exit(1)

    if board:
        # Single-board trending: compute and display within that board's thread map
        posts = load_board(board)
        scored, children = _score_board_roots(posts)
        top_count = max(1, math.ceil(len(scored) * 0.05))
        trending_top = scored[:top_count]
        if not trending_top:
            print("No trending posts found for the last week.")
            return
        print("Trending posts:")
        for score, root in trending_top:
            print(f"Score: {score}")
            print_thread(root, children)
    else:
        # Cross-board trending: collect all root candidates, score globally,
        # keep per-board children maps so threads print correctly
        all_candidates = []
        for board_name in list_board_names():
            posts = load_board(board_name)
            roots, children = build_thread_map(posts)
            cutoff = datetime.now() - timedelta(days=7)
            for root in roots:
                if datetime.fromisoformat(root["timestamp"]) < cutoff:
                    continue
                reply_count = count_descendants(root["id"], children)
                score = root.get("upvotes", 0) - root.get("downvotes", 0) + reply_count * 5
                all_candidates.append((score, root, children))
        all_candidates.sort(key=lambda x: (-x[0], x[1]["timestamp"]))
        top_count = max(1, math.ceil(len(all_candidates) * 0.05))
        trending_top = all_candidates[:top_count]
        if not trending_top:
            print("No trending posts found for the last week.")
            return
        print("Trending posts:")
        for score, root, children in trending_top:
            print(f"Score: {score}")
            print_thread(root, children)


def command_profile(args):
    if len(args) < 2:
        print("Usage: python bbs.py profile <show|setbio> <username> [bio]")
        sys.exit(1)
    action = args[0].lower()
    username = args[1]
    meta = load_meta()

    if action == "show":
        user = find_user(meta, username)
        if not user:
            print(f"User {username} not found.")
            sys.exit(1)
        print(f"Username: {user['username']}")
        print(f"Join date: {user['join_date']}")
        print(f"Post count: {user['post_count']}")
        print(f"Bio: {user['bio']}")
        return

    if action == "setbio":
        if len(args) < 3:
            print("Usage: python bbs.py profile setbio <username> <bio>")
            sys.exit(1)
        bio = " ".join(args[2:])
        user = get_or_create_user(meta, username)
        user["bio"] = bio
        save_meta(meta)
        print("Bio updated.")
        return

    print("Usage: python bbs.py profile <show|setbio> <username> [bio]")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def print_usage():
    print("Usage: python bbs.py <post|reply|read|users|boards|search|profile|upvote|downvote|trending> [...]")


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()
    args = sys.argv[2:]

    if command == "post":
        command_post(args)
    elif command == "reply":
        command_reply(args)
    elif command == "read":
        command_read(args)
    elif command == "users":
        command_users()
    elif command == "boards":
        command_boards()
    elif command == "search":
        command_search(args)
    elif command == "profile":
        command_profile(args)
    elif command == "upvote":
        command_upvote(args)
    elif command == "downvote":
        command_downvote(args)
    elif command == "trending":
        command_trending(args)
    else:
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
