import sys
from datetime import datetime

from sqlalchemy import text
from db import engine, init_db

init_db()


def post(username, message):
    with engine.begin() as conn:
        conn.execute(
            text("INSERT OR IGNORE INTO users (username) VALUES (:username)"),
            {"username": username}
        )
        row = conn.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": username}
        ).fetchone()
        conn.execute(
            text("INSERT INTO posts (user_id, message, timestamp) VALUES (:user_id, :message, :timestamp)"),
            {"user_id": row[0], "message": message, "timestamp": datetime.now().isoformat()}
        )
    print("Posted.")


def read():
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT p.timestamp, u.username, p.message "
            "FROM posts p JOIN users u ON p.user_id = u.id "
            "ORDER BY p.id"
        )).fetchall()
    for r in rows:
        print(f"[{r[0]}] {r[1]}: {r[2]}")


def users():
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT DISTINCT username FROM users "
            "JOIN posts ON users.id = posts.user_id "
            "ORDER BY posts.id"
        )).fetchall()
    for r in rows:
        print(r[0])


def search(keyword):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT p.timestamp, u.username, p.message "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                "WHERE p.message LIKE :keyword "
                "ORDER BY p.id"
            ),
            {"keyword": f"%{keyword}%"}
        ).fetchall()
    for r in rows:
        print(f"[{r[0]}] {r[1]}: {r[2]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bbs_db.py <command> [args]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "post":
        if len(sys.argv) < 4:
            print("Usage: python bbs_db.py post <username> <message>")
            sys.exit(1)
        post(sys.argv[2], " ".join(sys.argv[3:]))
    elif command == "read":
        read()
    elif command == "users":
        users()
    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python bbs_db.py search <keyword>")
            sys.exit(1)
        search(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
