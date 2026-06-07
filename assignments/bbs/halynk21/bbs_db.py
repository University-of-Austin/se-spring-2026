#!/usr/bin/env python3
"""
bbs_db.py — Bulletin Board System · SQLite Edition (Gold Tier)

GOLD FEATURES
─────────────
  • Rich terminal UI   — ASCII art banner, colour themes, styled tables
  • Interactive shell  — persistent login session with readline history,
                         the `bbs [user]>` prompt keeps you "logged in"
  • Boards / Topics    — posts belong to named boards; create your own
  • Threaded replies   — reply to any post by ID; threads shown indented
  • User profiles      — join date, post count, editable bio
  • Post reactions     — emoji reactions (👍 ❤️ 😂 🔥 …) per post
  • Private messages   — direct messages between users, with an inbox
  • Leaderboard        — top-N most active users
  • Trending posts     — score = reactions×3 + replies×2 + 1, last 7 days

ONE-SHOT USAGE (backwards-compatible with Part A)
──────────────────────────────────────────────────
  python bbs_db.py post   <username> <message>
  python bbs_db.py read   [board]
  python bbs_db.py users
  python bbs_db.py search <keyword>

  # Gold extras (one-shot)
  python bbs_db.py boards
  python bbs_db.py thread    <post_id>
  python bbs_db.py reply     <post_id> <username> <message>
  python bbs_db.py edit      <post_id> <username> <new message>
  python bbs_db.py delete    <post_id> <username>
  python bbs_db.py pin       <post_id> <admin_username>
  python bbs_db.py unpin     <post_id> <admin_username>
  python bbs_db.py profile   <username>
  python bbs_db.py leaderboard
  python bbs_db.py trending
  python bbs_db.py react     <post_id> <emoji> <username>
  python bbs_db.py msg       <sender>  <recipient> <message>
  python bbs_db.py inbox     <username>

INTERACTIVE MODE
────────────────
  python bbs_db.py          # no arguments → interactive login
  python bbs_db.py -i       # explicit flag
"""

from __future__ import annotations

import sys
import os
import re
import json
import random
import time
from datetime import datetime, timedelta, date as _date

# ── readline for command history (graceful fallback on Windows) ──────────────
try:
    import readline  # noqa: F401  (side-effect: enables arrow-key history)
    readline.set_history_length(200)
except ImportError:
    pass

from sqlalchemy import text

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.theme import Theme
    from rich.prompt import Prompt
    from rich import box
    from rich.padding import Padding
    from rich.columns import Columns

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from db import engine, init_db, init_econ

# ── Colour theme ─────────────────────────────────────────────────────────────
if RICH_AVAILABLE:
    THEME = Theme(
        {
            "banner":    "bold cyan",
            "info":      "dim cyan",
            "success":   "bold green",
            "warn":      "bold yellow",
            "error":     "bold red",
            "prompt":    "bold magenta",
            "username":  "bold bright_blue",
            "board":     "bold bright_yellow",
            "timestamp": "dim white",
            "post_id":   "dim green",
            "reaction":  "bold bright_magenta",
            "heading":   "bold underline white",
        }
    )
    console = Console(theme=THEME, highlight=False)
else:
    # Thin shim so the rest of the code works without rich
    class _FallbackConsole:
        def print(self, *args, **kwargs):
            # Strip rich markup-ish brackets
            text = " ".join(str(a) for a in args)
            import re
            text = re.sub(r"\[/?[^\]]*\]", "", text)
            print(text)
        def rule(self, title=""):
            print("─" * 60 + ("  " + title if title else ""))
        def clear(self):
            os.system("clear" if os.name != "nt" else "cls")
    console = _FallbackConsole()

# ── ASCII banner ──────────────────────────────────────────────────────────────
BANNER = r"""
[banner] ██████╗ ██████╗ ███████╗
[banner]██╔══██╗██╔══██╗██╔════╝  Bulletin Board System
[banner]██████╔╝██████╔╝███████╗  SQLite Edition  v2.0
[banner]██╔══██╗██╔══██╗╚════██║  ─────────────────────
[banner]██████╔╝██████╔╝███████║  Terminal-native · 2026
[banner]╚═════╝ ╚═════╝ ╚══════╝[/banner]"""

HELP_TEXT = r"""\
[heading]Available commands[/heading]

[board]POSTING[/board]
  post   <message>                  Post to current board
  post   <board> <message>          Post to a specific board
  reply  <post_id> <message>        Reply to a post
  edit   <post_id> <new message>    Edit your own post
  delete <post_id>                  Delete your own post

[board]READING[/board]
  read   \[board] \[--limit N] \[--page N]   Read posts with pagination
  thread <post_id>                  Show full thread
  boards                            List all boards
  use    <board>                    Switch active board
  search <keyword>                  Search posts and usernames

[board]SOCIAL[/board]
  react    <post_id> <emoji>        React to a post  (e.g. 👍 ❤️ 🔥)
  unreact  <post_id> <emoji>        Remove your reaction
  msg      <username> <message>     Send a private message
  inbox                             Read your inbox

[board]PROFILES[/board]
  users                             List all users
  profile  \[username]              View a user's profile
  bio      <text>                   Set your bio

[board]MODERATION[/board]
  pin      <post_id>                Pin a post to the top (admin/mod only)
  unpin    <post_id>                Unpin a post (admin/mod only)
  promote  <username>               Grant mod privileges (admin/mod only)
  makeadmin <username>              Grant admin rights (admin or first-run only)

[board]SUBSCRIPTIONS[/board]
  subscribe    <board>              Subscribe to a board
  unsubscribe  <board>              Unsubscribe from a board
  subscriptions                     List your subscriptions
  digest                            New posts since last visit across subscribed boards

[board]ECONOMY[/board]
  fish \[cast N]                    Catch a fish (or N at once)
  inventory                         View your fish + liquidation value
  sell <fish|all>                   Sell fish at today's market price
  buy  <fish> <qty>                 Buy fish to speculate
  market                            Today's prices with trend indicators
  gamble <amount|all|half>          Try your luck at the slots
  balance                           Check your wallet
  give   <username> <amount>        Send money to a player
  history \[N]                      Last N transactions (default 10)
  stats  \[username]                Lifetime economy breakdown
  ecoleaderboard \[--sort earned]   Richest players

[board]STATS[/board]
  leaderboard                       Most active users
  trending                          Hot posts (last 7 days)

[board]SESSION[/board]
  export \[file]                    Dump all posts to JSON (default: bbs_export.json)
  clear                             Clear the screen
  help                              Show this help
  logout / exit / quit              Leave the BBS
"""


# ═══════════════════════════════════════════════════════════════════════════════
# LOW-LEVEL DB HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def fmt_ts(ts: str) -> str:
    """ISO timestamp → human-friendly 'YYYY-MM-DD HH:MM'."""
    return ts[:16].replace("T", " ")


def get_or_create_user(conn, username: str) -> tuple[int, bool]:
    """Return (user_id, created:bool). Race-safe via INSERT OR IGNORE."""
    result = conn.execute(
        text("INSERT OR IGNORE INTO users (username, bio, created_at) VALUES (:u, '', :ts)"),
        {"u": username, "ts": now_iso()},
    )
    created = result.rowcount == 1
    conn.commit()
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()
    return row[0], created


def get_board_id(conn, name: str) -> int | None:
    """Return board id by name, or None if not found."""
    row = conn.execute(
        text("SELECT id FROM boards WHERE name = :n"),
        {"n": name},
    ).fetchone()
    return row[0] if row else None


def get_or_create_board(conn, name: str) -> int:
    bid = get_board_id(conn, name)
    if bid is not None:
        return bid
    result = conn.execute(
        text("INSERT INTO boards (name, description, created_at) VALUES (:n, '', :ts)"),
        {"n": name, "ts": now_iso()},
    )
    conn.commit()
    return result.lastrowid


def reaction_summary(conn, post_id: int) -> str:
    """Return a compact string like '👍 3  ❤️ 1' for a post."""
    rows = conn.execute(
        text("""
            SELECT reaction, COUNT(*) as cnt
            FROM reactions
            WHERE post_id = :pid
            GROUP BY reaction
            ORDER BY cnt DESC
        """),
        {"pid": post_id},
    ).fetchall()
    if not rows:
        return ""
    return "  ".join(f"{r} {c}" for r, c in rows)


def scan_mentions(conn, post_id: int, message: str) -> None:
    """Find @username patterns in message and insert mention rows."""
    for uname in set(re.findall(r'@(\w+)', message)):
        row = conn.execute(
            text("SELECT id FROM users WHERE username = :u"),
            {"u": uname},
        ).fetchone()
        if row:
            conn.execute(
                text("""
                    INSERT OR IGNORE INTO mentions (post_id, mentioned_user_id, notified)
                    VALUES (:pid, :uid, 0)
                """),
                {"pid": post_id, "uid": row[0]},
            )
    conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# COMMANDS (each function takes an open connection + args)
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_post(conn, username: str, message: str, board_name: str = "general",
             parent_id: int | None = None) -> None:
    if not message.strip():
        console.print("[error]Message cannot be empty.[/error]")
        return
    user_id, created = get_or_create_user(conn, username)
    board_id = get_or_create_board(conn, board_name)

    result = conn.execute(
        text("""
            INSERT INTO posts (user_id, board_id, parent_id, message, timestamp)
            VALUES (:uid, :bid, :pid, :msg, :ts)
        """),
        {
            "uid": user_id, "bid": board_id,
            "pid": parent_id, "msg": message, "ts": now_iso(),
        },
    )
    conn.commit()
    post_id = result.lastrowid
    scan_mentions(conn, post_id, message)
    if created:
        console.print(f"[success]Account created for [username]{username}[/username]. Posted as #{post_id}.[/success]")
    else:
        console.print(f"[success]Posted as [post_id]#{post_id}[/post_id] to [board]{board_name}[/board].[/success]")


def cmd_read(conn, board_name: str | None = None, limit: int = 30, page: int = 1) -> None:
    """Read top-level posts with pagination. Pinned posts always appear first."""
    offset = (page - 1) * limit
    _SELECT = """
        SELECT p.id, u.username, b.name, p.message, p.timestamp, p.edited_at, p.pinned
        FROM posts p
        JOIN users  u ON p.user_id  = u.id
        LEFT JOIN boards b ON p.board_id = b.id
    """

    if board_name:
        bid = get_board_id(conn, board_name)
        if bid is None:
            console.print(f"[error]Board '[board]{board_name}[/board]' not found.[/error]")
            return
        total = conn.execute(
            text("SELECT COUNT(*) FROM posts p WHERE p.board_id = :bid AND p.parent_id IS NULL"),
            {"bid": bid},
        ).scalar()
        total_pages = max(1, (total + limit - 1) // limit)
        rows = conn.execute(
            text(_SELECT + "WHERE p.board_id = :bid AND p.parent_id IS NULL"
                           " ORDER BY p.pinned DESC, p.timestamp DESC LIMIT :limit OFFSET :offset"),
            {"bid": bid, "limit": limit, "offset": offset},
        ).fetchall()
    else:
        total = conn.execute(
            text("SELECT COUNT(*) FROM posts p WHERE p.parent_id IS NULL"),
        ).scalar()
        total_pages = max(1, (total + limit - 1) // limit)
        rows = conn.execute(
            text(_SELECT + "WHERE p.parent_id IS NULL"
                           " ORDER BY p.pinned DESC, p.timestamp DESC LIMIT :limit OFFSET :offset"),
            {"limit": limit, "offset": offset},
        ).fetchall()

    if not rows:
        msg = f"No posts on page {page}." if page > 1 else "No posts yet."
        console.print(f"[info]{msg}[/info]")
        return

    page_info = f"Page {page}/{total_pages}  ·  {total} post{'s' if total != 1 else ''}"

    if RICH_AVAILABLE:
        tbl = Table(title=page_info, box=box.SIMPLE_HEAD, show_header=True,
                    header_style="heading", expand=True)
        tbl.add_column("#",       style="post_id",   width=5,  no_wrap=True)
        tbl.add_column("Board",   style="board",     width=10, no_wrap=True)
        tbl.add_column("User",    style="username",  width=12, no_wrap=True)
        tbl.add_column("Message", ratio=1)
        tbl.add_column("When",    style="timestamp", width=16, no_wrap=True)

        for pid, uname, bname, msg, ts, edited_at, pinned in rows:
            rxn = reaction_summary(conn, pid)
            reply_count = conn.execute(
                text("SELECT COUNT(*) FROM posts WHERE parent_id = :pid"),
                {"pid": pid},
            ).scalar()
            msg_display = ("📌 " if pinned else "") + msg
            footer = ""
            if edited_at:
                footer += f"\n[dim](edited {fmt_ts(edited_at)})[/dim]"
            if rxn:
                footer += f"\n[reaction]{rxn}[/reaction]"
            if reply_count:
                footer += f"\n[info]↩ {reply_count} repl{'y' if reply_count==1 else 'ies'}[/info]"
            tbl.add_row(str(pid), bname or "?", uname, msg_display + footer, fmt_ts(ts))
        console.print(tbl)
        if total_pages > 1:
            console.print(
                f"[info]  ← read --page {max(1, page-1)}   "
                f"read --page {min(total_pages, page+1)} →[/info]"
            )
    else:
        print(f"--- {page_info} ---")
        for pid, uname, bname, msg, ts, edited_at, pinned in rows:
            pin_marker  = "📌 " if pinned else ""
            edit_marker = " (edited)" if edited_at else ""
            print(f"[{fmt_ts(ts)}] #{pid} ({bname}) {pin_marker}{uname}: {msg}{edit_marker}")
        if total_pages > 1:
            print(f"--- page {page} of {total_pages} ---")


def cmd_users(conn) -> None:
    rows = conn.execute(
        text("""
            SELECT u.username, COUNT(p.id) as posts, u.created_at
            FROM users u
            LEFT JOIN posts p ON p.user_id = u.id
            GROUP BY u.id
            ORDER BY u.username ASC
        """)
    ).fetchall()

    if not rows:
        console.print("[info]No users yet.[/info]")
        return

    if RICH_AVAILABLE:
        tbl = Table(box=box.SIMPLE_HEAD, header_style="heading")
        tbl.add_column("Username",  style="username")
        tbl.add_column("Posts",     justify="right")
        tbl.add_column("Joined",    style="timestamp")
        for uname, posts, joined in rows:
            tbl.add_row(uname, str(posts), fmt_ts(joined))
        console.print(tbl)
    else:
        for uname, posts, _ in rows:
            print(f"{uname}  ({posts} posts)")


def cmd_search(conn, keyword: str) -> None:
    """
    SQL LIKE query — the database does the scan so we never load the
    entire posts table into Python memory.  At a million rows this is
    still fast if the message column is indexed.
    """
    rows = conn.execute(
        text("""
            SELECT p.id, u.username, b.name, p.message, p.timestamp
            FROM posts p
            JOIN users  u ON p.user_id  = u.id
            LEFT JOIN boards b ON p.board_id = b.id
            WHERE p.message LIKE :kw ESCAPE '!' OR u.username LIKE :kw ESCAPE '!'
            ORDER BY p.timestamp DESC
            LIMIT 50
        """),
        {"kw": "%" + keyword.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%"},
    ).fetchall()

    if not rows:
        console.print("[info]No results found.[/info]")
        return

    if RICH_AVAILABLE:
        tbl = Table(box=box.SIMPLE_HEAD, header_style="heading", expand=True)
        tbl.add_column("#",       style="post_id",   width=5)
        tbl.add_column("Board",   style="board",     width=10)
        tbl.add_column("User",    style="username",  width=12)
        tbl.add_column("Message", ratio=1)
        tbl.add_column("When",    style="timestamp", width=16)
        for pid, uname, bname, msg, ts in rows:
            # Highlight the matched keyword
            highlighted = msg.replace(keyword, f"[bold yellow]{keyword}[/bold yellow]")
            tbl.add_row(str(pid), bname or "?", uname, highlighted, fmt_ts(ts))
        console.print(tbl)
    else:
        for pid, uname, bname, msg, ts in rows:
            print(f"[{fmt_ts(ts)}] #{pid} ({bname}) {uname}: {msg}")


def cmd_boards(conn) -> None:
    rows = conn.execute(
        text("""
            SELECT b.name, b.description,
                   COUNT(p.id) as post_count,
                   b.created_at
            FROM boards b
            LEFT JOIN posts p ON p.board_id = b.id AND p.parent_id IS NULL
            GROUP BY b.id
            ORDER BY post_count DESC
        """)
    ).fetchall()

    if RICH_AVAILABLE:
        tbl = Table(box=box.SIMPLE_HEAD, header_style="heading")
        tbl.add_column("Board",       style="board")
        tbl.add_column("Description")
        tbl.add_column("Posts", justify="right")
        tbl.add_column("Created", style="timestamp")
        for name, desc, count, created in rows:
            tbl.add_row(name, desc or "—", str(count), fmt_ts(created))
        console.print(tbl)
    else:
        for name, desc, count, _ in rows:
            print(f"{name}  ({count} posts)  {desc}")


def cmd_thread(conn, post_id: int) -> None:
    """Display a post and all its replies, indented recursively."""

    def fetch_post(pid: int):
        return conn.execute(
            text("""
                SELECT p.id, u.username, b.name, p.message, p.timestamp, p.parent_id
                FROM posts p
                JOIN users u ON p.user_id = u.id
                LEFT JOIN boards b ON p.board_id = b.id
                WHERE p.id = :pid
            """),
            {"pid": pid},
        ).fetchone()

    def print_subtree(pid: int, indent: int = 0):
        row = fetch_post(pid)
        if not row:
            return
        pid2, uname, bname, msg, ts, parent = row
        prefix = "  " * indent
        rxn = reaction_summary(conn, pid2)

        if RICH_AVAILABLE:
            indent_str = "  " * indent
            connector = "└─ " if indent > 0 else ""
            console.print(
                f"{indent_str}[post_id]{connector}#{pid2}[/post_id] "
                f"[username]{uname}[/username]  "
                f"[timestamp]{fmt_ts(ts)}[/timestamp]\n"
                f"{indent_str}   {msg}"
                + (f"\n{indent_str}   [reaction]{rxn}[/reaction]" if rxn else "")
            )
        else:
            print(f"{prefix}#{pid2} {uname} [{fmt_ts(ts)}]: {msg}")
            if rxn:
                print(f"{prefix}   {rxn}")

        # Fetch direct children
        children = conn.execute(
            text("SELECT id FROM posts WHERE parent_id = :pid ORDER BY timestamp ASC"),
            {"pid": pid2},
        ).fetchall()
        for (child_id,) in children:
            print_subtree(child_id, indent + 1)

    print_subtree(post_id)


def cmd_reply(conn, username: str, parent_id: int, message: str) -> None:
    parent = conn.execute(
        text("SELECT id, board_id FROM posts WHERE id = :pid"),
        {"pid": parent_id},
    ).fetchone()
    if not parent:
        console.print(f"[error]Post #{parent_id} not found.[/error]")
        return
    _, board_id = parent
    # Resolve board name
    board_row = conn.execute(
        text("SELECT name FROM boards WHERE id = :bid"),
        {"bid": board_id},
    ).fetchone()
    board_name = board_row[0] if board_row else "general"
    cmd_post(conn, username, message, board_name, parent_id=parent_id)


def cmd_react(conn, username: str, post_id: int, reaction: str) -> None:
    user_id, _ = get_or_create_user(conn, username)
    # Check post exists
    if not conn.execute(text("SELECT id FROM posts WHERE id = :pid"), {"pid": post_id}).fetchone():
        console.print(f"[error]Post #{post_id} not found.[/error]")
        return
    try:
        conn.execute(
            text("""
                INSERT OR IGNORE INTO reactions (post_id, user_id, reaction, created_at)
                VALUES (:pid, :uid, :r, :ts)
            """),
            {"pid": post_id, "uid": user_id, "r": reaction, "ts": now_iso()},
        )
        conn.commit()
        console.print(f"[reaction]{reaction}[/reaction] [success]added to post #{post_id}.[/success]")
    except Exception as e:
        console.print(f"[error]{e}[/error]")


def cmd_unreact(conn, username: str, post_id: int, reaction: str) -> None:
    user_id, _ = get_or_create_user(conn, username)
    conn.execute(
        text("""
            DELETE FROM reactions
            WHERE post_id = :pid AND user_id = :uid AND reaction = :r
        """),
        {"pid": post_id, "uid": user_id, "r": reaction},
    )
    conn.commit()
    console.print(f"[reaction]{reaction}[/reaction] [info]removed from post #{post_id}.[/info]")


def cmd_edit(conn, username: str, post_id: int, new_message: str) -> None:
    row = conn.execute(
        text("SELECT p.id, u.username FROM posts p JOIN users u ON p.user_id = u.id WHERE p.id = :pid"),
        {"pid": post_id},
    ).fetchone()
    if not row:
        console.print(f"[error]Post #{post_id} not found.[/error]")
        return
    if row[1] != username:
        console.print("[error]You can only edit your own posts.[/error]")
        return
    conn.execute(
        text("UPDATE posts SET message = :msg, edited_at = :ts WHERE id = :pid"),
        {"msg": new_message, "ts": now_iso(), "pid": post_id},
    )
    conn.commit()
    scan_mentions(conn, post_id, new_message)
    console.print(f"[success]Post #{post_id} updated.[/success]")


def cmd_delete(conn, username: str, post_id: int) -> None:
    row = conn.execute(
        text("SELECT p.id, u.username FROM posts p JOIN users u ON p.user_id = u.id WHERE p.id = :pid"),
        {"pid": post_id},
    ).fetchone()
    if not row:
        console.print(f"[error]Post #{post_id} not found.[/error]")
        return
    priv = conn.execute(
        text("SELECT is_admin, is_mod FROM users WHERE username = :u"), {"u": username}
    ).fetchone()
    is_privileged = priv and (priv[0] or priv[1])
    if row[1] != username and not is_privileged:
        console.print("[error]You can only delete your own posts.[/error]")
        return
    conn.execute(text("DELETE FROM reactions WHERE post_id = :pid"), {"pid": post_id})
    conn.execute(text("DELETE FROM mentions  WHERE post_id = :pid"), {"pid": post_id})
    # Promote direct replies to top-level rather than leaving them stranded
    conn.execute(text("UPDATE posts SET parent_id = NULL WHERE parent_id = :pid"), {"pid": post_id})
    conn.execute(text("DELETE FROM posts     WHERE id      = :pid"), {"pid": post_id})
    conn.commit()
    console.print(f"[success]Post #{post_id} deleted.[/success]")


def cmd_pin(conn, username: str, post_id: int, pinned: bool = True) -> None:
    row = conn.execute(
        text("SELECT is_admin, is_mod FROM users WHERE username = :u"), {"u": username}
    ).fetchone()
    if not row or (not row[0] and not row[1]):
        console.print("[error]Only admins and mods can pin posts.[/error]")
        return
    if not conn.execute(text("SELECT id FROM posts WHERE id = :pid"), {"pid": post_id}).fetchone():
        console.print(f"[error]Post #{post_id} not found.[/error]")
        return
    conn.execute(
        text("UPDATE posts SET pinned = :v WHERE id = :pid"),
        {"v": 1 if pinned else 0, "pid": post_id},
    )
    conn.commit()
    action = "pinned" if pinned else "unpinned"
    console.print(f"[success]Post #{post_id} {action}.[/success]")


def cmd_makeadmin(conn, requester: str, target: str) -> None:
    admin_count = conn.execute(text("SELECT COUNT(*) FROM users WHERE is_admin = 1")).scalar()
    req_row = conn.execute(
        text("SELECT is_admin FROM users WHERE username = :u"), {"u": requester}
    ).fetchone()
    if admin_count > 0 and (not req_row or not req_row[0]):
        console.print("[error]Only admins can promote other users.[/error]")
        return
    result = conn.execute(
        text("UPDATE users SET is_admin = 1 WHERE username = :u"), {"u": target}
    )
    if result.rowcount == 0:
        console.print(f"[error]User '[username]{target}[/username]' not found.[/error]")
        return
    conn.commit()
    console.print(f"[success][username]{target}[/username] is now an admin.[/success]")


def cmd_profile(conn, username: str) -> None:
    row = conn.execute(
        text("""
            SELECT u.id, u.username, u.bio, u.created_at,
                   COUNT(p.id) as post_count
            FROM users u
            LEFT JOIN posts p ON p.user_id = u.id
            WHERE u.username = :u
            GROUP BY u.id
        """),
        {"u": username},
    ).fetchone()
    if not row:
        console.print(f"[error]User '[username]{username}[/username]' not found.[/error]")
        return
    uid, uname, bio, joined, posts = row

    # Recent posts
    recent = conn.execute(
        text("""
            SELECT p.id, b.name, p.message, p.timestamp
            FROM posts p
            LEFT JOIN boards b ON p.board_id = b.id
            WHERE p.user_id = :uid AND p.parent_id IS NULL
            ORDER BY p.timestamp DESC LIMIT 5
        """),
        {"uid": uid},
    ).fetchall()

    balance, earned, lost, peak = _get_wallet(conn, uid)

    if RICH_AVAILABLE:
        lines = Text()
        lines.append(f"  Username : ", style="dim")
        lines.append(f"{uname}\n", style="username")
        lines.append(f"  Bio      : ", style="dim")
        lines.append(f"{bio or '(none)'}\n")
        lines.append(f"  Joined   : ", style="dim")
        lines.append(f"{fmt_ts(joined)}\n", style="timestamp")
        lines.append(f"  Posts    : ", style="dim")
        lines.append(f"{posts}\n")
        lines.append(f"\n  Balance  : ", style="dim")
        lines.append(f"${balance:,}\n", style="bold green")
        lines.append(f"  Peak     : ", style="dim")
        lines.append(f"${peak:,}\n")
        lines.append(f"  Earned   : ", style="dim")
        lines.append(f"${earned:,}\n", style="green")
        lines.append(f"  Lost     : ", style="dim")
        lines.append(f"${lost:,}\n", style="red")
        console.print(Panel(lines, title=f"[username]{uname}[/username]'s Profile", border_style="cyan"))

        if recent:
            tbl = Table(box=box.SIMPLE, header_style="heading", show_header=True)
            tbl.add_column("#",    style="post_id", width=5)
            tbl.add_column("Board", style="board",  width=10)
            tbl.add_column("Message", ratio=1)
            tbl.add_column("When", style="timestamp", width=16)
            for pid, bname, msg, ts in recent:
                tbl.add_row(str(pid), bname or "?", msg[:80], fmt_ts(ts))
            console.print(Padding(tbl, (0, 2)))
    else:
        print(f"Username : {uname}")
        print(f"Bio      : {bio or '(none)'}")
        print(f"Joined   : {fmt_ts(joined)}")
        print(f"Posts    : {posts}")
        print(f"Balance  : ${balance:,}  (peak: ${peak:,})  Earned: ${earned:,}  Lost: ${lost:,}")


def cmd_set_bio(conn, username: str, bio: str) -> None:
    user_id, _ = get_or_create_user(conn, username)
    conn.execute(
        text("UPDATE users SET bio = :bio WHERE id = :uid"),
        {"bio": bio, "uid": user_id},
    )
    conn.commit()
    console.print("[success]Bio updated.[/success]")


def cmd_msg(conn, sender: str, recipient: str, message: str) -> None:
    sender_id, _ = get_or_create_user(conn, sender)
    recip_row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"),
        {"u": recipient},
    ).fetchone()
    if not recip_row:
        console.print(f"[error]User '[username]{recipient}[/username]' not found.[/error]")
        return
    conn.execute(
        text("""
            INSERT INTO private_messages
                (sender_id, recipient_id, message, timestamp)
            VALUES (:sid, :rid, :msg, :ts)
        """),
        {"sid": sender_id, "rid": recip_row[0], "msg": message, "ts": now_iso()},
    )
    conn.commit()
    console.print(f"[success]Message sent to [username]{recipient}[/username].[/success]")


def cmd_inbox(conn, username: str) -> None:
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()
    if not row:
        console.print(f"[error]User '[username]{username}[/username]' not found.[/error]")
        return
    uid = row[0]

    msgs = conn.execute(
        text("""
            SELECT pm.id, u.username, pm.message, pm.timestamp, pm.read_at
            FROM private_messages pm
            JOIN users u ON pm.sender_id = u.id
            WHERE pm.recipient_id = :uid
            ORDER BY pm.timestamp DESC
            LIMIT 30
        """),
        {"uid": uid},
    ).fetchall()

    if not msgs:
        console.print("[info]Inbox is empty.[/info]")
        return

    if RICH_AVAILABLE:
        tbl = Table(box=box.SIMPLE_HEAD, header_style="heading")
        tbl.add_column("#",    style="post_id", width=5)
        tbl.add_column("From", style="username", width=14)
        tbl.add_column("Message", ratio=1)
        tbl.add_column("When", style="timestamp", width=16)
        tbl.add_column("", width=4)
        for mid, sender, msg, ts, read_at in msgs:
            new_flag = "" if read_at else "[bold green]NEW[/bold green]"
            tbl.add_row(str(mid), sender, msg, fmt_ts(ts), new_flag)
        console.print(tbl)
    else:
        for mid, sender, msg, ts, read_at in msgs:
            flag = "[NEW] " if not read_at else ""
            print(f"#{mid} {flag}From {sender} [{fmt_ts(ts)}]: {msg}")

    # Mark all as read
    conn.execute(
        text("""
            UPDATE private_messages SET read_at = :ts
            WHERE recipient_id = :uid AND read_at IS NULL
        """),
        {"uid": uid, "ts": now_iso()},
    )
    conn.commit()


def cmd_leaderboard(conn, top: int = 10) -> None:
    rows = conn.execute(
        text("""
            SELECT u.username,
                   COUNT(DISTINCT p.id)          AS posts,
                   (SELECT COUNT(*) FROM reactions r
                    JOIN posts p2 ON r.post_id = p2.id
                    WHERE p2.user_id = u.id)     AS reactions_received,
                   COUNT(DISTINCT pm.id)         AS messages_sent
            FROM users u
            LEFT JOIN posts p             ON p.user_id    = u.id
            LEFT JOIN private_messages pm ON pm.sender_id = u.id
            GROUP BY u.id
            ORDER BY posts DESC, reactions_received DESC
            LIMIT :top
        """),
        {"top": top},
    ).fetchall()

    if not rows:
        console.print("[info]No data yet.[/info]")
        return

    if RICH_AVAILABLE:
        tbl = Table(
            title="🏆  Leaderboard",
            box=box.HEAVY_HEAD,
            header_style="heading",
            show_lines=False,
        )
        tbl.add_column("Rank", justify="right", width=5)
        tbl.add_column("Username",          style="username",  width=16)
        tbl.add_column("Posts",             justify="right")
        tbl.add_column("Reactions received",justify="right")
        tbl.add_column("PMs sent",          justify="right")

        medals = ["🥇", "🥈", "🥉"]
        for i, (uname, posts, rxn, pms) in enumerate(rows):
            rank = medals[i] if i < 3 else str(i + 1)
            tbl.add_row(rank, uname, str(posts), str(rxn), str(pms))
        console.print(tbl)
    else:
        for i, (uname, posts, rxn, pms) in enumerate(rows, 1):
            print(f"{i}. {uname}  {posts} posts  {rxn} reactions")


def cmd_trending(conn, days: int = 7, top: int = 10) -> None:
    """
    Trending score for a top-level post in the last `days` days:
      score = reactions × 3 + replies × 2 + 1

    The +1 ensures every post has a non-zero base score, preventing
    division-by-zero if we ever want to normalise.
    """
    cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
    rows = conn.execute(
        text("""
            SELECT
                p.id,
                u.username,
                b.name                   AS board,
                p.message,
                p.timestamp,
                COUNT(DISTINCT r.id)     AS rxn_count,
                COUNT(DISTINCT rep.id)   AS reply_count,
                (COUNT(DISTINCT r.id) * 3 + COUNT(DISTINCT rep.id) * 2 + 1) AS score
            FROM posts p
            JOIN  users  u   ON p.user_id  = u.id
            LEFT JOIN boards b ON p.board_id = b.id
            LEFT JOIN reactions r   ON r.post_id = p.id AND r.created_at >= :cutoff
            LEFT JOIN posts     rep ON rep.parent_id = p.id AND rep.timestamp >= :cutoff
            WHERE p.parent_id IS NULL
              AND p.timestamp >= :cutoff
            GROUP BY p.id
            ORDER BY score DESC
            LIMIT :top
        """),
        {"cutoff": cutoff, "top": top},
    ).fetchall()

    if not rows:
        console.print(f"[info]No posts in the last {days} day(s).[/info]")
        return

    if RICH_AVAILABLE:
        tbl = Table(
            title=f"🔥  Trending (last {days} days)",
            box=box.HEAVY_HEAD,
            header_style="heading",
            expand=True,
        )
        tbl.add_column("#",      style="post_id",   width=5)
        tbl.add_column("Board",  style="board",     width=10)
        tbl.add_column("User",   style="username",  width=12)
        tbl.add_column("Message",ratio=1)
        tbl.add_column("🔥",     justify="right",   width=6)
        tbl.add_column("💬",     justify="right",   width=5)
        tbl.add_column("Score",  justify="right",   width=7)
        for pid, uname, board, msg, ts, rxn, replies, score in rows:
            tbl.add_row(
                str(pid), board or "?", uname,
                msg[:90], str(rxn), str(replies), str(score),
            )
        console.print(tbl)
    else:
        for pid, uname, board, msg, ts, rxn, replies, score in rows:
            print(f"#{pid} score={score}  {uname}: {msg[:60]}")


def cmd_subscribe(conn, username: str, board_name: str, subscribe: bool = True) -> None:
    user_id, _ = get_or_create_user(conn, username)
    bid = get_board_id(conn, board_name)
    if bid is None:
        console.print(f"[error]Board '[board]{board_name}[/board]' not found.[/error]")
        return
    if subscribe:
        conn.execute(
            text("""
                INSERT OR IGNORE INTO subscriptions (user_id, board_id, created_at)
                VALUES (:uid, :bid, :ts)
            """),
            {"uid": user_id, "bid": bid, "ts": now_iso()},
        )
        conn.commit()
        console.print(f"[success]Subscribed to [board]{board_name}[/board].[/success]")
    else:
        conn.execute(
            text("DELETE FROM subscriptions WHERE user_id = :uid AND board_id = :bid"),
            {"uid": user_id, "bid": bid},
        )
        conn.commit()
        console.print(f"[info]Unsubscribed from [board]{board_name}[/board].[/info]")


def cmd_digest(conn, username: str) -> None:
    """Show all posts since the user's last digest across their subscribed boards."""
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"), {"u": username}
    ).fetchone()
    if not row:
        console.print(f"[error]User '[username]{username}[/username]' not found.[/error]")
        return
    user_id = row[0]

    subs = conn.execute(
        text("""
            SELECT s.id, b.name, s.last_digest_at
            FROM subscriptions s
            JOIN boards b ON s.board_id = b.id
            WHERE s.user_id = :uid
            ORDER BY b.name ASC
        """),
        {"uid": user_id},
    ).fetchall()

    if not subs:
        console.print(
            "[info]No subscriptions yet.  "
            "Use [bold]subscribe <board>[/bold] to follow a board.[/info]"
        )
        return

    now = now_iso()
    total_new = 0

    _DIGEST_SQL_ALL = """
        SELECT p.id, u.username, p.message, p.timestamp, p.edited_at
        FROM posts p
        JOIN users  u ON p.user_id  = u.id
        JOIN boards b ON p.board_id = b.id
        WHERE b.name = :board AND p.parent_id IS NULL
        ORDER BY p.timestamp ASC
    """
    _DIGEST_SQL_SINCE = """
        SELECT p.id, u.username, p.message, p.timestamp, p.edited_at
        FROM posts p
        JOIN users  u ON p.user_id  = u.id
        JOIN boards b ON p.board_id = b.id
        WHERE b.name = :board AND p.parent_id IS NULL AND p.timestamp > :since
        ORDER BY p.timestamp ASC
    """

    for sub_id, board_name, last_digest_at in subs:
        if last_digest_at:
            posts = conn.execute(
                text(_DIGEST_SQL_SINCE), {"board": board_name, "since": last_digest_at}
            ).fetchall()
        else:
            posts = conn.execute(
                text(_DIGEST_SQL_ALL), {"board": board_name}
            ).fetchall()

        if not posts:
            continue

        total_new += len(posts)

        if RICH_AVAILABLE:
            since_label = f"since {fmt_ts(last_digest_at)}" if last_digest_at else "all posts"
            tbl = Table(
                title=f"[board]{board_name}[/board]  ({since_label})",
                box=box.SIMPLE_HEAD, header_style="heading", expand=True,
            )
            tbl.add_column("#",       style="post_id",  width=5,  no_wrap=True)
            tbl.add_column("User",    style="username", width=12, no_wrap=True)
            tbl.add_column("Message", ratio=1)
            tbl.add_column("When",    style="timestamp", width=16, no_wrap=True)
            for pid, uname, msg, ts, edited_at in posts:
                suffix = " [dim](edited)[/dim]" if edited_at else ""
                tbl.add_row(str(pid), uname, msg + suffix, fmt_ts(ts))
            console.print(tbl)
        else:
            print(f"\n=== {board_name} ===")
            for pid, uname, msg, ts, edited_at in posts:
                edit_marker = " (edited)" if edited_at else ""
                print(f"  [{fmt_ts(ts)}] #{pid} {uname}: {msg}{edit_marker}")

        # Advance the watermark for this board
        conn.execute(
            text("UPDATE subscriptions SET last_digest_at = :ts WHERE id = :sid"),
            {"ts": now, "sid": sub_id},
        )

    conn.commit()

    if total_new == 0:
        console.print("[info]No new posts since your last digest.[/info]")
    else:
        console.print(f"\n[success]{total_new} new post(s) across {len(subs)} subscribed board(s).[/success]")


def cmd_subscriptions(conn, username: str) -> None:
    """List the boards the user is subscribed to."""
    row = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username}).fetchone()
    if not row:
        return
    user_id = row[0]
    subs = conn.execute(
        text("""
            SELECT b.name, s.created_at, s.last_digest_at
            FROM subscriptions s
            JOIN boards b ON s.board_id = b.id
            WHERE s.user_id = :uid
            ORDER BY b.name ASC
        """),
        {"uid": user_id},
    ).fetchall()

    if not subs:
        console.print("[info]No subscriptions.[/info]")
        return

    if RICH_AVAILABLE:
        tbl = Table(box=box.SIMPLE_HEAD, header_style="heading")
        tbl.add_column("Board",       style="board")
        tbl.add_column("Subscribed",  style="timestamp")
        tbl.add_column("Last digest", style="timestamp")
        for bname, created, last_digest in subs:
            tbl.add_row(bname, fmt_ts(created), fmt_ts(last_digest) if last_digest else "never")
        console.print(tbl)
    else:
        for bname, created, last_digest in subs:
            last = fmt_ts(last_digest) if last_digest else "never"
            print(f"{bname}  (subscribed {fmt_ts(created)}, last digest {last})")


# ═══════════════════════════════════════════════════════════════════════════════
# ECONOMY — FISH CATALOGUE, HELPERS, AND COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

FISH = [
    {"name": "Sardine",        "emoji": "🐟", "base": 5,    "weight": 40},
    {"name": "Mackerel",       "emoji": "🐠", "base": 15,   "weight": 25},
    {"name": "Trout",          "emoji": "🎣", "base": 30,   "weight": 15},
    {"name": "Salmon",         "emoji": "🐡", "base": 60,   "weight": 10},
    {"name": "Tuna",           "emoji": "🐟", "base": 120,  "weight": 6},
    {"name": "Swordfish",      "emoji": "⚔️",  "base": 250,  "weight": 3},
    {"name": "Legendary Carp", "emoji": "🏆", "base": 1000, "weight": 1},
]
FISH_BY_NAME = {f["name"].lower(): f for f in FISH}

LOTTERY_OUTCOMES = [
    {"name": "Jackpot",           "mult": 5,  "prob": 2.00,  "emoji": "💎"},
    {"name": "Big win",           "mult": 3,  "prob": 8.00,  "emoji": "⭐"},
    {"name": "Win",               "mult": 2,  "prob": 15.00, "emoji": "🍒"},
    {"name": "Nothing",           "mult": 1,  "prob": 44.99, "emoji": "🍋"},
    {"name": "Lose",              "mult": 0,  "prob": 30.00, "emoji": "💸"},
    {"name": "Catastrophic Loss", "mult": -1, "prob": 0.01,  "emoji": "💀"},
]
REEL_SYMBOLS = ["🍋", "🍒", "⭐", "💎", "💸"]

_price_rng = random.Random()
ANIMATE    = sys.stdout.isatty()


def fish_price(fish: dict) -> int:
    """Today's price — ±10%, deterministic per fish per day."""
    _price_rng.seed(_date.today().isoformat() + fish["name"])
    return max(1, round(fish["base"] * _price_rng.uniform(0.90, 1.10)))


def balance_bar(balance: int, peak: int) -> str:
    peak = max(peak or 1, 1)
    filled = min(20, round(20 * balance / peak))
    bar = "█" * filled + "░" * (20 - filled)
    return f"💰 Balance: [bold green]${balance:,}[/bold green]  {bar}  (peak: ${peak:,})"


def _get_wallet(conn, user_id: int) -> tuple[int, int, int, int]:
    """Return (balance, total_earned, total_lost, peak_balance), defaulting NULLs."""
    row = conn.execute(
        text("""SELECT COALESCE(balance,100), COALESCE(total_earned,0),
                       COALESCE(total_lost,0), COALESCE(peak_balance,100)
                FROM users WHERE id = :uid"""),
        {"uid": user_id},
    ).fetchone()
    return row if row else (100, 0, 0, 100)


def mutate_balance(conn, user_id: int, amount: int, action: str,
                   detail: str = "") -> tuple[int, int]:
    """Apply delta to balance, update stats, log. Returns (new_balance, peak)."""
    balance, earned, lost, peak = _get_wallet(conn, user_id)
    new_balance = max(1, balance + amount)
    actual      = new_balance - balance
    if actual > 0:
        earned += actual
    elif actual < 0:
        lost += abs(actual)
    new_peak = max(peak, new_balance)
    conn.execute(
        text("""UPDATE users SET balance=:b, total_earned=:e,
                total_lost=:l, peak_balance=:p WHERE id=:uid"""),
        {"b": new_balance, "e": earned, "l": lost, "p": new_peak, "uid": user_id},
    )
    conn.execute(
        text("""INSERT INTO econ_log
                (user_id, action, detail, amount, balance_after, timestamp)
                VALUES (:uid,:act,:det,:amt,:bal,:ts)"""),
        {"uid": user_id, "act": action, "det": detail,
         "amt": actual, "bal": new_balance, "ts": now_iso()},
    )
    return new_balance, new_peak


def _log_fish(conn, user_id: int, fish_name: str) -> None:
    balance, *_ = _get_wallet(conn, user_id)
    conn.execute(
        text("""INSERT INTO econ_log
                (user_id, action, detail, amount, balance_after, timestamp)
                VALUES (:uid,'fish',:det,0,:bal,:ts)"""),
        {"uid": user_id, "det": fish_name, "bal": balance, "ts": now_iso()},
    )


# ── Fishing ──────────────────────────────────────────────────────────────────

def cmd_fish(conn, username: str, casts: int = 1) -> None:
    user_id, _ = get_or_create_user(conn, username)
    pop     = [f["name"]   for f in FISH]
    weights = [f["weight"] for f in FISH]
    for _ in range(casts):
        fish_name = random.choices(pop, weights=weights, k=1)[0]
        fish      = FISH_BY_NAME[fish_name.lower()]
        price     = fish_price(fish)
        legendary = fish_name == "Legendary Carp"
        if ANIMATE:
            console.print("\n[info]🎣 Casting line...[/info]")
            time.sleep(0.4)
            console.print("[dim]〰〰〰〰〰〰〰〰[/dim]")
            time.sleep(0.6)
            if legendary:
                time.sleep(0.3)
                console.print("[bold yellow]⚡ THE LINE PULLS HARD...[/bold yellow]")
                time.sleep(0.5)
        conn.execute(
            text("INSERT OR IGNORE INTO inventory (user_id,fish_type,quantity) VALUES (:uid,:ft,0)"),
            {"uid": user_id, "ft": fish_name},
        )
        conn.execute(
            text("UPDATE inventory SET quantity=quantity+1 WHERE user_id=:uid AND fish_type=:ft"),
            {"uid": user_id, "ft": fish_name},
        )
        _log_fish(conn, user_id, fish_name)
        if legendary:
            console.print(f"[bold yellow]🏆 LEGENDARY CARP! (worth ${price:,} today)[/bold yellow]")
        else:
            console.print(
                f"{fish['emoji']} You caught a [bold]{fish_name}[/bold]!  "
                f"(worth [green]${price}[/green] today)"
            )
    conn.commit()
    if casts > 1:
        console.print(f"[info]Cast {casts}×. Check [bold]inventory[/bold] to see your haul.[/info]")


def cmd_inventory(conn, username: str) -> None:
    row = conn.execute(text("SELECT id FROM users WHERE username=:u"), {"u": username}).fetchone()
    if not row:
        console.print("[error]User not found.[/error]"); return
    items = conn.execute(
        text("SELECT fish_type,quantity FROM inventory WHERE user_id=:uid AND quantity>0 ORDER BY fish_type"),
        {"uid": row[0]},
    ).fetchall()
    if not items:
        console.print("[info]Inventory empty. Try [bold]fish[/bold]![/info]"); return
    total = 0
    if RICH_AVAILABLE:
        tbl = Table(box=box.SIMPLE, header_style="heading")
        tbl.add_column("Fish",  style="bold")
        tbl.add_column("Qty",   justify="right")
        tbl.add_column("Price", justify="right", style="green")
        tbl.add_column("Value", justify="right", style="bold green")
        for fname, qty in items:
            fish = FISH_BY_NAME.get(fname.lower())
            if not fish: continue
            p = fish_price(fish); v = p * qty; total += v
            tbl.add_row(f"{fish['emoji']} {fname}", f"×{qty}", f"${p}", f"${v:,}")
        console.print(tbl)
        console.print(f"[bold green]Total liquidation value: ${total:,}[/bold green]")
    else:
        for fname, qty in items:
            fish = FISH_BY_NAME.get(fname.lower())
            if not fish: continue
            p = fish_price(fish); v = p * qty; total += v
            print(f"{fish['emoji']} {fname:<18} ×{qty:<4} ${v:,}")
        print(f"{'─'*35}\nTotal: ${total:,}")


def cmd_sell(conn, username: str, fish_arg: str) -> None:
    row = conn.execute(text("SELECT id FROM users WHERE username=:u"), {"u": username}).fetchone()
    if not row:
        console.print("[error]User not found.[/error]"); return
    user_id = row[0]
    if fish_arg.lower() == "all":
        items = conn.execute(
            text("SELECT fish_type,quantity FROM inventory WHERE user_id=:uid AND quantity>0"),
            {"uid": user_id},
        ).fetchall()
    else:
        matched = next((f for f in FISH if f["name"].lower() == fish_arg.lower()), None)
        if not matched:
            console.print(f"[error]Unknown fish '{fish_arg}'. Check [bold]market[/bold].[/error]"); return
        item = conn.execute(
            text("SELECT fish_type,quantity FROM inventory WHERE user_id=:uid AND fish_type=:ft AND quantity>0"),
            {"uid": user_id, "ft": matched["name"]},
        ).fetchone()
        items = [item] if item else []
    if not items:
        console.print("[info]Nothing to sell.[/info]"); return
    total = 0
    for fname, qty in items:
        fish = FISH_BY_NAME.get(fname.lower())
        if not fish: continue
        p = fish_price(fish); earnings = p * qty; total += earnings
        conn.execute(
            text("UPDATE inventory SET quantity=0 WHERE user_id=:uid AND fish_type=:ft"),
            {"uid": user_id, "ft": fname},
        )
        console.print(f"  Sold {qty}× {fish['emoji']} {fname} @ ${p} = [green]${earnings:,}[/green]")
    new_bal, peak = mutate_balance(conn, user_id, total, "sell", f"sold fish for ${total:,}")
    conn.commit()
    console.print(f"\n[bold green]Total: +${total:,}[/bold green]")
    console.print(balance_bar(new_bal, peak))


def cmd_market(conn) -> None:
    today     = _date.today().isoformat()
    yesterday = (_date.today() - timedelta(days=1)).isoformat()
    now_dt    = datetime.now()
    midnight  = datetime.combine(now_dt.date() + timedelta(days=1), datetime.min.time())
    diff      = midnight - now_dt
    hours, rem = divmod(diff.seconds, 3600); mins = rem // 60
    if RICH_AVAILABLE:
        console.print(f"\n[heading]📊 Fish Market — {today}[/heading]")
        console.print(f"[dim]  Prices reset in: {hours}h {mins}m[/dim]\n")
        tbl = Table(box=box.SIMPLE, show_header=False)
        tbl.add_column("", width=3)
        tbl.add_column("Fish",   style="bold",  width=18)
        tbl.add_column("Price",  justify="right", style="green", width=8)
        tbl.add_column("Change", justify="right", width=8)
        for fish in FISH:
            today_p = fish_price(fish)
            _price_rng.seed(yesterday + fish["name"])
            yest_p  = max(1, round(fish["base"] * _price_rng.uniform(0.90, 1.10)))
            pct     = ((today_p - yest_p) / yest_p) * 100
            if   pct >  0.5: arrow = f"[green]🔺 +{pct:.0f}%[/green]"
            elif pct < -0.5: arrow = f"[red]🔻 {pct:.0f}%[/red]"
            else:             arrow = "[dim]─  ─%[/dim]"
            tbl.add_row(fish["emoji"], fish["name"], f"${today_p}", arrow)
        console.print(tbl)
    else:
        print(f"📊 Fish Market — {today}  (resets in {hours}h {mins}m)")
        for fish in FISH:
            print(f"  {fish['emoji']} {fish['name']:<18} ${fish_price(fish)}")


def cmd_buy(conn, username: str, fish_name_arg: str, quantity: int) -> None:
    row = conn.execute(text("SELECT id FROM users WHERE username=:u"), {"u": username}).fetchone()
    if not row:
        console.print("[error]User not found.[/error]"); return
    user_id = row[0]
    if quantity <= 0:
        console.print("[error]Quantity must be at least 1.[/error]"); return
    fish = next((f for f in FISH if f["name"].lower() == fish_name_arg.lower()), None)
    if not fish:
        console.print(f"[error]Unknown fish '{fish_name_arg}'.[/error]"); return
    price = fish_price(fish); total = price * quantity
    balance, *_ = _get_wallet(conn, user_id)
    if total > balance:
        console.print(f"[error]Need ${total:,}, have ${balance:,}.[/error]"); return
    conn.execute(
        text("INSERT OR IGNORE INTO inventory (user_id,fish_type,quantity) VALUES (:uid,:ft,0)"),
        {"uid": user_id, "ft": fish["name"]},
    )
    conn.execute(
        text("UPDATE inventory SET quantity=quantity+:q WHERE user_id=:uid AND fish_type=:ft"),
        {"q": quantity, "uid": user_id, "ft": fish["name"]},
    )
    new_bal, peak = mutate_balance(conn, user_id, -total, "buy",
                                   f"bought {quantity}× {fish['name']} @ ${price}")
    conn.commit()
    console.print(
        f"[success]Bought {quantity}× {fish['emoji']} {fish['name']} @ ${price} "
        f"= [red]-${total:,}[/red][/success]"
    )
    console.print(balance_bar(new_bal, peak))


# ── Gambling ─────────────────────────────────────────────────────────────────

def cmd_gamble(conn, username: str, amount_arg: str) -> None:
    row = conn.execute(text("SELECT id FROM users WHERE username=:u"), {"u": username}).fetchone()
    if not row:
        console.print("[error]User not found.[/error]"); return
    user_id = row[0]
    balance, *rest_w = _get_wallet(conn, user_id)
    peak = rest_w[2]
    if   amount_arg.lower() == "all":  bet = balance
    elif amount_arg.lower() == "half": bet = max(1, balance // 2)
    else:
        try:   bet = int(amount_arg)
        except ValueError:
            console.print("[error]Usage: gamble <amount|all|half>[/error]"); return
    if bet <= 0:
        console.print("[error]Bet must be positive.[/error]"); return
    if bet > balance:
        console.print(f"[error]Can't bet ${bet:,} — have ${balance:,}.[/error]"); return
    outcome = random.choices(LOTTERY_OUTCOMES, weights=[o["prob"] for o in LOTTERY_OUTCOMES], k=1)[0]
    if ANIMATE:
        for i in range(3):
            syms = random.choices(REEL_SYMBOLS, k=3)
            suffix = "  spinning..." if i < 2 else "  ..."
            console.print(f"🎰 [ {' | '.join(syms)} ]{suffix}")
            time.sleep(0.4)
    console.print("─" * 45)
    if outcome["name"] == "Catastrophic Loss":
        wipe_amount = -(balance - 1)   # reduce to exactly $1
        new_bal, new_peak = mutate_balance(conn, user_id, wipe_amount, "gamble_lose",
                                           "catastrophic loss")
        conn.commit()
        console.print("🎰 [ 💀 | 💀 | 💀 ]")
        console.print("\n[bold red]  ⚠️  CATASTROPHIC LOSS[/bold red]")
        console.print("[red]  Your entire fortune has been wiped.[/red]")
        console.print("[red]  Balance: $1[/red]")
    elif outcome["mult"] == 0:
        new_bal, new_peak = mutate_balance(conn, user_id, -bet, "gamble_lose", f"lost ${bet:,}")
        conn.commit()
        console.print(f"\n    💸 Lost — -${bet:,}")
        console.print(balance_bar(new_bal, new_peak))
    elif outcome["mult"] == 1:
        fresh_bal, _, _, fresh_peak = _get_wallet(conn, user_id)
        console.print(f"\n    🍋 Nothing — kept your ${bet:,}")
        console.print(balance_bar(fresh_bal, fresh_peak))
    else:
        profit = bet * (outcome["mult"] - 1)
        new_bal, new_peak = mutate_balance(conn, user_id, profit, "gamble_win",
                                           f"{outcome['name']} x{outcome['mult']}")
        conn.commit()
        console.print(
            f"\n    {outcome['emoji']} [bold green]{outcome['name']} "
            f"×{outcome['mult']} — ${bet:,} → ${bet * outcome['mult']:,}[/bold green]"
        )
        console.print(balance_bar(new_bal, new_peak))


# ── Economy utilities ─────────────────────────────────────────────────────────

def cmd_balance(conn, username: str) -> None:
    row = conn.execute(text("SELECT id FROM users WHERE username=:u"), {"u": username}).fetchone()
    if not row:
        console.print("[error]User not found.[/error]"); return
    balance, _, _, peak = _get_wallet(conn, row[0])
    console.print(balance_bar(balance, peak))


def cmd_give(conn, sender: str, recipient: str, amount: int) -> None:
    if sender == recipient:
        console.print("[error]Cannot give money to yourself.[/error]"); return
    s_row = conn.execute(text("SELECT id FROM users WHERE username=:u"), {"u": sender}).fetchone()
    r_row = conn.execute(text("SELECT id FROM users WHERE username=:u"), {"u": recipient}).fetchone()
    if not s_row:
        console.print("[error]Sender not found.[/error]"); return
    if not r_row:
        console.print(f"[error]User '[username]{recipient}[/username]' not found.[/error]"); return
    if amount <= 0:
        console.print("[error]Amount must be positive.[/error]"); return
    s_bal, *_ = _get_wallet(conn, s_row[0])
    if amount > s_bal:
        console.print(f"[error]Insufficient funds. Have ${s_bal:,}, need ${amount:,}.[/error]"); return
    new_s, s_peak = mutate_balance(conn, s_row[0], -amount, "give", f"gave ${amount:,} to {recipient}")
    mutate_balance(conn, r_row[0],  amount, "give", f"received ${amount:,} from {sender}")
    conn.commit()
    console.print(f"[success]Sent [green]${amount:,}[/green] to [username]{recipient}[/username].[/success]")
    console.print(balance_bar(new_s, s_peak))


def cmd_history(conn, username: str, n: int = 10) -> None:
    row = conn.execute(text("SELECT id FROM users WHERE username=:u"), {"u": username}).fetchone()
    if not row:
        console.print("[error]User not found.[/error]"); return
    rows = conn.execute(
        text("""SELECT action,detail,amount,balance_after,timestamp
                FROM econ_log WHERE user_id=:uid ORDER BY timestamp DESC LIMIT :n"""),
        {"uid": row[0], "n": n},
    ).fetchall()
    if not rows:
        console.print("[info]No transaction history yet.[/info]"); return
    if RICH_AVAILABLE:
        tbl = Table(box=box.SIMPLE_HEAD, header_style="heading")
        tbl.add_column("Action",  style="bold",      width=14)
        tbl.add_column("Detail",  ratio=1)
        tbl.add_column("Amount",  justify="right",   width=10)
        tbl.add_column("Balance", justify="right",   style="green", width=10)
        tbl.add_column("When",    style="timestamp", width=16)
        for action, detail, amount, bal_after, ts in reversed(rows):
            amt_str = (f"[green]+${amount:,}[/green]" if amount >= 0
                       else f"[red]-${abs(amount):,}[/red]")
            tbl.add_row(action, detail or "─", amt_str, f"${bal_after:,}", fmt_ts(ts))
        console.print(tbl)
    else:
        for action, detail, amount, bal_after, ts in reversed(rows):
            sign = "+" if amount >= 0 else ""
            print(f"[{fmt_ts(ts)}] {action}: {detail or '─'}  {sign}${amount:,}  → ${bal_after:,}")


def cmd_eco_stats(conn, username: str) -> None:
    row = conn.execute(text("SELECT id FROM users WHERE username=:u"), {"u": username}).fetchone()
    if not row:
        console.print(f"[error]User '[username]{username}[/username]' not found.[/error]"); return
    uid = row[0]
    balance, earned, lost, peak = _get_wallet(conn, uid)
    net = earned - lost
    fish_rows = conn.execute(
        text("SELECT detail,COUNT(*) FROM econ_log WHERE user_id=:uid AND action='fish' GROUP BY detail ORDER BY 2 DESC"),
        {"uid": uid},
    ).fetchall()
    gw = conn.execute(
        text("SELECT COUNT(*),COALESCE(SUM(amount),0) FROM econ_log WHERE user_id=:uid AND action='gamble_win'"),
        {"uid": uid},
    ).fetchone()
    gl = conn.execute(
        text("SELECT COUNT(*),COALESCE(SUM(amount),0) FROM econ_log WHERE user_id=:uid AND action='gamble_lose'"),
        {"uid": uid},
    ).fetchone()
    best = conn.execute(
        text("SELECT detail,amount FROM econ_log WHERE user_id=:uid AND action='sell' ORDER BY amount DESC LIMIT 1"),
        {"uid": uid},
    ).fetchone()
    if RICH_AVAILABLE:
        lines = Text()
        lines.append("  Balance  : ", style="dim"); lines.append(f"${balance:,}\n",  style="bold green")
        lines.append("  Peak     : ", style="dim"); lines.append(f"${peak:,}\n",     style="bold")
        lines.append("  Earned   : ", style="dim"); lines.append(f"${earned:,}\n",   style="green")
        lines.append("  Lost     : ", style="dim"); lines.append(f"${lost:,}\n",     style="red")
        lines.append("  Net      : ", style="dim")
        lines.append(f"{'+'if net>=0 else ''}${net:,}\n",
                     style="bold green" if net >= 0 else "bold red")
        lines.append(f"  Gamble   : ", style="dim")
        lines.append(f"{gw[0]} wins / {gl[0]} losses\n")
        if best:
            lines.append("  Best sale: ", style="dim")
            lines.append(f"${best[1]:,}  ({best[0]})\n", style="bold")
        if fish_rows:
            lines.append("\n  Fish caught:\n", style="dim")
            for fname, cnt in fish_rows:
                f = FISH_BY_NAME.get(fname.lower())
                emoji = f["emoji"] if f else "🐟"
                lines.append(f"    {emoji} {fname:<18} ×{cnt}\n")
        console.print(Panel(lines, title=f"[username]{username}[/username]'s Economy", border_style="cyan"))
    else:
        print(f"Balance:${balance:,}  Peak:${peak:,}  Earned:${earned:,}  Lost:${lost:,}  Net:${net:,}")
        print(f"Gamble: {gw[0]} wins / {gl[0]} losses")
        for fname, cnt in fish_rows:
            print(f"  {fname}: ×{cnt}")


_ECO_LEADERBOARD_QUERIES = {
    "earned": """
        SELECT u.username, COALESCE(u.balance,100), COALESCE(u.total_earned,0), COALESCE(u.total_lost,0)
        FROM users u ORDER BY COALESCE(u.total_earned,0) DESC LIMIT 10""",
    "net": """
        SELECT u.username, COALESCE(u.balance,100), COALESCE(u.total_earned,0), COALESCE(u.total_lost,0)
        FROM users u ORDER BY (COALESCE(u.total_earned,0)-COALESCE(u.total_lost,0)) DESC LIMIT 10""",
    "balance": """
        SELECT u.username, COALESCE(u.balance,100), COALESCE(u.total_earned,0), COALESCE(u.total_lost,0)
        FROM users u ORDER BY COALESCE(u.balance,100) DESC LIMIT 10""",
}


def cmd_eco_leaderboard(conn, sort: str = "balance") -> None:
    query = _ECO_LEADERBOARD_QUERIES.get(sort, _ECO_LEADERBOARD_QUERIES["balance"])
    rows = conn.execute(text(query)).fetchall()
    if not rows:
        console.print("[info]No economy data yet.[/info]"); return
    if RICH_AVAILABLE:
        tbl = Table(title="💰  Eco Leaderboard", box=box.HEAVY_HEAD, header_style="heading")
        tbl.add_column("Rank",   justify="right", width=5)
        tbl.add_column("Player", style="username", width=16)
        tbl.add_column("Balance",justify="right", style="bold green")
        tbl.add_column("Earned", justify="right", style="green")
        tbl.add_column("Lost",   justify="right", style="red")
        tbl.add_column("Net",    justify="right")
        medals = ["🥇", "🥈", "🥉"]
        for i, (uname, bal, earned, lost) in enumerate(rows):
            net   = earned - lost
            rank  = medals[i] if i < 3 else str(i + 1)
            trend = "📈" if net >= 0 else "📉"
            tbl.add_row(rank, uname, f"${bal:,}", f"${earned:,}", f"${lost:,}",
                        f"{trend} {'+'if net>=0 else ''}${net:,}")
        console.print(tbl)
    else:
        for i, (uname, bal, earned, lost) in enumerate(rows, 1):
            net = earned - lost
            print(f"{i}. {uname}  ${bal:,}  net: {'+'if net>=0 else ''}${net:,}")


def cmd_export(conn, out_path: str = "bbs_export.json") -> None:
    """Dump all posts to a JSON file in the same format as bbs.json."""
    rows = conn.execute(
        text("""
            SELECT u.username, p.message, p.timestamp, p.edited_at, p.pinned,
                   b.name AS board, p.parent_id, p.id
            FROM posts p
            JOIN users u ON p.user_id = u.id
            LEFT JOIN boards b ON p.board_id = b.id
            ORDER BY p.timestamp ASC
        """)
    ).fetchall()

    posts = [
        {
            "id":        pid,
            "username":  uname,
            "message":   msg,
            "timestamp": ts,
            "board":     board or "general",
            "parent_id": parent_id,
            **({"edited_at": edited_at} if edited_at else {}),
            **({"pinned": True}         if pinned    else {}),
        }
        for uname, msg, ts, edited_at, pinned, board, parent_id, pid in rows
    ]

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(posts, fh, indent=2, ensure_ascii=False)

    console.print(
        f"[success]Exported {len(posts)} post(s) to [bold]{out_path}[/bold].[/success]"
    )


def cmd_promote(conn, requester: str, target: str) -> None:
    """Grant moderator privileges to a user."""
    req_row = conn.execute(
        text("SELECT is_admin, is_mod FROM users WHERE username = :u"), {"u": requester}
    ).fetchone()
    if not req_row or (not req_row[0] and not req_row[1]):
        console.print("[error]Only admins or mods can promote users.[/error]")
        return
    result = conn.execute(
        text("UPDATE users SET is_mod = 1 WHERE username = :u"), {"u": target}
    )
    if result.rowcount == 0:
        console.print(f"[error]User '[username]{target}[/username]' not found.[/error]")
        return
    conn.commit()
    console.print(f"[success][username]{target}[/username] is now a moderator.[/success]")


# ═══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE SHELL
# ═══════════════════════════════════════════════════════════════════════════════

def interactive_mode(initial_user: str | None = None) -> None:
    """Drop into a persistent interactive BBS session."""

    if RICH_AVAILABLE:
        console.print(BANNER)
        console.print(
            Panel(
                "[info]Type [bold]help[/bold] for a list of commands.  "
                "[bold]exit[/bold] to quit.[/info]",
                border_style="dim cyan",
            )
        )
    else:
        print("=== BBS Interactive Mode ===  (type 'help' for commands)")

    # ── Login ────────────────────────────────────────────────────────────────
    if initial_user:
        username = initial_user
    else:
        if RICH_AVAILABLE:
            username = Prompt.ask("\n[prompt]Enter your username[/prompt]").strip()
        else:
            username = input("Username: ").strip()

    if not username:
        console.print("[error]Username cannot be empty.[/error]")
        return

    with engine.connect() as conn:
        user_id, created = get_or_create_user(conn, username)
        if created:
            console.print(f"\n[success]Welcome to the BBS, [username]{username}[/username]! Account created.[/success]")
        else:
            # Unread PM count
            unread = conn.execute(
                text("""
                    SELECT COUNT(*) FROM private_messages
                    WHERE recipient_id = :uid AND read_at IS NULL
                """),
                {"uid": user_id},
            ).scalar()
            unread_mentions = conn.execute(
                text("SELECT COUNT(*) FROM mentions WHERE mentioned_user_id = :uid AND notified = 0"),
                {"uid": user_id},
            ).scalar()
            if unread_mentions:
                conn.execute(
                    text("UPDATE mentions SET notified = 1 WHERE mentioned_user_id = :uid AND notified = 0"),
                    {"uid": user_id},
                )
                conn.commit()
            bal_row = conn.execute(
                text("SELECT COALESCE(balance,100) FROM users WHERE id=:uid"), {"uid": user_id}
            ).fetchone()
            bal_display = f"  💰 ${bal_row[0]:,}" if bal_row else ""
            greeting = f"\n[success]Welcome back, [username]{username}[/username]![/success]{bal_display}"
            if unread:
                greeting += f"  [warn]You have {unread} unread message(s) — type [bold]inbox[/bold].[/warn]"
            if unread_mentions:
                greeting += f"  [warn]You were mentioned {unread_mentions} time(s) since your last login.[/warn]"
            new_sub_posts = conn.execute(
                text("""
                    SELECT COUNT(*) FROM posts p
                    JOIN subscriptions s ON p.board_id = s.board_id
                    WHERE s.user_id = :uid
                      AND p.parent_id IS NULL
                      AND (s.last_digest_at IS NULL OR p.timestamp > s.last_digest_at)
                """),
                {"uid": user_id},
            ).scalar()
            if new_sub_posts:
                greeting += f"  [warn]{new_sub_posts} new post(s) in your subscribed boards — type [bold]digest[/bold].[/warn]"
            console.print(greeting)

    current_board = "general"

    # ── Main REPL ────────────────────────────────────────────────────────────
    while True:
        try:
            if RICH_AVAILABLE:
                prompt_str = f"[prompt]bbs [{username}] [{current_board}][/prompt]> "
                raw = console.input(prompt_str).strip()
            else:
                raw = input(f"bbs [{username}] [{current_board}]> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[info]Goodbye![/info]")
            break

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        cmd = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        with engine.connect() as conn:

            # ── Navigation ──────────────────────────────────────────────────
            if cmd in ("exit", "quit", "logout", "q"):
                console.print("[info]Goodbye![/info]")
                break

            elif cmd == "help":
                console.print(HELP_TEXT)

            elif cmd == "clear":
                os.system("clear" if os.name != "nt" else "cls")
                if RICH_AVAILABLE:
                    console.print(BANNER)

            elif cmd == "boards":
                cmd_boards(conn)

            elif cmd == "use":
                if not rest:
                    console.print("[error]Usage: use <board>[/error]")
                else:
                    bid = get_board_id(conn, rest.strip())
                    if bid is None:
                        console.print(f"[warn]Board '[board]{rest.strip()}[/board]' does not exist.  "
                                      f"Posting to it will create it.[/warn]")
                    current_board = rest.strip()
                    console.print(f"[success]Switched to [board]{current_board}[/board].[/success]")

            # ── Posting ─────────────────────────────────────────────────────
            elif cmd == "post":
                if not rest:
                    console.print("[error]Usage: post <message>  OR  post <board> <message>[/error]")
                else:
                    # Heuristic: if first token matches an existing board, use it.
                    # Skip the DB lookup when there's only one token (no board prefix possible).
                    tokens = rest.split(maxsplit=1)
                    maybe_board = tokens[0] if tokens else None
                    board_exists = (
                        len(tokens) >= 2
                        and maybe_board is not None
                        and get_board_id(conn, maybe_board) is not None
                    )
                    if board_exists:
                        cmd_post(conn, username, tokens[1], board_name=tokens[0])
                    else:
                        cmd_post(conn, username, rest, board_name=current_board)

            elif cmd == "reply":
                tokens = rest.split(maxsplit=1)
                if len(tokens) < 2 or not tokens[0].isdigit():
                    console.print("[error]Usage: reply <post_id> <message>[/error]")
                else:
                    cmd_reply(conn, username, int(tokens[0]), tokens[1])

            elif cmd == "edit":
                tokens = rest.split(maxsplit=1)
                if len(tokens) < 2 or not tokens[0].isdigit():
                    console.print("[error]Usage: edit <post_id> <new message>[/error]")
                else:
                    cmd_edit(conn, username, int(tokens[0]), tokens[1])

            elif cmd == "delete":
                if not rest.strip().isdigit():
                    console.print("[error]Usage: delete <post_id>[/error]")
                else:
                    cmd_delete(conn, username, int(rest.strip()))

            # ── Reading ─────────────────────────────────────────────────────
            elif cmd == "read":
                # Optional: 'read [board] [--limit N] [--page N]'
                board_arg = None
                limit = 30
                page  = 1
                if rest:
                    tokens = rest.split()
                    i = 0
                    while i < len(tokens):
                        if tokens[i] == "--limit" and i + 1 < len(tokens) and tokens[i+1].isdigit():
                            limit = int(tokens[i + 1]); i += 2
                        elif tokens[i] == "--page" and i + 1 < len(tokens) and tokens[i+1].isdigit():
                            page = int(tokens[i + 1]); i += 2
                        elif not tokens[i].startswith("--"):
                            board_arg = tokens[i]; i += 1
                        else:
                            i += 1
                cmd_read(conn, board_arg, limit, page)

            elif cmd == "thread":
                if not rest or not rest.strip().isdigit():
                    console.print("[error]Usage: thread <post_id>[/error]")
                else:
                    cmd_thread(conn, int(rest.strip()))

            elif cmd == "search":
                if not rest:
                    console.print("[error]Usage: search <keyword>[/error]")
                else:
                    cmd_search(conn, rest)

            # ── Reactions ───────────────────────────────────────────────────
            elif cmd == "react":
                tokens = rest.split(maxsplit=1)
                if len(tokens) < 2 or not tokens[0].isdigit():
                    console.print("[error]Usage: react <post_id> <emoji>[/error]")
                else:
                    cmd_react(conn, username, int(tokens[0]), tokens[1].strip())

            elif cmd == "unreact":
                tokens = rest.split(maxsplit=1)
                if len(tokens) < 2 or not tokens[0].isdigit():
                    console.print("[error]Usage: unreact <post_id> <emoji>[/error]")
                else:
                    cmd_unreact(conn, username, int(tokens[0]), tokens[1].strip())

            # ── Social ──────────────────────────────────────────────────────
            elif cmd == "msg":
                tokens = rest.split(maxsplit=1)
                if len(tokens) < 2:
                    console.print("[error]Usage: msg <username> <message>[/error]")
                else:
                    cmd_msg(conn, username, tokens[0], tokens[1])

            elif cmd == "inbox":
                cmd_inbox(conn, username)

            # ── Profiles ────────────────────────────────────────────────────
            elif cmd == "users":
                cmd_users(conn)

            elif cmd == "profile":
                target = rest.strip() or username
                cmd_profile(conn, target)

            elif cmd == "bio":
                if not rest:
                    console.print("[error]Usage: bio <text>[/error]")
                else:
                    cmd_set_bio(conn, username, rest)

            # ── Moderation ──────────────────────────────────────────────────
            elif cmd == "pin":
                if not rest.strip().isdigit():
                    console.print("[error]Usage: pin <post_id>[/error]")
                else:
                    cmd_pin(conn, username, int(rest.strip()), pinned=True)

            elif cmd == "unpin":
                if not rest.strip().isdigit():
                    console.print("[error]Usage: unpin <post_id>[/error]")
                else:
                    cmd_pin(conn, username, int(rest.strip()), pinned=False)

            elif cmd == "makeadmin":
                if not rest.strip():
                    console.print("[error]Usage: makeadmin <username>[/error]")
                else:
                    cmd_makeadmin(conn, username, rest.strip())

            elif cmd == "promote":
                if not rest.strip():
                    console.print("[error]Usage: promote <username>[/error]")
                else:
                    cmd_promote(conn, username, rest.strip())

            # ── Subscriptions ───────────────────────────────────────────────
            elif cmd == "subscribe":
                if not rest.strip():
                    console.print("[error]Usage: subscribe <board>[/error]")
                else:
                    cmd_subscribe(conn, username, rest.strip(), subscribe=True)

            elif cmd == "unsubscribe":
                if not rest.strip():
                    console.print("[error]Usage: unsubscribe <board>[/error]")
                else:
                    cmd_subscribe(conn, username, rest.strip(), subscribe=False)

            elif cmd == "digest":
                cmd_digest(conn, username)

            elif cmd == "subscriptions":
                cmd_subscriptions(conn, username)

            # ── Economy ─────────────────────────────────────────────────────
            elif cmd == "fish":
                casts = 1
                if rest.strip():
                    tokens = rest.split()
                    if tokens[0].lower() == "cast" and len(tokens) > 1 and tokens[1].isdigit():
                        casts = int(tokens[1])
                    elif tokens[0].isdigit():
                        casts = int(tokens[0])
                cmd_fish(conn, username, casts)

            elif cmd == "inventory":
                cmd_inventory(conn, username)

            elif cmd == "sell":
                if not rest.strip():
                    console.print("[error]Usage: sell <fish|all>[/error]")
                else:
                    cmd_sell(conn, username, rest.strip())

            elif cmd == "buy":
                tokens = rest.split(maxsplit=1)
                if len(tokens) < 2 or not tokens[1].strip().isdigit():
                    console.print("[error]Usage: buy <fish> <quantity>[/error]")
                else:
                    cmd_buy(conn, username, tokens[0], int(tokens[1]))

            elif cmd == "market":
                cmd_market(conn)

            elif cmd == "gamble":
                if not rest.strip():
                    console.print("[error]Usage: gamble <amount|all|half>[/error]")
                else:
                    cmd_gamble(conn, username, rest.strip())

            elif cmd == "balance":
                cmd_balance(conn, username)

            elif cmd == "give":
                tokens = rest.split(maxsplit=1)
                if len(tokens) < 2:
                    console.print("[error]Usage: give <username> <amount>[/error]")
                else:
                    try:
                        cmd_give(conn, username, tokens[0], int(tokens[1]))
                    except ValueError:
                        console.print("[error]Amount must be a number.[/error]")

            elif cmd == "history":
                n = int(rest.strip()) if rest.strip().isdigit() else 10
                cmd_history(conn, username, n)

            elif cmd == "stats":
                target = rest.strip() or username
                cmd_eco_stats(conn, target)

            elif cmd == "ecoleaderboard":
                tokens = rest.split()
                sort = "balance"
                if "--sort" in tokens:
                    idx = tokens.index("--sort")
                    if idx + 1 < len(tokens):
                        sort = tokens[idx + 1]
                cmd_eco_leaderboard(conn, sort)

            # ── Stats ───────────────────────────────────────────────────────
            elif cmd == "leaderboard":
                cmd_leaderboard(conn)

            elif cmd == "trending":
                cmd_trending(conn)

            elif cmd == "export":
                out = rest.strip() if rest.strip() else "bbs_export.json"
                cmd_export(conn, out)

            else:
                console.print(
                    f"[error]Unknown command '[bold]{cmd}[/bold]'.  "
                    f"Type [bold]help[/bold] for a list.[/error]"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# ONE-SHOT (non-interactive) ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def one_shot(args: list[str]) -> None:
    """Handle a single command supplied as CLI arguments."""
    cmd = args[0]

    with engine.connect() as conn:

        if cmd == "post" and len(args) >= 3:
            cmd_post(conn, args[1], " ".join(args[2:]))

        elif cmd == "read":
            board = None
            limit = 30
            page  = 1
            remaining = args[1:]
            i = 0
            while i < len(remaining):
                if remaining[i] == "--limit" and i + 1 < len(remaining) and remaining[i+1].isdigit():
                    limit = int(remaining[i + 1]); i += 2
                elif remaining[i] == "--page" and i + 1 < len(remaining) and remaining[i+1].isdigit():
                    page = int(remaining[i + 1]); i += 2
                else:
                    board = remaining[i]; i += 1
            cmd_read(conn, board, limit, page)

        elif cmd == "users":
            cmd_users(conn)

        elif cmd == "search" and len(args) >= 2:
            cmd_search(conn, " ".join(args[1:]))

        elif cmd == "reply" and len(args) >= 4 and args[1].isdigit():
            cmd_reply(conn, args[2], int(args[1]), " ".join(args[3:]))

        elif cmd == "edit" and len(args) >= 4 and args[1].isdigit():
            cmd_edit(conn, args[2], int(args[1]), " ".join(args[3:]))

        elif cmd == "delete" and len(args) >= 3 and args[1].isdigit():
            cmd_delete(conn, args[2], int(args[1]))

        elif cmd == "pin" and len(args) >= 3 and args[1].isdigit():
            cmd_pin(conn, args[2], int(args[1]), pinned=True)

        elif cmd == "unpin" and len(args) >= 3 and args[1].isdigit():
            cmd_pin(conn, args[2], int(args[1]), pinned=False)

        elif cmd == "export":
            out = args[1] if len(args) > 1 else "bbs_export.json"
            cmd_export(conn, out)

        elif cmd == "makeadmin" and len(args) >= 3:
            cmd_makeadmin(conn, args[1], args[2])

        elif cmd == "promote" and len(args) >= 3:
            cmd_promote(conn, args[1], args[2])

        elif cmd == "subscribe" and len(args) >= 3:
            cmd_subscribe(conn, args[1], args[2], subscribe=True)

        elif cmd == "unsubscribe" and len(args) >= 3:
            cmd_subscribe(conn, args[1], args[2], subscribe=False)

        elif cmd == "digest" and len(args) >= 2:
            cmd_digest(conn, args[1])

        elif cmd == "subscriptions" and len(args) >= 2:
            cmd_subscriptions(conn, args[1])

        elif cmd == "boards":
            cmd_boards(conn)

        elif cmd == "thread" and len(args) >= 2 and args[1].isdigit():
            cmd_thread(conn, int(args[1]))

        elif cmd == "profile" and len(args) >= 2:
            cmd_profile(conn, args[1])

        elif cmd == "bio" and len(args) >= 3:
            cmd_set_bio(conn, args[1], " ".join(args[2:]))

        elif cmd == "react" and len(args) >= 4 and args[1].isdigit():
            cmd_react(conn, args[3], int(args[1]), args[2])

        elif cmd == "unreact" and len(args) >= 4 and args[1].isdigit():
            cmd_unreact(conn, args[3], int(args[1]), args[2])

        elif cmd == "msg" and len(args) >= 4:
            cmd_msg(conn, args[1], args[2], " ".join(args[3:]))

        elif cmd == "inbox" and len(args) >= 2:
            cmd_inbox(conn, args[1])

        elif cmd == "leaderboard":
            cmd_leaderboard(conn)

        elif cmd == "trending":
            cmd_trending(conn)

        # ── Economy ───────────────────────────────────────────────────────────
        elif cmd == "fish":
            if len(args) < 2:
                console.print("[error]Usage: python bbs_db.py fish <username> [cast N][/error]")
            else:
                casts = 1
                if len(args) >= 4 and args[2].lower() == "cast" and args[3].isdigit():
                    casts = int(args[3])
                elif len(args) >= 3 and args[2].isdigit():
                    casts = int(args[2])
                cmd_fish(conn, args[1], casts)

        elif cmd == "inventory" and len(args) >= 2:
            cmd_inventory(conn, args[1])

        elif cmd == "sell" and len(args) >= 3:
            cmd_sell(conn, args[1], " ".join(args[2:]))

        elif cmd == "buy" and len(args) >= 4 and args[3].isdigit():
            cmd_buy(conn, args[1], args[2], int(args[3]))

        elif cmd == "market":
            cmd_market(conn)

        elif cmd == "gamble" and len(args) >= 3:
            cmd_gamble(conn, args[1], args[2])

        elif cmd == "balance" and len(args) >= 2:
            cmd_balance(conn, args[1])

        elif cmd == "give" and len(args) >= 4 and args[3].isdigit():
            cmd_give(conn, args[1], args[2], int(args[3]))

        elif cmd == "history":
            username_arg = args[1] if len(args) >= 2 else None
            n = int(args[2]) if len(args) >= 3 and args[2].isdigit() else 10
            if username_arg:
                cmd_history(conn, username_arg, n)

        elif cmd == "stats":
            if len(args) >= 2:
                cmd_eco_stats(conn, args[1])

        elif cmd == "ecoleaderboard":
            sort = "balance"
            if "--sort" in args and args.index("--sort") + 1 < len(args):
                sort = args[args.index("--sort") + 1]
            cmd_eco_leaderboard(conn, sort)

        else:
            console.print(f"[error]Unknown command or wrong arguments: {' '.join(args)}[/error]")
            console.print("Run [bold]python bbs_db.py[/bold] with no arguments for interactive mode.")
            sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    init_db()
    init_econ()
    args = sys.argv[1:]

    # Interactive mode triggers
    if not args or args == ["-i"]:
        interactive_mode()
        return

    if args[0] == "-i" and len(args) >= 2:
        interactive_mode(initial_user=args[1])
        return

    one_shot(args)


if __name__ == "__main__":
    main()
