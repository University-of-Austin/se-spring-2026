"""
BBS (Bulletin Board System) - JSON File Storage Version

A simple command-line bulletin board that stores posts in a JSON file.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# The file where all posts are stored
DATA_FILE = Path("bbs.json")


def load_posts() -> list[dict]:
    """
    Load all posts from the JSON file.
    Returns an empty list if the file doesn't exist yet.
    """
    if not DATA_FILE.exists():
        return []

    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_posts(posts: list[dict]) -> None:
    """
    Save all posts to the JSON file.
    Uses indent=2 for human-readable formatting.
    """
    with open(DATA_FILE, "w") as f:
        json.dump(posts, f, indent=2)


def main():
    """Main entry point - parses command and routes to appropriate function."""
    # Check if a command was provided
    if len(sys.argv) < 2:
        print("Usage: python bbs.py <command> [arguments]")
        print("Commands:")
        print("  post <username> <message>  - Post a message")
        print("  read                       - Read all messages")
        print("  users                      - List all users")
        print("  search <keyword>           - Search posts by keyword")
        sys.exit(1)

    command = sys.argv[1]

    if command == "post":
        # Requires username and message
        if len(sys.argv) < 4:
            print("Usage: python bbs.py post <username> <message>")
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
            print("Usage: python bbs.py search <keyword>")
            sys.exit(1)
        keyword = sys.argv[2]
        search_messages(keyword)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


def post_message(username: str, message: str):
    """Post a new message to the board."""
    # Load existing posts (or empty list if none)
    posts = load_posts()

    # Create the new post with current timestamp
    new_post = {
        "username": username,
        "message": message,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    # Append and save
    posts.append(new_post)
    save_posts(posts)

    print("Posted.")


def read_messages():
    """Read and display all messages."""
    posts = load_posts()

    for post in posts:
        # Parse the ISO timestamp and format it for display
        timestamp = datetime.fromisoformat(post["timestamp"])
        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M")

        print(f"[{formatted_time}] {post['username']}: {post['message']}")


def list_users():
    """List all users who have posted."""
    posts = load_posts()

    # Use a set to get unique usernames, preserving first-seen order
    seen = set()
    for post in posts:
        username = post["username"]
        if username not in seen:
            seen.add(username)
            print(username)


def search_messages(keyword: str):
    """Search posts by keyword (case-insensitive)."""
    posts = load_posts()
    keyword_lower = keyword.lower()

    for post in posts:
        # Check if keyword appears in the message (case-insensitive)
        if keyword_lower in post["message"].lower():
            timestamp = datetime.fromisoformat(post["timestamp"])
            formatted_time = timestamp.strftime("%Y-%m-%d %H:%M")
            print(f"[{formatted_time}] {post['username']}: {post['message']}")


if __name__ == "__main__":
    main()
