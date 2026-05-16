import sys
import textwrap
from datetime import datetime
from sqlalchemy import text
from rich.console import Console
from db import engine, init_db

console = Console()

LLAMA_BANNER = r"""
    '
 ~)
     (_ --- ;
     /| ~ |\
    /  /  /|
"""

LLAMA_BODY = r"""       o
      o
       ~)
        (_---;
         /|~|\
        / / / |"""


def show_banner():
    console.print(LLAMA_BANNER, style="bold magenta", end="")
    console.print("  LLAMAGRAM", style="bold magenta")
    console.print()


def make_llama_post(post_id, username, message, ts, indent=""):
    bubble_width = max(len(message), len(username) + 10, 20)
    bubble_width = min(bubble_width, 50)
    lines = textwrap.wrap(message, width=bubble_width)
    box_width = max(len(line) for line in lines)
    # Build the bubble
    bubble = []
    bubble.append(f" {'_' * (box_width + 2)}")
    if len(lines) == 1:
        bubble.append(f"( {lines[0]:<{box_width}} )")
    else:
        bubble.append(f"/ {lines[0]:<{box_width}} \\")
        for line in lines[1:-1]:
            bubble.append(f"| {line:<{box_width}} |")
        bubble.append(f"\\ {lines[-1]:<{box_width}} /")
    bubble.append(f" {'-' * (box_width + 2)}")
    # Print bubble
    for bline in bubble:
        console.print(f"{indent}[white]{bline}[/white]")
    # Print llama body
    for lline in LLAMA_BODY.strip().split("\n"):
        escaped = lline.replace("\\", "\\\\")
        console.print(f"{indent}[bold magenta]{escaped}[/bold magenta]")
    # Print metadata underneath
    console.print(
        f"{indent}  [bold blue]\\[{post_id}][/bold blue] "
        f"[bold yellow]{username}[/bold yellow] "
        f"[dim]{ts}[/dim]"
    )


def post_message(username, message):
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": username},
        ).fetchone()

        if existing:
            user_id = existing[0]
        else:
            result = conn.execute(
                text("INSERT INTO users (username) VALUES (:username)"),
                {"username": username},
            )
            user_id = result.lastrowid

        conn.execute(
            text("INSERT INTO posts (user_id, message, timestamp) VALUES (:user_id, :message, :timestamp)"),
            {
                "user_id": user_id,
                "message": message,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )
        conn.commit()
    console.print("[bold green]Posted to Llamagram![/bold green]")


def reply_message(username, post_id, message):
    with engine.connect() as conn:
        parent = conn.execute(
            text("SELECT id FROM posts WHERE id = :post_id"),
            {"post_id": post_id},
        ).fetchone()

        if not parent:
            console.print(f"[bold red]Post {post_id} not found.[/bold red]")
            sys.exit(1)

        existing = conn.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": username},
        ).fetchone()

        if existing:
            user_id = existing[0]
        else:
            result = conn.execute(
                text("INSERT INTO users (username) VALUES (:username)"),
                {"username": username},
            )
            user_id = result.lastrowid

        conn.execute(
            text("INSERT INTO posts (user_id, message, timestamp, parent_id) VALUES (:user_id, :message, :timestamp, :parent_id)"),
            {
                "user_id": user_id,
                "message": message,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "parent_id": post_id,
            },
        )
        conn.commit()
    console.print("[bold green]Reply sent![/bold green]")


def read_posts():
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT p.id, u.username, p.message, p.timestamp, p.parent_id "
            "FROM posts p JOIN users u ON p.user_id = u.id "
            "ORDER BY p.timestamp"
        )).fetchall()

    if not rows:
        console.print("[dim]No posts yet.[/dim]")
        return

    top_level = []
    replies = {}
    for row in rows:
        post_id, username, message, timestamp, parent_id = row
        if parent_id is None:
            top_level.append(row)
        else:
            replies.setdefault(parent_id, []).append(row)

    for i, row in enumerate(top_level):
        post_id, username, message, timestamp, _ = row
        ts = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M")
        make_llama_post(post_id, username, message, ts)
        for reply in replies.get(post_id, []):
            r_id, r_user, r_msg, r_ts, _ = reply
            r_ts_fmt = datetime.fromisoformat(r_ts).strftime("%Y-%m-%d %H:%M")
            make_llama_post(r_id, r_user, r_msg, r_ts_fmt, indent="        ")
        if i < len(top_level) - 1:
            console.print("[dim]─────────────────────────────[/dim]")


def list_users():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT username FROM users ORDER BY id")).fetchall()
    for row in rows:
        console.print(f"[bold yellow]{row[0]}[/bold yellow]")


def search_posts(keyword):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT u.username, p.message, p.timestamp "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                "WHERE p.message LIKE :keyword "
                "ORDER BY p.timestamp"
            ),
            {"keyword": f"%{keyword}%"},
        ).fetchall()

    if not rows:
        console.print("[dim]No matching posts found.[/dim]")
        return
    for row in rows:
        ts = datetime.fromisoformat(row[2]).strftime("%Y-%m-%d %H:%M")
        console.print(
            f"[dim]{ts}[/dim] [bold yellow]{row[0]}[/bold yellow]: {row[1]}"
        )


def main():
    if len(sys.argv) < 2:
        show_banner()
        console.print("[bold red]Usage: python bbs_db.py <command> [args][/bold red]")
        console.print("Commands: post, read, users, search, reply")
        sys.exit(1)

    init_db()
    show_banner()
    command = sys.argv[1]

    if command == "post":
        if len(sys.argv) < 4:
            console.print("[bold red]Usage: python bbs_db.py post <username> <message>[/bold red]")
            sys.exit(1)
        post_message(sys.argv[2], sys.argv[3])

    elif command == "read":
        read_posts()

    elif command == "users":
        list_users()

    elif command == "reply":
        if len(sys.argv) < 5:
            console.print("[bold red]Usage: python bbs_db.py reply <username> <post_id> <message>[/bold red]")
            sys.exit(1)
        reply_message(sys.argv[2], int(sys.argv[3]), sys.argv[4])

    elif command == "search":
        if len(sys.argv) < 3:
            console.print("[bold red]Usage: python bbs_db.py search <keyword>[/bold red]")
            sys.exit(1)
        search_posts(sys.argv[2])

    else:
        console.print(f"[bold red]Unknown command: {command}[/bold red]")
        console.print("Commands: post, read, users, search, reply")
        sys.exit(1)


if __name__ == "__main__":
    main()
