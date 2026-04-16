"""
BBS - Bulletin Board System (Part B: SQLite + Gold Features)

Standard commands (same interface as bbs.py):
    python bbs_db.py post <username> <message>
    python bbs_db.py read
    python bbs_db.py users
    python bbs_db.py search <keyword>

Gold-tier extensions:
    python bbs_db.py reply <post_id> <username> <message>   # Reply to a post (threads)
    python bbs_db.py profile <username>                      # View user profile
    python bbs_db.py setbio <username> <bio>                 # Set user bio
    python bbs_db.py                                         # Interactive mode (bbs> prompt)
"""

import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich import box
from sqlalchemy import text

from db import engine, init_db

console = Console()

BANNER = r"""
 ____  ____  ____
|  _ \|  _ \/ ___|
| |_) | |_) \___ \
|  _ <|  __/ ___) |
|_| \_\_|   |____/
"""

TAGLINE = "Retro Bulletin Board System - SQLite Edition"


def print_banner():
    console.print(Panel(
        f"[bold cyan]{BANNER}[/bold cyan][dim]{TAGLINE}[/dim]",
        border_style="cyan",
        padding=(0, 2),
    ))


# -- helpers ------------------------------------------------------------------

def get_or_create_user(conn, username):
    """Return user id, creating the user row if needed."""
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()
    if row:
        return row[0]
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    result = conn.execute(
        text("INSERT INTO users (username, created_at) VALUES (:u, :ts)"),
        {"u": username, "ts": now},
    )
    return result.lastrowid


def format_ts(ts_str):
    """Return display-friendly timestamp (strips seconds)."""
    return ts_str.replace("T", " ")[:16]


def render_posts(rows, indent=0):
    """
    Render a list of (id, username, message, timestamp) rows with optional indent.
    Returns a Rich Text object.
    """
    out = Text()
    prefix = "  " * indent
    for row in rows:
        post_id, username, message, ts = row
        out.append(f"{prefix}[#{post_id}] ", style="dim")
        out.append(f"[{format_ts(ts)}] ", style="green")
        out.append(f"{username}", style="bold yellow")
        out.append(": ")
        out.append(f"{message}\n")
    return out


# -- commands -----------------------------------------------------------------

def cmd_post(username, message, parent_id=None):
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with engine.begin() as conn:
        user_id = get_or_create_user(conn, username)
        conn.execute(
            text("""
                INSERT INTO posts (user_id, message, timestamp, parent_id)
                VALUES (:uid, :msg, :ts, :pid)
            """),
            {"uid": user_id, "msg": message, "ts": now, "pid": parent_id},
        )
    console.print("[bold green]Posted.[/bold green]")


def cmd_reply(post_id_str, username, message):
    try:
        post_id = int(post_id_str)
    except ValueError:
        console.print(f"[red]Error:[/red] post_id must be an integer, got '{post_id_str}'")
        return
    with engine.connect() as conn:
        parent = conn.execute(
            text("SELECT id FROM posts WHERE id = :pid"),
            {"pid": post_id},
        ).fetchone()
    if not parent:
        console.print(f"[red]Error:[/red] No post with id {post_id}.")
        return
    cmd_post(username, message, parent_id=post_id)


def _fetch_thread(conn, parent_id):
    """Recursively fetch thread replies for a given parent post id."""
    rows = conn.execute(
        text("""
            SELECT p.id, u.username, p.message, p.timestamp
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.parent_id = :pid
            ORDER BY p.timestamp ASC
        """),
        {"pid": parent_id},
    ).fetchall()
    return rows


def cmd_read():
    with engine.connect() as conn:
        # Fetch top-level posts (no parent)
        top_posts = conn.execute(text("""
            SELECT p.id, u.username, p.message, p.timestamp
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.parent_id IS NULL
            ORDER BY p.timestamp ASC
        """)).fetchall()

        if not top_posts:
            console.print("[dim]No messages yet.[/dim]")
            return

        for post in top_posts:
            post_id, username, message, ts = post
            # Top-level post
            line = Text()
            line.append(f"[#{post_id}] ", style="dim")
            line.append(f"[{format_ts(ts)}] ", style="green")
            line.append(f"{username}", style="bold yellow")
            line.append(": ")
            line.append(message)
            console.print(line)

            # Replies (one level, indented)
            replies = _fetch_thread(conn, post_id)
            for reply in replies:
                rid, runame, rmsg, rts = reply
                rline = Text()
                rline.append("  -> ", style="dim cyan")
                rline.append(f"[#{rid}] ", style="dim")
                rline.append(f"[{format_ts(rts)}] ", style="green")
                rline.append(f"{runame}", style="bold yellow")
                rline.append(": ")
                rline.append(rmsg)
                console.print(rline)


def cmd_users():
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT u.username, COUNT(p.id) AS post_count, u.created_at
            FROM users u
            LEFT JOIN posts p ON p.user_id = u.id
            GROUP BY u.id
            ORDER BY u.username ASC
        """)).fetchall()

    if not rows:
        console.print("[dim]No users yet.[/dim]")
        return

    table = Table(title="Users", box=box.SIMPLE_HEAVY, border_style="cyan")
    table.add_column("Username", style="bold yellow")
    table.add_column("Posts", justify="right", style="green")
    table.add_column("Joined", style="dim")

    for username, post_count, created_at in rows:
        table.add_row(username, str(post_count), format_ts(created_at))

    console.print(table)


def cmd_search(keyword):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT p.id, u.username, p.message, p.timestamp
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.message LIKE :kw
                ORDER BY p.timestamp ASC
            """),
            {"kw": f"%{keyword}%"},
        ).fetchall()

    if not rows:
        console.print(f"[dim]No posts matching '[bold]{keyword}[/bold]'.[/dim]")
        return

    console.print(Rule(f"Results for '[bold yellow]{keyword}[/bold yellow]'", style="cyan"))
    for post_id, username, message, ts in rows:
        line = Text()
        line.append(f"[#{post_id}] ", style="dim")
        line.append(f"[{format_ts(ts)}] ", style="green")
        line.append(f"{username}", style="bold yellow")
        line.append(": ")
        # Highlight the matched keyword
        msg_lower = message.lower()
        kw_lower = keyword.lower()
        idx = msg_lower.find(kw_lower)
        if idx >= 0:
            line.append(message[:idx])
            line.append(message[idx:idx + len(keyword)], style="bold white on red")
            line.append(message[idx + len(keyword):])
        else:
            line.append(message)
        console.print(line)


def cmd_profile(username):
    with engine.connect() as conn:
        user = conn.execute(
            text("SELECT id, bio, created_at FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()

        if not user:
            console.print(f"[red]No user named '{username}'.[/red]")
            return

        user_id, bio, created_at = user
        post_count = conn.execute(
            text("SELECT COUNT(*) FROM posts WHERE user_id = :uid AND parent_id IS NULL"),
            {"uid": user_id},
        ).scalar()
        reply_count = conn.execute(
            text("SELECT COUNT(*) FROM posts WHERE user_id = :uid AND parent_id IS NOT NULL"),
            {"uid": user_id},
        ).scalar()

    bio_display = bio if bio else "[dim](no bio set)[/dim]"
    panel_content = (
        f"[bold cyan]Username:[/bold cyan] [bold yellow]{username}[/bold yellow]\n"
        f"[bold cyan]Joined:[/bold cyan]   {format_ts(created_at)}\n"
        f"[bold cyan]Posts:[/bold cyan]    {post_count}  "
        f"[bold cyan]Replies:[/bold cyan] {reply_count}\n"
        f"[bold cyan]Bio:[/bold cyan]      {bio_display}"
    )
    console.print(Panel(panel_content, title=f"Profile: {username}", border_style="yellow"))


def cmd_setbio(username, bio):
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE users SET bio = :bio WHERE username = :u"),
            {"bio": bio, "u": username},
        )
    if result.rowcount == 0:
        console.print(f"[red]No user named '{username}'. Post something first to create an account.[/red]")
    else:
        console.print(f"[green]Bio updated for {username}.[/green]")


# -- interactive mode ----------------------------------------------------------

HELP_TEXT = """[bold cyan]Available commands:[/bold cyan]
  [yellow]post[/yellow] <username> <message>         Post a message
  [yellow]reply[/yellow] <post_id> <username> <msg>  Reply to a post
  [yellow]read[/yellow]                              Read all messages
  [yellow]users[/yellow]                             List all users
  [yellow]search[/yellow] <keyword>                  Search messages
  [yellow]profile[/yellow] <username>                View user profile
  [yellow]setbio[/yellow] <username> <bio>           Set your bio
  [yellow]help[/yellow]                              Show this help
  [yellow]quit[/yellow] / [yellow]exit[/yellow]                      Exit BBS"""


def dispatch(args):
    """Run a single command from a list of argument strings."""
    if not args:
        return
    cmd = args[0].lower()

    if cmd == "post":
        if len(args) < 3:
            console.print("[red]Usage: post <username> <message>[/red]")
        else:
            cmd_post(args[1], args[2])

    elif cmd == "reply":
        if len(args) < 4:
            console.print("[red]Usage: reply <post_id> <username> <message>[/red]")
        else:
            cmd_reply(args[1], args[2], args[3])

    elif cmd == "read":
        cmd_read()

    elif cmd == "users":
        cmd_users()

    elif cmd == "search":
        if len(args) < 2:
            console.print("[red]Usage: search <keyword>[/red]")
        else:
            cmd_search(args[1])

    elif cmd == "profile":
        if len(args) < 2:
            console.print("[red]Usage: profile <username>[/red]")
        else:
            cmd_profile(args[1])

    elif cmd == "setbio":
        if len(args) < 3:
            console.print("[red]Usage: setbio <username> <bio>[/red]")
        else:
            cmd_setbio(args[1], args[2])

    elif cmd in ("help", "?"):
        console.print(HELP_TEXT)

    elif cmd in ("quit", "exit", "q"):
        console.print("[dim]Goodbye. Drop your carrier.[/dim]")
        sys.exit(0)

    else:
        console.print(f"[red]Unknown command:[/red] {cmd}  (type [yellow]help[/yellow] for commands)")


def interactive_mode():
    print_banner()
    console.print(HELP_TEXT)
    console.print()

    import shlex
    while True:
        try:
            raw = console.input("[bold cyan]bbs>[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye. Drop your carrier.[/dim]")
            break
        if not raw:
            continue
        try:
            args = shlex.split(raw)
        except ValueError as e:
            console.print(f"[red]Parse error:[/red] {e}")
            continue
        dispatch(args)


# -- entry point ---------------------------------------------------------------

def main():
    init_db()

    if len(sys.argv) < 2:
        # No arguments -> interactive mode
        interactive_mode()
        return

    dispatch(sys.argv[1:])


if __name__ == "__main__":
    main()
