#!/usr/bin/env python3
"""
BBS (Bulletin Board System) - SQLite Database Version (Gold Tier)

A retro-inspired bulletin board with threads, private messages,
emoji reactions, user profiles, trending posts, and a full
interactive terminal mode with ASCII art and colored output.

All queries use raw SQL via SQLAlchemy's text() — no ORM.
"""

import sys
import os
from datetime import datetime
from sqlalchemy import text
from db import engine, init_db

# ---------------------------------------------------------------------------
# Rich library setup (graceful fallback if not installed)
# ---------------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.prompt import Prompt
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None

# ---------------------------------------------------------------------------
# ASCII art banner
# ---------------------------------------------------------------------------
BANNER = r"""
[bold cyan]
 ____  ____  ____
| __ )| __ )/ ___|
|  _ \|  _ \\___ \
| |_) | |_) |___) |
|____/|____/|____/
[/bold cyan]
[dim]═══════════════════════════════════════[/dim]
[bold yellow]  Welcome to the Bulletin Board System[/bold yellow]
[dim]  ───────────────────────────────────[/dim]
[italic]  "The internet before the internet"[/italic]
[dim]═══════════════════════════════════════[/dim]
"""

PLAIN_BANNER = r"""
 ____  ____  ____
| __ )| __ )/ ___|
|  _ \|  _ \\___ \
| |_) | |_) |___) |
|____/|____/|____/

═══════════════════════════════════════
  Welcome to the Bulletin Board System
  ───────────────────────────────────
  "The internet before the internet"
═══════════════════════════════════════
"""

# Allowed emoji reactions
VALID_EMOJIS = {
    "thumbsup": "👍", "thumbsdown": "👎", "heart": "❤️",
    "laugh": "😂", "fire": "🔥", "wow": "😮",
    "sad": "😢", "clap": "👏", "think": "🤔",
    "100": "💯", "star": "⭐", "rocket": "🚀",
    "eyes": "👀", "wave": "👋", "skull": "💀",
}


def rprint(msg=""):
    """Print with rich markup if available, plain otherwise."""
    if RICH_AVAILABLE:
        console.print(msg)
    else:
        print(msg)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_or_create_user(conn, username):
    """Look up a user by username; create if not found. Returns user ID."""
    result = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    )
    row = result.fetchone()
    if row:
        return row[0]

    conn.execute(
        text("INSERT INTO users (username, created_at) VALUES (:username, :created_at)"),
        {"username": username, "created_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S")},
    )
    result = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    )
    return result.fetchone()[0]


def get_user_id(conn, username):
    """Look up a user; return ID or None."""
    result = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    )
    row = result.fetchone()
    return row[0] if row else None


def format_reactions(conn, post_id):
    """Return a string of emoji reactions for a post, e.g. '👍x3 🔥x1'."""
    result = conn.execute(
        text("""
            SELECT emoji, COUNT(*) as cnt
            FROM reactions
            WHERE post_id = :post_id
            GROUP BY emoji
            ORDER BY cnt DESC
        """),
        {"post_id": post_id},
    )
    rows = result.fetchall()
    if not rows:
        return ""
    parts = []
    for emoji_key, count in rows:
        symbol = VALID_EMOJIS.get(emoji_key, emoji_key)
        parts.append(f"{symbol}x{count}" if count > 1 else symbol)
    return "  " + " ".join(parts)


# ---------------------------------------------------------------------------
# Core commands
# ---------------------------------------------------------------------------

def cmd_post(username, message, parent_id=None):
    """Insert a new post (or reply if parent_id is given)."""
    with engine.connect() as conn:
        user_id = get_or_create_user(conn, username)

        if parent_id is not None:
            # Verify parent exists
            result = conn.execute(
                text("SELECT id FROM posts WHERE id = :pid"),
                {"pid": parent_id},
            )
            if not result.fetchone():
                rprint(f"[red]Error: Post #{parent_id} not found.[/red]" if RICH_AVAILABLE
                       else f"Error: Post #{parent_id} not found.")
                return

        conn.execute(
            text("""
                INSERT INTO posts (user_id, message, timestamp, parent_id)
                VALUES (:user_id, :message, :timestamp, :parent_id)
            """),
            {
                "user_id": user_id,
                "message": message,
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "parent_id": parent_id,
            },
        )
        conn.commit()

        # Get the ID of the post we just created
        result = conn.execute(text("SELECT last_insert_rowid()"))
        new_id = result.fetchone()[0]

    if parent_id:
        rprint(f"[green]Reply posted (#{new_id}).[/green]" if RICH_AVAILABLE
               else f"Reply posted (#{new_id}).")
    else:
        rprint(f"[green]Posted (#{new_id}).[/green]" if RICH_AVAILABLE
               else f"Posted (#{new_id}).")


def cmd_read():
    """Display all top-level posts with their threaded replies."""
    with engine.connect() as conn:
        # Fetch all posts
        result = conn.execute(text("""
            SELECT p.id, u.username, p.message, p.timestamp, p.parent_id
            FROM posts p
            JOIN users u ON p.user_id = u.id
            ORDER BY p.timestamp, p.id
        """))
        all_posts = result.fetchall()

        if not all_posts:
            rprint("No posts yet.")
            return

        # Organize into tree: top-level posts and their children
        top_level = []
        children = {}  # parent_id -> list of posts
        for post_id, username, message, timestamp, parent_id in all_posts:
            if parent_id is None:
                top_level.append((post_id, username, message, timestamp))
            else:
                children.setdefault(parent_id, []).append(
                    (post_id, username, message, timestamp)
                )

        # Print with threading
        for post_id, username, message, timestamp, in top_level:
            ts = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M")
            reactions = format_reactions(conn, post_id)
            if RICH_AVAILABLE:
                rprint(f"[bold cyan]#{post_id}[/bold cyan] [{ts}] [bold]{username}[/bold]: {message}{reactions}")
            else:
                print(f"#{post_id} [{ts}] {username}: {message}{reactions}")

            # Print replies indented
            if post_id in children:
                for reply_id, r_user, r_msg, r_ts in children[post_id]:
                    ts2 = datetime.fromisoformat(r_ts).strftime("%Y-%m-%d %H:%M")
                    r_reactions = format_reactions(conn, reply_id)
                    if RICH_AVAILABLE:
                        rprint(f"   [dim]└─[/dim] [bold cyan]#{reply_id}[/bold cyan] [{ts2}] [bold]{r_user}[/bold]: {r_msg}{r_reactions}")
                    else:
                        print(f"   └─ #{reply_id} [{ts2}] {r_user}: {r_msg}{r_reactions}")


def cmd_users():
    """List all users who have posted, ordered by first post."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT u.username
            FROM users u
            JOIN posts p ON u.id = p.user_id
            GROUP BY u.id
            ORDER BY MIN(p.timestamp), MIN(p.id)
        """))
        rows = result.fetchall()

    for (username,) in rows:
        rprint(username)


def cmd_search(keyword):
    """Search posts by keyword using SQL LIKE."""
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT p.id, u.username, p.message, p.timestamp
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.message LIKE :pattern
                ORDER BY p.timestamp, p.id
            """),
            {"pattern": f"%{keyword}%"},
        )
        rows = result.fetchall()

    if not rows:
        rprint("No matching posts found.")
        return

    for post_id, username, message, timestamp in rows:
        ts = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M")
        if RICH_AVAILABLE:
            rprint(f"[bold cyan]#{post_id}[/bold cyan] [{ts}] [bold]{username}[/bold]: {message}")
        else:
            print(f"#{post_id} [{ts}] {username}: {message}")


# ---------------------------------------------------------------------------
# Gold features: react, profile, bio, dm, inbox, trending
# ---------------------------------------------------------------------------

def cmd_react(post_id, username, emoji_name):
    """Add an emoji reaction to a post."""
    emoji_name = emoji_name.lower()
    if emoji_name not in VALID_EMOJIS:
        rprint(f"Unknown emoji: {emoji_name}")
        rprint(f"Available: {', '.join(sorted(VALID_EMOJIS.keys()))}")
        return

    with engine.connect() as conn:
        # Verify post exists
        result = conn.execute(
            text("SELECT id FROM posts WHERE id = :pid"), {"pid": post_id}
        )
        if not result.fetchone():
            rprint(f"Error: Post #{post_id} not found.")
            return

        user_id = get_or_create_user(conn, username)

        # Check if this exact reaction already exists
        result = conn.execute(
            text("""
                SELECT id FROM reactions
                WHERE post_id = :pid AND user_id = :uid AND emoji = :emoji
            """),
            {"pid": post_id, "uid": user_id, "emoji": emoji_name},
        )
        if result.fetchone():
            # Remove the reaction (toggle off)
            conn.execute(
                text("""
                    DELETE FROM reactions
                    WHERE post_id = :pid AND user_id = :uid AND emoji = :emoji
                """),
                {"pid": post_id, "uid": user_id, "emoji": emoji_name},
            )
            conn.commit()
            rprint(f"Removed {VALID_EMOJIS[emoji_name]} from post #{post_id}.")
            return

        conn.execute(
            text("""
                INSERT INTO reactions (post_id, user_id, emoji)
                VALUES (:pid, :uid, :emoji)
            """),
            {"pid": post_id, "uid": user_id, "emoji": emoji_name},
        )
        conn.commit()
    rprint(f"Reacted {VALID_EMOJIS[emoji_name]} to post #{post_id}.")


def cmd_profile(username):
    """Show a user's profile: join date, post count, bio."""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, bio, created_at FROM users WHERE username = :username"),
            {"username": username},
        )
        row = result.fetchone()
        if not row:
            rprint(f"User '{username}' not found.")
            return
        user_id, bio, created_at = row

        result = conn.execute(
            text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"),
            {"uid": user_id},
        )
        post_count = result.fetchone()[0]

        result = conn.execute(
            text("""
                SELECT COUNT(*) FROM reactions r
                JOIN posts p ON r.post_id = p.id
                WHERE p.user_id = :uid
            """),
            {"uid": user_id},
        )
        reactions_received = result.fetchone()[0]

    join_date = datetime.fromisoformat(created_at).strftime("%Y-%m-%d")

    if RICH_AVAILABLE:
        table = Table(title=f"Profile: {username}", box=box.ROUNDED, show_header=False)
        table.add_column("Field", style="bold")
        table.add_column("Value")
        table.add_row("Joined", join_date)
        table.add_row("Posts", str(post_count))
        table.add_row("Reactions received", str(reactions_received))
        table.add_row("Bio", bio if bio else "(no bio set)")
        console.print(table)
    else:
        print(f"=== Profile: {username} ===")
        print(f"  Joined: {join_date}")
        print(f"  Posts: {post_count}")
        print(f"  Reactions received: {reactions_received}")
        print(f"  Bio: {bio if bio else '(no bio set)'}")


def cmd_bio(username, bio_text):
    """Set or update a user's bio."""
    with engine.connect() as conn:
        user_id = get_or_create_user(conn, username)
        conn.execute(
            text("UPDATE users SET bio = :bio WHERE id = :uid"),
            {"bio": bio_text, "uid": user_id},
        )
        conn.commit()
    rprint("Bio updated.")


def cmd_dm(sender, recipient, message):
    """Send a private message from sender to recipient."""
    with engine.connect() as conn:
        sender_id = get_or_create_user(conn, sender)
        recipient_id = get_or_create_user(conn, recipient)
        if sender_id == recipient_id:
            rprint("You can't DM yourself.")
            return
        conn.execute(
            text("""
                INSERT INTO messages (sender_id, recipient_id, message, timestamp)
                VALUES (:sid, :rid, :msg, :ts)
            """),
            {
                "sid": sender_id,
                "rid": recipient_id,
                "msg": message,
                "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )
        conn.commit()
    rprint(f"Message sent to {recipient}.")


def cmd_inbox(username):
    """Show all DMs for a user (received and sent), mark received as read."""
    with engine.connect() as conn:
        user_id = get_user_id(conn, username)
        if user_id is None:
            rprint(f"User '{username}' not found.")
            return

        # Received messages
        result = conn.execute(
            text("""
                SELECT u.username, m.message, m.timestamp, m.read
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE m.recipient_id = :uid
                ORDER BY m.timestamp
            """),
            {"uid": user_id},
        )
        received = result.fetchall()

        # Sent messages
        result = conn.execute(
            text("""
                SELECT u.username, m.message, m.timestamp
                FROM messages m
                JOIN users u ON m.recipient_id = u.id
                WHERE m.sender_id = :uid
                ORDER BY m.timestamp
            """),
            {"uid": user_id},
        )
        sent = result.fetchall()

        if not received and not sent:
            rprint("Inbox is empty.")
            return

        if received:
            if RICH_AVAILABLE:
                rprint("[bold underline]Received Messages[/bold underline]")
            else:
                print("=== Received Messages ===")
            for sender, msg, ts, is_read in received:
                ts_fmt = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
                new_tag = "" if is_read else " [NEW]"
                if RICH_AVAILABLE:
                    new_style = "[bold red] [NEW][/bold red]" if not is_read else ""
                    rprint(f"  [{ts_fmt}] [bold]{sender}[/bold]: {msg}{new_style}")
                else:
                    print(f"  [{ts_fmt}] {sender}: {msg}{new_tag}")

        if sent:
            if RICH_AVAILABLE:
                rprint("[bold underline]Sent Messages[/bold underline]")
            else:
                print("=== Sent Messages ===")
            for recipient_name, msg, ts in sent:
                ts_fmt = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
                if RICH_AVAILABLE:
                    rprint(f"  [{ts_fmt}] → [bold]{recipient_name}[/bold]: {msg}")
                else:
                    print(f"  [{ts_fmt}] → {recipient_name}: {msg}")

        # Mark all received as read
        conn.execute(
            text("UPDATE messages SET read = 1 WHERE recipient_id = :uid AND read = 0"),
            {"uid": user_id},
        )
        conn.commit()


def cmd_trending():
    """Show the top 10 posts by total reaction count."""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT p.id, u.username, p.message, p.timestamp, COUNT(r.id) as react_count
            FROM posts p
            JOIN users u ON p.user_id = u.id
            JOIN reactions r ON r.post_id = p.id
            GROUP BY p.id
            ORDER BY react_count DESC, p.timestamp DESC
            LIMIT 10
        """))
        rows = result.fetchall()

    if not rows:
        rprint("No reactions yet. Be the first to react!")
        return

    if RICH_AVAILABLE:
        rprint("[bold underline]🔥 Trending Posts[/bold underline]\n")
    else:
        print("=== Trending Posts ===\n")

    for rank, (post_id, username, message, timestamp, count) in enumerate(rows, 1):
        ts = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M")
        with engine.connect() as conn:
            reactions = format_reactions(conn, post_id)
        if RICH_AVAILABLE:
            rprint(f"  [bold yellow]#{rank}[/bold yellow] [bold cyan]Post #{post_id}[/bold cyan] [{ts}] [bold]{username}[/bold]: {message}")
            rprint(f"      {reactions}  ({count} reaction{'s' if count != 1 else ''})\n")
        else:
            print(f"  #{rank} Post #{post_id} [{ts}] {username}: {message}")
            print(f"      {reactions}  ({count} reaction{'s' if count != 1 else ''})\n")


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def interactive_mode():
    """Launch an interactive BBS session with a persistent prompt."""
    init_db()

    if RICH_AVAILABLE:
        console.print(BANNER)
    else:
        print(PLAIN_BANNER)

    # Login
    if RICH_AVAILABLE:
        username = Prompt.ask("[bold]Enter your username[/bold]").strip()
    else:
        username = input("Enter your username: ").strip()

    if not username:
        rprint("Username cannot be empty.")
        return

    with engine.connect() as conn:
        get_or_create_user(conn, username)
        conn.commit()

    if RICH_AVAILABLE:
        console.print(f"\n[bold green]Logged in as [underline]{username}[/underline]. Type 'help' for commands.[/bold green]\n")
    else:
        print(f"\nLogged in as {username}. Type 'help' for commands.\n")

    # Check for unread DMs
    with engine.connect() as conn:
        uid = get_user_id(conn, username)
        result = conn.execute(
            text("SELECT COUNT(*) FROM messages WHERE recipient_id = :uid AND read = 0"),
            {"uid": uid},
        )
        unread = result.fetchone()[0]
    if unread > 0:
        if RICH_AVAILABLE:
            console.print(f"[bold red]📬 You have {unread} unread message{'s' if unread != 1 else ''}! Type 'inbox' to read.[/bold red]\n")
        else:
            print(f"📬 You have {unread} unread message{'s' if unread != 1 else ''}! Type 'inbox' to read.\n")

    # Command loop
    while True:
        try:
            if RICH_AVAILABLE:
                raw = Prompt.ask(f"[bold magenta]bbs ({username})>[/bold magenta] ").strip()
            else:
                raw = input(f"bbs ({username})> ").strip()
        except (EOFError, KeyboardInterrupt):
            rprint("\nGoodbye!")
            break

        if not raw:
            continue

        parts = _smart_split(raw)
        cmd = parts[0].lower()

        if cmd in ("quit", "exit", "logout"):
            rprint("Goodbye! 👋")
            break

        elif cmd == "help":
            _print_help()

        elif cmd == "post":
            if len(parts) < 2:
                rprint("Usage: post <message>")
                continue
            cmd_post(username, " ".join(parts[1:]))

        elif cmd == "read":
            cmd_read()

        elif cmd == "users":
            cmd_users()

        elif cmd == "search":
            if len(parts) < 2:
                rprint("Usage: search <keyword>")
                continue
            cmd_search(" ".join(parts[1:]))

        elif cmd == "reply":
            if len(parts) < 3:
                rprint("Usage: reply <post_id> <message>")
                continue
            try:
                pid = int(parts[1])
            except ValueError:
                rprint("Post ID must be a number.")
                continue
            cmd_post(username, " ".join(parts[2:]), parent_id=pid)

        elif cmd == "react":
            if len(parts) < 3:
                rprint("Usage: react <post_id> <emoji>")
                rprint(f"Available emojis: {', '.join(sorted(VALID_EMOJIS.keys()))}")
                continue
            try:
                pid = int(parts[1])
            except ValueError:
                rprint("Post ID must be a number.")
                continue
            cmd_react(pid, username, parts[2])

        elif cmd == "emojis":
            if RICH_AVAILABLE:
                rprint("[bold underline]Available Emojis[/bold underline]")
            else:
                print("Available Emojis:")
            for name, symbol in sorted(VALID_EMOJIS.items()):
                rprint(f"  {name:<12} {symbol}")

        elif cmd == "profile":
            target = parts[1] if len(parts) > 1 else username
            cmd_profile(target)

        elif cmd == "bio":
            if len(parts) < 2:
                rprint("Usage: bio <text>")
                continue
            cmd_bio(username, " ".join(parts[1:]))

        elif cmd == "dm":
            if len(parts) < 3:
                rprint("Usage: dm <username> <message>")
                continue
            cmd_dm(username, parts[1], " ".join(parts[2:]))

        elif cmd == "inbox":
            cmd_inbox(username)

        elif cmd == "trending":
            cmd_trending()

        else:
            rprint(f"Unknown command: {cmd}. Type 'help' for available commands.")


def _smart_split(raw):
    """Split input respecting quoted strings, like a shell would."""
    import shlex
    try:
        return shlex.split(raw)
    except ValueError:
        return raw.split()


def _print_help():
    """Print the help menu for interactive mode."""
    if RICH_AVAILABLE:
        table = Table(title="BBS Commands", box=box.SIMPLE_HEAVY)
        table.add_column("Command", style="bold cyan")
        table.add_column("Description")
        table.add_row("post <message>", "Post a new message to the board")
        table.add_row("read", "Read all posts (with threads)")
        table.add_row("reply <id> <message>", "Reply to a post by ID")
        table.add_row("search <keyword>", "Search posts by keyword")
        table.add_row("users", "List all users")
        table.add_row("react <id> <emoji>", "React to a post (toggle on/off)")
        table.add_row("emojis", "List available emoji reactions")
        table.add_row("trending", "Show most-reacted posts")
        table.add_row("dm <user> <message>", "Send a private message")
        table.add_row("inbox", "View your messages")
        table.add_row("profile [user]", "View a user profile (default: you)")
        table.add_row("bio <text>", "Set your bio")
        table.add_row("quit", "Log out and exit")
        console.print(table)
    else:
        print("=== BBS Commands ===")
        print("  post <message>          Post a new message")
        print("  read                    Read all posts (with threads)")
        print("  reply <id> <message>    Reply to a post by ID")
        print("  search <keyword>        Search posts by keyword")
        print("  users                   List all users")
        print("  react <id> <emoji>      React to a post (toggle on/off)")
        print("  emojis                  List available emojis")
        print("  trending                Show most-reacted posts")
        print("  dm <user> <message>     Send a private message")
        print("  inbox                   View your messages")
        print("  profile [user]          View a user profile")
        print("  bio <text>              Set your bio")
        print("  quit                    Log out and exit")


# ---------------------------------------------------------------------------
# CLI entry point (one-shot mode)
# ---------------------------------------------------------------------------

def print_usage():
    print("Usage:")
    print("  python bbs_db.py post <username> <message>       - Post a message")
    print("  python bbs_db.py read                            - Read all messages")
    print("  python bbs_db.py users                           - List all users")
    print("  python bbs_db.py search <keyword>                - Search by keyword")
    print("  python bbs_db.py reply <post_id> <user> <msg>    - Reply to a post")
    print("  python bbs_db.py react <post_id> <user> <emoji>  - React to a post")
    print("  python bbs_db.py profile <username>              - View user profile")
    print("  python bbs_db.py bio <username> <text>           - Set user bio")
    print("  python bbs_db.py dm <from> <to> <message>        - Send a DM")
    print("  python bbs_db.py inbox <username>                - View inbox")
    print("  python bbs_db.py trending                        - Trending posts")
    print("  python bbs_db.py interactive                     - Launch interactive mode")


def main():
    init_db()

    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

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
            parent_id = int(sys.argv[2])
        except ValueError:
            print("Post ID must be a number.")
            sys.exit(1)
        cmd_post(sys.argv[3], sys.argv[4], parent_id=parent_id)

    elif command == "react":
        if len(sys.argv) < 5:
            print("Usage: python bbs_db.py react <post_id> <username> <emoji>")
            print(f"Available emojis: {', '.join(sorted(VALID_EMOJIS.keys()))}")
            sys.exit(1)
        try:
            post_id = int(sys.argv[2])
        except ValueError:
            print("Post ID must be a number.")
            sys.exit(1)
        cmd_react(post_id, sys.argv[3], sys.argv[4])

    elif command == "profile":
        if len(sys.argv) < 3:
            print("Usage: python bbs_db.py profile <username>")
            sys.exit(1)
        cmd_profile(sys.argv[2])

    elif command == "bio":
        if len(sys.argv) < 4:
            print("Usage: python bbs_db.py bio <username> <text>")
            sys.exit(1)
        cmd_bio(sys.argv[2], sys.argv[3])

    elif command == "dm":
        if len(sys.argv) < 5:
            print("Usage: python bbs_db.py dm <from> <to> <message>")
            sys.exit(1)
        cmd_dm(sys.argv[2], sys.argv[3], sys.argv[4])

    elif command == "inbox":
        if len(sys.argv) < 3:
            print("Usage: python bbs_db.py inbox <username>")
            sys.exit(1)
        cmd_inbox(sys.argv[2])

    elif command == "trending":
        cmd_trending()

    elif command == "interactive":
        interactive_mode()

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
