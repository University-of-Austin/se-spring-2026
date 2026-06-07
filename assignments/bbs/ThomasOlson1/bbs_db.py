import math
import shutil
import sys
from datetime import datetime, timedelta
from sqlalchemy import text
from db import engine, init_db

DEFAULT_BOARD = "general"
TRENDING_VIEW = "trending"
DAILY_VOTE_LIMIT = 5


def format_post(row, indent=0):
    board = row.get("board", DEFAULT_BOARD)
    board_post_id = row.get("board_post_id", row.get("id"))
    upvotes = row.get("upvotes", 0)
    downvotes = row.get("downvotes", 0)
    timestamp = row["timestamp"][:16].replace('T', ' ')
    prefix = "  " * indent
    votes_text = f" ({upvotes}↑/{downvotes}↓)"
    line = f"{prefix}[{board_post_id}] [{board}] {row['username']}: {row['message']}{votes_text}"
    width = shutil.get_terminal_size(fallback=(100, 20)).columns
    if width > len(line) + len(timestamp) + 1:
        spacer = " " * (width - len(line) - len(timestamp))
        return f"{line}{spacer}{timestamp}"
    return f"{line} {timestamp}"


def count_descendants(post_id, children):
    total = 0
    for child in children.get(post_id, []):
        total += 1 + count_descendants(child["id"], children)
    return total


def now_timestamp():
    return datetime.now().replace(microsecond=0).isoformat()


def get_user_id(conn, username):
    conn.execute(text("PRAGMA foreign_keys = ON"))
    conn.execute(
        text(
            "INSERT OR IGNORE INTO users (username, join_date, post_count, bio) "
            "VALUES (:username, :join_date, 0, '')"
        ),
        {"username": username, "join_date": now_timestamp()},
    )
    result = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    )
    return result.scalar_one()


def get_next_board_post_id(conn, board_id):
    return conn.execute(
        text("SELECT COALESCE(MAX(board_post_id), 0) + 1 FROM posts WHERE board_id = :board_id"),
        {"board_id": board_id},
    ).scalar_one()


def increment_post_count(conn, user_id):
    conn.execute(
        text("UPDATE users SET post_count = post_count + 1 WHERE id = :user_id"),
        {"user_id": user_id},
    )


def get_board_id(conn, board):
    conn.execute(text("PRAGMA foreign_keys = ON"))
    conn.execute(
        text("INSERT OR IGNORE INTO boards (name) VALUES (:board)"),
        {"board": board},
    )
    result = conn.execute(
        text("SELECT id FROM boards WHERE name = :board"),
        {"board": board},
    )
    return result.scalar_one()


def _cast_vote(conn, username: str, board: str, board_post_id: int, vote_type: str):
    """Validates and records a vote inside an open transaction. Exits on any error."""
    user_id = get_user_id(conn, username)

    board_row = conn.execute(
        text("SELECT id FROM boards WHERE name = :board"),
        {"board": board},
    ).mappings().first()
    if not board_row:
        print(f"Error: board '{board}' not found.")
        sys.exit(1)

    post = conn.execute(
        text("SELECT id FROM posts WHERE board_id = :bid AND board_post_id = :bpid"),
        {"bid": board_row["id"], "bpid": board_post_id},
    ).mappings().first()
    if not post:
        print(f"Error: message {board_post_id} not found in board {board}.")
        sys.exit(1)
    post_id = post["id"]

    existing = conn.execute(
        text("SELECT id FROM votes WHERE user_id = :uid AND post_id = :pid"),
        {"uid": user_id, "pid": post_id},
    ).first()
    if existing:
        print("Error: you have already voted on this post.")
        sys.exit(1)

    today = datetime.now().date().isoformat()
    count = conn.execute(
        text("SELECT COUNT(*) FROM votes WHERE user_id = :uid AND date = :date"),
        {"uid": user_id, "date": today},
    ).scalar_one()
    if count >= DAILY_VOTE_LIMIT:
        print(f"Error: {username} has reached the daily vote limit ({DAILY_VOTE_LIMIT}/day).")
        sys.exit(1)

    conn.execute(
        text("INSERT INTO votes (user_id, post_id, vote_type, date) VALUES (:uid, :pid, :vtype, :date)"),
        {"uid": user_id, "pid": post_id, "vtype": vote_type, "date": today},
    )
    if vote_type == "up":
        conn.execute(text("UPDATE posts SET upvotes = upvotes + 1 WHERE id = :pid"), {"pid": post_id})
    else:
        conn.execute(text("UPDATE posts SET downvotes = downvotes + 1 WHERE id = :pid"), {"pid": post_id})


def ensure_board_allowed(board):
    if board and board.lower() == TRENDING_VIEW:
        print(f"Error: '{TRENDING_VIEW}' is a reserved trending view and cannot be used as a board.")
        sys.exit(1)


def build_thread_map(posts):
    posts_by_id = {post["id"]: post for post in posts}
    children = {post["id"]: [] for post in posts}
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


def print_thread(post, children, indent=0):
    print(format_post(post, indent))
    for child in children.get(post["id"], []):
        print_thread(child, children, indent + 1)


def command_post(args):
    if len(args) < 1:
        print("Usage: python bbs_db.py post <username> [--board <board>] <message>")
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

    if board.lower() == TRENDING_VIEW:
        print(f"Error: '{TRENDING_VIEW}' is a reserved trending view and cannot be posted to.")
        sys.exit(1)

    if not message:
        print("Error: message cannot be empty.")
        sys.exit(1)

    timestamp = now_timestamp()
    init_db()

    with engine.begin() as conn:
        user_id = get_user_id(conn, username)
        board_id = get_board_id(conn, board)
        board_post_id = get_next_board_post_id(conn, board_id)
        conn.execute(
            text(
                "INSERT INTO posts (user_id, board_id, board_post_id, message, timestamp, parent_id) "
                "VALUES (:user_id, :board_id, :board_post_id, :message, :timestamp, NULL)"
            ),
            {
                "user_id": user_id,
                "board_id": board_id,
                "board_post_id": board_post_id,
                "message": message,
                "timestamp": timestamp,
            },
        )
        increment_post_count(conn, user_id)
    print("Posted.")


def command_reply(args):
    if len(args) < 2:
        print("Usage: python bbs_db.py reply <username> [--board <board>] <message_id> <message>")
        sys.exit(1)
    username = args[0]
    board = DEFAULT_BOARD
    message = None
    parent_index = 1

    if len(args) >= 4 and args[1] in ("--board", "-b"):
        board = args[2]
        parent_index = 3
    else:
        parent_index = 1

    if board.lower() == TRENDING_VIEW:
        print(f"Error: '{TRENDING_VIEW}' is a reserved trending view and cannot be replied to.")
        sys.exit(1)

    if len(args) > parent_index:
        try:
            parent_board_id = int(args[parent_index])
        except ValueError:
            print("Error: message_id must be a number.")
            sys.exit(1)
    else:
        print("Usage: python bbs_db.py reply <username> [--board <board>] <message_id> <message>")
        sys.exit(1)

    if len(args) > parent_index + 1:
        message = " ".join(args[parent_index + 1:])
    else:
        message = input("Message: ").strip()

    if not message:
        print("Error: message cannot be empty.")
        sys.exit(1)

    init_db()
    with engine.begin() as conn:
        board_id = get_board_id(conn, board)
        parent = conn.execute(
            text(
                "SELECT p.id FROM posts p WHERE p.board_id = :board_id AND p.board_post_id = :board_post_id"
            ),
            {"board_id": board_id, "board_post_id": parent_board_id},
        ).mappings().first()
        if not parent:
            print(f"Error: message {parent_board_id} not found in board {board}.")
            sys.exit(1)
        parent_id = parent["id"]
        user_id = get_user_id(conn, username)
        board_post_id = get_next_board_post_id(conn, board_id)
        conn.execute(
            text(
                "INSERT INTO posts (user_id, board_id, board_post_id, message, timestamp, parent_id) "
                "VALUES (:user_id, :board_id, :board_post_id, :message, :timestamp, :parent_id)"
            ),
            {
                "user_id": user_id,
                "board_id": board_id,
                "board_post_id": board_post_id,
                "message": message,
                "timestamp": now_timestamp(),
                "parent_id": parent_id,
            },
        )
        increment_post_count(conn, user_id)
    print("Replied.")


def command_read(args):
    if len(args) > 1:
        print("Usage: python bbs_db.py read [board]")
        sys.exit(1)
    board = args[0] if args else None
    if board and board.lower() == TRENDING_VIEW:
        command_trending([])
        return
    init_db()
    with engine.connect() as conn:
        sql = (
            "SELECT p.id, p.parent_id, p.board_post_id, parent.board_post_id AS parent_board_post_id, u.username, p.message, p.timestamp, b.name AS board, p.upvotes, p.downvotes "
            "FROM posts p "
            "LEFT JOIN posts parent ON p.parent_id = parent.id "
            "JOIN users u ON p.user_id = u.id "
            "JOIN boards b ON p.board_id = b.id "
        )
        params = {}
        if board:
            sql += "WHERE b.name = :board "
            params["board"] = board
            sql += "ORDER BY p.timestamp"
        else:
            sql += "ORDER BY b.name, p.timestamp"
        rows = conn.execute(text(sql), params).mappings().all()
    roots, children = build_thread_map(rows)
    if not board:
        roots.sort(key=lambda p: (p.get("board", DEFAULT_BOARD), p["timestamp"]))
    if board:
        for root in roots:
            print_thread(root, children)
    else:
        current_board = None
        for root in roots:
            board_name = root.get("board", DEFAULT_BOARD)
            if board_name != current_board:
                current_board = board_name
                print(f"--- {board_name} ---")
            print_thread(root, children)


def command_users():
    init_db()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT username FROM users ORDER BY username")
        ).scalars().all()
    for username in rows:
        print(username)


def command_boards():
    init_db()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT b.name, COUNT(p.id) AS post_count "
                "FROM boards b "
                "LEFT JOIN posts p ON p.board_id = b.id "
                "GROUP BY b.name "
                "ORDER BY b.name"
            )
        ).mappings().all()
    for row in rows:
        print(f"{row['name']} ({row['post_count']} posts)")


def command_search(args):
    if len(args) == 0 or len(args) > 2:
        print("Usage: python bbs_db.py search <keyword> [board]")
        sys.exit(1)
    keyword = f"%{args[0]}%"
    board = args[1] if len(args) == 2 else None
    if board and board.lower() == TRENDING_VIEW:
        print(f"Error: '{TRENDING_VIEW}' is not a real board. Use python bbs_db.py trending instead.")
        sys.exit(1)
    init_db()
    with engine.connect() as conn:
        sql = (
            "SELECT p.id, p.parent_id, p.board_post_id, u.username, p.message, p.timestamp, b.name AS board, p.upvotes, p.downvotes "
            "FROM posts p "
            "JOIN users u ON p.user_id = u.id "
            "JOIN boards b ON p.board_id = b.id "
            "WHERE p.message LIKE :keyword "
        )
        params = {"keyword": keyword}
        if board:
            sql += "AND b.name = :board "
            params["board"] = board
        sql += "ORDER BY p.timestamp"
        rows = conn.execute(text(sql), params).mappings().all()
    for row in rows:
        print(format_post(row))


def command_upvote(args):
    if len(args) != 3:
        print("Usage: python bbs_db.py upvote <username> <board> <message_id>")
        sys.exit(1)
    username, board = args[0], args[1]
    if board.lower() == TRENDING_VIEW:
        print(f"Error: '{TRENDING_VIEW}' is a computed view and cannot be voted on directly.")
        sys.exit(1)
    try:
        board_post_id = int(args[2])
    except ValueError:
        print("Error: message_id must be a number.")
        sys.exit(1)
    init_db()
    with engine.begin() as conn:
        _cast_vote(conn, username, board, board_post_id, "up")
    print("Upvoted.")


def command_downvote(args):
    if len(args) != 3:
        print("Usage: python bbs_db.py downvote <username> <board> <message_id>")
        sys.exit(1)
    username, board = args[0], args[1]
    if board.lower() == TRENDING_VIEW:
        print(f"Error: '{TRENDING_VIEW}' is a computed view and cannot be voted on directly.")
        sys.exit(1)
    try:
        board_post_id = int(args[2])
    except ValueError:
        print("Error: message_id must be a number.")
        sys.exit(1)
    init_db()
    with engine.begin() as conn:
        _cast_vote(conn, username, board, board_post_id, "down")
    print("Downvoted.")


def command_trending(args):
    if len(args) > 1:
        print("Usage: python bbs_db.py trending [board]")
        sys.exit(1)
    board = args[0] if args else None
    if board and board.lower() == TRENDING_VIEW:
        print(f"Error: '{TRENDING_VIEW}' is not a real board. Use python bbs_db.py trending instead.")
        sys.exit(1)

    # Push the time filter to SQL so we only load the posts that can actually
    # be trending candidates (and their replies, which must be newer than the
    # root anyway). This avoids pulling the entire post history into Python.
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    init_db()
    with engine.connect() as conn:
        sql = (
            "SELECT p.id, p.parent_id, p.board_post_id, u.username, p.message, p.timestamp, b.name AS board, p.upvotes, p.downvotes "
            "FROM posts p "
            "JOIN users u ON p.user_id = u.id "
            "JOIN boards b ON p.board_id = b.id "
            "WHERE p.timestamp >= :cutoff "
        )
        params: dict = {"cutoff": cutoff}
        if board:
            sql += "AND b.name = :board "
            params["board"] = board
        sql += "ORDER BY p.timestamp"
        rows = conn.execute(text(sql), params).mappings().all()

    roots, children = build_thread_map(rows)
    if not roots:
        print("No trending posts found for the last week.")
        return
    scored = []
    for root in roots:
        reply_count = count_descendants(root["id"], children)
        score = root.get("upvotes", 0) - root.get("downvotes", 0) + reply_count * 5
        scored.append((score, root))
    scored.sort(key=lambda x: (-x[0], x[1]["timestamp"]))
    top_count = max(1, math.ceil(len(scored) * 0.05))
    print("Trending posts:")
    for score, root in scored[:top_count]:
        print(f"Score: {score}")
        print_thread(root, children)


def command_profile(args):
    if len(args) < 2:
        print("Usage: python bbs_db.py profile <show|setbio> <username> [bio]")
        sys.exit(1)
    action = args[0].lower()
    username = args[1]
    init_db()

    if action == "show":
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT username, join_date, post_count, bio "
                    "FROM users WHERE username = :username"
                ),
                {"username": username},
            ).mappings().first()
        if not row:
            print(f"User {username} not found.")
            sys.exit(1)
        print(f"Username: {row['username']}")
        print(f"Join date: {row['join_date']}")
        print(f"Post count: {row['post_count']}")
        print(f"Bio: {row['bio']}")
        return

    if action == "setbio":
        if len(args) < 3:
            print("Usage: python bbs_db.py profile setbio <username> <bio>")
            sys.exit(1)
        bio = " ".join(args[2:])
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT OR IGNORE INTO users (username, join_date, post_count, bio) "
                    "VALUES (:username, :join_date, 0, '')"
                ),
                {"username": username, "join_date": now_timestamp()},
            )
            conn.execute(
                text("UPDATE users SET bio = :bio WHERE username = :username"),
                {"bio": bio, "username": username},
            )
        print("Bio updated.")
        return

    print("Usage: python bbs_db.py profile <show|setbio> <username> [bio]")
    sys.exit(1)


def print_usage():
    print("Usage: python bbs_db.py <post|reply|read|users|boards|search|profile|upvote|downvote|trending> [...]")


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
