import sys
from datetime import datetime
from sqlalchemy import text
from db import engine, init_db


def get_or_create_user(conn, username):
    """Return the user ID for the given username, creating the user if needed."""
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username}
    ).fetchone()
    if row:
        return row[0]
    result = conn.execute(
        text("INSERT INTO users (username, joined) VALUES (:username, :joined)"),
        {"username": username, "joined": datetime.now().isoformat()}
    )
    return result.lastrowid


def post(username, message):
    with engine.begin() as conn:
        user_id = get_or_create_user(conn, username)
        conn.execute(
            text("INSERT INTO posts (user_id, message, timestamp) VALUES (:user_id, :message, :timestamp)"),
            {"user_id": user_id, "message": message, "timestamp": datetime.now().isoformat()}
        )
    print("Posted.")


def read():
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT u.username, p.message, p.timestamp "
            "FROM posts p JOIN users u ON p.user_id = u.id "
            "ORDER BY p.timestamp"
        )).fetchall()
    for username, message, timestamp in rows:
        dt = datetime.fromisoformat(timestamp)
        print(f"[{dt.strftime('%Y-%m-%d %H:%M')}] {username}: {message}")


def users():
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT username FROM users ORDER BY username"
        )).fetchall()
    for (username,) in rows:
        print(username)


def profile(username):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT username, bio, joined FROM users WHERE username = :username"),
            {"username": username}
        ).fetchone()
        if not row:
            print(f"User '{username}' not found.")
            return
        username, bio, joined = row
        count = conn.execute(
            text("SELECT COUNT(*) FROM posts WHERE user_id = (SELECT id FROM users WHERE username = :username)"),
            {"username": username}
        ).fetchone()[0]
    if joined:
        dt = datetime.fromisoformat(joined)
        joined_str = dt.strftime("%Y-%m-%d %H:%M")
    else:
        joined_str = "unknown"
    print(f"User:    {username}")
    print(f"Joined:  {joined_str}")
    print(f"Posts:   {count}")
    print(f"Bio:     {bio if bio else '(not set)'}")


def bio(username, text_content):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": username}
        ).fetchone()
        if not row:
            print(f"User '{username}' not found.")
            return
        conn.execute(
            text("UPDATE users SET bio = :bio WHERE username = :username"),
            {"bio": text_content, "username": username}
        )
    print(f"Bio updated for {username}.")


def search(keyword):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT u.username, p.message, p.timestamp "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                "WHERE p.message LIKE :keyword "
                "ORDER BY p.timestamp"
            ),
            {"keyword": f"%{keyword}%"}
        ).fetchall()
    for username, message, timestamp in rows:
        dt = datetime.fromisoformat(timestamp)
        print(f"[{dt.strftime('%Y-%m-%d %H:%M')}] {username}: {message}")


if __name__ == "__main__":
    init_db()

    if len(sys.argv) < 2:
        print("Usage: python bbs_db.py <command> [args]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "post" and len(sys.argv) >= 4:
        post(sys.argv[2], " ".join(sys.argv[3:]))
    elif command == "read":
        read()
    elif command == "users":
        users()
    elif command == "search" and len(sys.argv) >= 3:
        search(sys.argv[2])
    elif command == "profile" and len(sys.argv) >= 3:
        profile(sys.argv[2])
    elif command == "bio" and len(sys.argv) >= 4:
        bio(sys.argv[2], " ".join(sys.argv[3:]))
    else:
        print("Usage: python bbs_db.py <command> [args]")
        sys.exit(1)
