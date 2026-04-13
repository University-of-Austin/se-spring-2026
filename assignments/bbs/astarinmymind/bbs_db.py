"""
BBS (Bulletin Board System) - SQLite Database Version

A simple command-line bulletin board that stores posts in a SQLite database.
Uses SQLAlchemy with raw SQL queries (not ORM).
"""

import sys
from datetime import datetime

from sqlalchemy import text

from db import engine, init_db
from printer import print_post


def main():
    """Main entry point - initializes DB and routes to appropriate function."""
    # Ensure tables exist on every run
    init_db()

    # Check if a command was provided
    if len(sys.argv) < 2:
        print("Usage: python bbs_db.py <command> [arguments]")
        print("Commands:")
        print("  post <username> <message>  - Post a message")
        print("  read                       - Read all messages")
        print("  users                      - List all users")
        print("  search <keyword>           - Search posts by keyword")
        print("  flair <username> <emoji>   - Set user flair")
        sys.exit(1)

    command = sys.argv[1]

    if command == "post":
        # Requires username and message arguments
        if len(sys.argv) < 4:
            print("Usage: python bbs_db.py post <username> <message>")
            sys.exit(1)
        username = sys.argv[2]
        message = sys.argv[3]
        post_message(username, message)

    elif command == "read":
        read_messages()

    elif command == "users":
        list_users()

    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python bbs_db.py search <keyword>")
            sys.exit(1)
        keyword = sys.argv[2]
        search_messages(keyword)

    elif command == "flair":
        if len(sys.argv) < 4:
            print("Usage: python bbs_db.py flair <username> <emoji>")
            sys.exit(1)
        username = sys.argv[2]
        emoji = sys.argv[3]
        set_flair(username, emoji)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


def get_or_create_user(conn, username: str) -> int:
    """
    Look up a user by username. If they don't exist, create them.
    Returns the user's ID (primary key).
    """
    # First, try to find the user
    result = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username}
    )
    row = result.fetchone()

    if row:
        # User exists, return their ID
        return row[0]

    # User doesn't exist, insert them
    result = conn.execute(
        text("INSERT INTO users (username) VALUES (:username)"),
        {"username": username}
    )
    conn.commit()
    # Return the ID of the newly inserted row
    return result.lastrowid


def post_message(username: str, message: str):
    """Post a new message to the board and print it."""
    with engine.connect() as conn:
        # Step 1: Get the user's ID (creating them if needed)
        user_id = get_or_create_user(conn, username)

        # Step 2: Insert the post with current timestamp
        timestamp = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            text("""
                INSERT INTO posts (user_id, message, timestamp)
                VALUES (:user_id, :message, :timestamp)
            """),
            {"user_id": user_id, "message": message, "timestamp": timestamp}
        )
        conn.commit()

    print("Posted.")

    # Print to thermal printer (non-blocking, won't fail if printer unavailable)
    formatted_time = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M")
    print_post(username, message, formatted_time)


def set_flair(username: str, emoji: str):
    """Set a user's flair emoji."""
    with engine.connect() as conn:
        result = conn.execute(
            text("UPDATE users SET flair = :flair WHERE username = :username"),
            {"flair": emoji, "username": username}
        )
        conn.commit()

        if result.rowcount == 0:
            print(f"User '{username}' not found.")
        else:
            print(f"Flair set to {emoji} for {username}.")


def format_user(username: str, flair: str | None) -> str:
    """Format username with optional flair."""
    if flair:
        return f"{username} {flair}"
    return username


def read_messages():
    """Read and display all messages."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT u.username, u.flair, p.message, p.timestamp
            FROM posts p
            JOIN users u ON p.user_id = u.id
            ORDER BY p.id
        """))

        for row in result:
            username, flair, message, timestamp_str = row
            timestamp = datetime.fromisoformat(timestamp_str)
            formatted_time = timestamp.strftime("%Y-%m-%d %H:%M")
            display_name = format_user(username, flair)
            print(f"[{formatted_time}] {display_name}: {message}")


def list_users():
    """List all users who have posted, alphabetically."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT u.username, u.flair
            FROM users u
            JOIN posts p ON u.id = p.user_id
            GROUP BY u.id
            ORDER BY u.username
        """))

        for row in result:
            username, flair = row
            print(format_user(username, flair))


def search_messages(keyword: str):
    """Search posts containing a keyword. Database does the filtering."""
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT u.username, u.flair, p.message, p.timestamp
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.message LIKE :pattern
                ORDER BY p.id
            """),
            {"pattern": f"%{keyword}%"}
        )

        for row in result:
            username, flair, message, timestamp_str = row
            timestamp = datetime.fromisoformat(timestamp_str)
            formatted_time = timestamp.strftime("%Y-%m-%d %H:%M")
            display_name = format_user(username, flair)
            print(f"[{formatted_time}] {display_name}: {message}")


if __name__ == "__main__":
    main()
