import sys
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.text import Text
from sqlalchemy import text

from db import engine, init_db

console = Console()

WELCOME = r"""
 ____  ____  ____
|  _ \|  _ \/ ___|
| |_) | |_) \___ \
|  _ <|  _ < ___) |
|_| \_\_| \_\____/

  Bulletin Board System
  Type 'help' for commands
"""


def format_post_rich(row, indent=0):
    ts = datetime.fromisoformat(row.timestamp)
    line = Text()
    line.append("  " * indent)
    line.append(f"[{ts.strftime('%Y-%m-%d %H:%M')}] ", style="dim")
    line.append(f"#{row.id} ", style="dim cyan")
    line.append(f"{row.username}", style="bold cyan")
    line.append(": ")
    line.append(row.message)
    return line


def format_post_plain(row, indent=0):
    ts = datetime.fromisoformat(row.timestamp)
    prefix = "  " * indent
    return f"{prefix}[{ts.strftime('%Y-%m-%d %H:%M')}] {row.username}: {row.message}"


def _format_age(hours):
    if hours < 1:
        return f"{int(hours * 60)}m"
    elif hours < 48:
        return f"{hours:.1f}h"
    else:
        return f"{hours / 24:.1f}d"


def get_user_id(conn, username):
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()
    return row.id if row else None


def get_or_create_user(conn, username):
    conn.execute(
        text("INSERT OR IGNORE INTO users (username) VALUES (:u)"),
        {"u": username},
    )
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()
    return row.id


def cmd_post(username, message, parent_id=None):
    with engine.begin() as conn:
        user_id = get_or_create_user(conn, username)
        conn.execute(
            text("""
                INSERT INTO posts (user_id, message, timestamp, parent_id)
                VALUES (:uid, :msg, :ts, :parent)
            """),
            {
                "uid": user_id,
                "msg": message,
                "ts": datetime.now().isoformat(timespec="milliseconds"),
                "parent": parent_id,
            },
        )
    print("Posted.")


def cmd_read():
    with engine.connect() as conn:
        # Fetch all top-level posts, then replies separately for indentation
        rows = conn.execute(text("""
            SELECT p.id, u.username, p.message, p.timestamp, p.parent_id
            FROM posts p JOIN users u ON p.user_id = u.id
            ORDER BY p.timestamp, p.id
        """)).fetchall()

    # Build a map of parent_id -> [children]
    top_level = [r for r in rows if r.parent_id is None]
    children = {}
    for r in rows:
        if r.parent_id is not None:
            children.setdefault(r.parent_id, []).append(r)

    def print_thread(row, depth=0):
        console.print(format_post_rich(row, indent=depth))
        for child in children.get(row.id, []):
            print_thread(child, depth + 1)

    for row in top_level:
        print_thread(row)


def cmd_users():
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT username FROM users ORDER BY id")).fetchall()
    for row in rows:
        print(row.username)


def cmd_search(keyword):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT p.id, u.username, p.message, p.timestamp, p.parent_id
                FROM posts p JOIN users u ON p.user_id = u.id
                WHERE p.message LIKE :kw
                ORDER BY p.timestamp, p.id
            """),
            {"kw": f"%{keyword}%"},
        ).fetchall()
    for row in rows:
        console.print(format_post_rich(row))


def cmd_reply(post_id, username, message):
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT id FROM posts WHERE id = :pid"),
            {"pid": post_id},
        ).fetchone()
    if not exists:
        print(f"Error: post #{post_id} does not exist.")
        sys.exit(1)
    cmd_post(username, message, parent_id=post_id)


def cmd_dm(sender_username, recipient_username, message):
    with engine.begin() as conn:
        sender_id = get_user_id(conn, sender_username)
        if sender_id is None:
            print(f"Error: user '{sender_username}' does not exist.")
            sys.exit(1)
        recipient_id = get_user_id(conn, recipient_username)
        if recipient_id is None:
            print(f"Error: user '{recipient_username}' does not exist.")
            sys.exit(1)
        if sender_id == recipient_id:
            print("Error: cannot send a DM to yourself.")
            sys.exit(1)
        conn.execute(
            text("""
                INSERT INTO direct_messages
                    (sender_id, recipient_id, message, timestamp, read_at)
                VALUES (:sid, :rid, :msg, :ts, NULL)
            """),
            {
                "sid": sender_id,
                "rid": recipient_id,
                "msg": message,
                "ts": datetime.now().isoformat(timespec="milliseconds"),
            },
        )
    print(f"DM sent to {recipient_username}.")


def cmd_inbox(username):
    with engine.begin() as conn:
        user_id = get_user_id(conn, username)
        if user_id is None:
            print(f"Error: user '{username}' does not exist.")
            sys.exit(1)
        rows = conn.execute(
            text("""
                SELECT dm.id, s.username AS sender, dm.message,
                       dm.timestamp, dm.read_at
                FROM direct_messages dm
                JOIN users s ON dm.sender_id = s.id
                WHERE dm.recipient_id = :uid
                ORDER BY dm.read_at IS NOT NULL, dm.timestamp ASC
            """),
            {"uid": user_id},
        ).fetchall()
        conn.execute(
            text("""
                UPDATE direct_messages
                SET read_at = :now
                WHERE recipient_id = :uid AND read_at IS NULL
            """),
            {"uid": user_id, "now": datetime.now().isoformat(timespec="milliseconds")},
        )

    if not rows:
        console.print(f"[dim]No messages in inbox for {username}.[/dim]")
        return

    unread_count = sum(1 for r in rows if r.read_at is None)
    console.print(
        f"[bold]Inbox for [cyan]{username}[/cyan][/bold] — "
        f"[bold yellow]{unread_count} unread[/bold yellow]"
    )
    for row in rows:
        ts = datetime.fromisoformat(row.timestamp)
        line = Text()
        if row.read_at is None:
            line.append("[UNREAD] ", style="bold yellow")
            line.append(f"#{row.id} ", style="dim cyan")
            line.append(f"[{ts.strftime('%Y-%m-%d %H:%M')}] ", style="dim")
            line.append(row.sender, style="bold cyan")
            line.append(f": {row.message}", style="bold")
        else:
            line.append("[read]   ", style="dim")
            line.append(f"#{row.id} ", style="dim cyan")
            line.append(f"[{ts.strftime('%Y-%m-%d %H:%M')}] ", style="dim")
            line.append(row.sender, style="cyan")
            line.append(f": {row.message}")
        console.print(line)


def cmd_leaderboard():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                u.username,
                COUNT(DISTINCT CASE WHEN p.parent_id IS NULL THEN p.id END)
                    AS total_posts,
                COUNT(DISTINCT r.id) AS replies_received
            FROM users u
            LEFT JOIN posts p ON p.user_id = u.id
            LEFT JOIN posts r ON r.parent_id = p.id
                              AND p.parent_id IS NULL
            GROUP BY u.id, u.username
            ORDER BY total_posts DESC, replies_received DESC, u.username ASC
        """)).fetchall()

    if not rows:
        console.print("[dim]No users yet.[/dim]")
        return

    table = Table(title="Leaderboard", show_header=True, header_style="bold magenta")
    table.add_column("#",                style="dim",       width=4,  justify="right")
    table.add_column("Username",         style="bold cyan", min_width=12)
    table.add_column("Posts",            justify="right",   width=7)
    table.add_column("Replies Received", justify="right",   width=16)

    for rank, row in enumerate(rows, start=1):
        table.add_row(str(rank), row.username, str(row.total_posts), str(row.replies_received))

    console.print(table)


def cmd_trending():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT
                p.id,
                u.username,
                p.message,
                p.timestamp,
                COUNT(r.id) AS reply_count,
                ROUND(
                    (julianday('now') - julianday(p.timestamp)) * 24,
                    2
                ) AS hours_ago,
                CAST(COUNT(r.id) AS REAL) /
                    pow(
                        (julianday('now') - julianday(p.timestamp)) * 24 + 2,
                        1.2
                    ) AS score
            FROM posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN posts r ON r.parent_id = p.id
            WHERE p.parent_id IS NULL
            GROUP BY p.id, u.username, p.message, p.timestamp
            ORDER BY score DESC
            LIMIT 10
        """)).fetchall()

    if not rows:
        console.print("[dim]No posts yet.[/dim]")
        return

    table = Table(title="Trending Posts", show_header=True, header_style="bold yellow")
    table.add_column("#",       style="dim",   width=4,  justify="right")
    table.add_column("Score",   justify="right", width=8)
    table.add_column("Age",     width=7)
    table.add_column("Replies", justify="right", width=7)
    table.add_column("Post",    min_width=35)

    for rank, row in enumerate(rows, start=1):
        ts = datetime.fromisoformat(row.timestamp)
        cell = Text()
        cell.append(f"[{ts.strftime('%Y-%m-%d %H:%M')}] ", style="dim")
        cell.append(f"#{row.id} ", style="dim cyan")
        cell.append(row.username, style="bold cyan")
        cell.append(f": {row.message}")

        table.add_row(
            str(rank),
            f"{row.score:.4f}",
            _format_age(row.hours_ago),
            str(row.reply_count),
            cell,
        )

    console.print(table)


def interactive_mode():
    console.print(WELCOME, style="bold green")
    username = console.input("[bold cyan]Login as:[/bold cyan] ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)
    with engine.begin() as conn:
        get_or_create_user(conn, username)
    console.print(f"Welcome, [bold cyan]{username}[/bold cyan]! Type 'help' for commands.\n")

    while True:
        try:
            raw = console.input(f"[bold green]bbs>[/bold green] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!")
            break

        if not raw:
            continue

        parts = raw.split(None, 1)
        cmd = parts[0].lower()

        if cmd == "quit" or cmd == "exit":
            console.print("Goodbye!")
            break
        elif cmd == "help":
            console.print(
                "[bold]Commands:[/bold]\n"
                "  post <message>             — post a message\n"
                "  reply <id> <message>       — reply to a post\n"
                "  read                       — read all messages\n"
                "  search <keyword>           — search messages\n"
                "  users                      — list all users\n"
                "  dm <recipient> <message>   — send a private message\n"
                "  inbox                      — view your inbox\n"
                "  leaderboard                — view user leaderboard\n"
                "  trending                   — view trending posts\n"
                "  quit                       — exit"
            )
        elif cmd == "post":
            if len(parts) < 2 or not parts[1].strip():
                print("Usage: post <message>")
            else:
                cmd_post(username, parts[1].strip())
        elif cmd == "reply":
            rest = parts[1].strip() if len(parts) > 1 else ""
            reply_parts = rest.split(None, 1)
            if len(reply_parts) < 2:
                print("Usage: reply <post_id> <message>")
            else:
                try:
                    post_id = int(reply_parts[0])
                except ValueError:
                    print("Error: post_id must be a number.")
                    continue
                cmd_reply(post_id, username, reply_parts[1])
        elif cmd == "read":
            cmd_read()
        elif cmd == "search":
            if len(parts) < 2 or not parts[1].strip():
                print("Usage: search <keyword>")
            else:
                cmd_search(parts[1].strip())
        elif cmd == "users":
            cmd_users()
        elif cmd == "dm":
            rest = parts[1].strip() if len(parts) > 1 else ""
            dm_parts = rest.split(None, 1)
            if len(dm_parts) < 2:
                print("Usage: dm <recipient> <message>")
            else:
                recipient, dm_message = dm_parts[0], dm_parts[1]
                with engine.connect() as conn:
                    recipient_id = get_user_id(conn, recipient)
                    sender_id = get_user_id(conn, username)
                if recipient_id is None:
                    print(f"Error: user '{recipient}' does not exist.")
                elif sender_id == recipient_id:
                    print("Error: cannot send a DM to yourself.")
                else:
                    cmd_dm(username, recipient, dm_message)
        elif cmd == "inbox":
            cmd_inbox(username)
        elif cmd == "leaderboard":
            cmd_leaderboard()
        elif cmd == "trending":
            cmd_trending()
        else:
            print(f"Unknown command: {cmd}. Type 'help' for commands.")


def main():
    init_db()

    if len(sys.argv) < 2:
        print("Usage: python bbs_db.py <command> [args]")
        print("Commands: post <username> <message>, read, users, search <keyword>,")
        print("          reply <post_id> <username> <message>,")
        print("          dm <sender> <recipient> <message>, inbox <username>,")
        print("          leaderboard, trending, interactive")
        sys.exit(1)

    command = sys.argv[1]

    if command == "post":
        if len(sys.argv) < 4:
            print("Usage: python bbs_db.py post <username> <message>")
            sys.exit(1)
        cmd_post(sys.argv[2], sys.argv[3])
    elif command == "read":
        cmd_read()
    elif command == "users":
        cmd_users()
    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python bbs_db.py search <keyword>")
            sys.exit(1)
        cmd_search(sys.argv[2])
    elif command == "reply":
        if len(sys.argv) < 5:
            print("Usage: python bbs_db.py reply <post_id> <username> <message>")
            sys.exit(1)
        try:
            post_id = int(sys.argv[2])
        except ValueError:
            print("Error: post_id must be a number.")
            sys.exit(1)
        cmd_reply(post_id, sys.argv[3], sys.argv[4])
    elif command == "dm":
        if len(sys.argv) < 5:
            print("Usage: python bbs_db.py dm <sender> <recipient> <message>")
            sys.exit(1)
        cmd_dm(sys.argv[2], sys.argv[3], sys.argv[4])
    elif command == "inbox":
        if len(sys.argv) < 3:
            print("Usage: python bbs_db.py inbox <username>")
            sys.exit(1)
        cmd_inbox(sys.argv[2])
    elif command == "leaderboard":
        cmd_leaderboard()
    elif command == "trending":
        cmd_trending()
    elif command == "interactive":
        interactive_mode()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
