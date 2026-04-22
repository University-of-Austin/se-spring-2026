"""BBS Part B: SQLite database version.

A command-line BBS using SQLAlchemy with raw SQL. Supports all Bronze, Silver,
and Gold features including interactive mode, DMs, reactions, voting, pinning,
achievements, and import/export.

Usage (one-shot commands):
    python bbs_db.py post <username> <board> <message>
    python bbs_db.py read [board] [--sort=hot|new|top]
    python bbs_db.py reply <post_id> <username> <message>
    python bbs_db.py users
    python bbs_db.py boards
    python bbs_db.py search <keyword>
    python bbs_db.py profile <username>
    python bbs_db.py bio <username> <text>
    python bbs_db.py dm <from_user> <to_user> <message>
    python bbs_db.py inbox <username>
    python bbs_db.py react <username> <post_id> <emoji>
    python bbs_db.py upvote <username> <post_id>
    python bbs_db.py downvote <username> <post_id>
    python bbs_db.py trending
    python bbs_db.py pin <post_id>
    python bbs_db.py badges <username>
    python bbs_db.py export [filename]
    python bbs_db.py import <filename>
    python bbs_db.py leaderboard [game]
    python bbs_db.py interactive
"""

import json
import os
import sys

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

from db import engine, init_db
import services
import display


# ---------------------------------------------------------------------------
# One-shot command handlers
# ---------------------------------------------------------------------------

def cmd_post(args):
    if len(args) < 3:
        print("Usage: python bbs_db.py post <username> <board> <message>")
        return
    username, board = args[0], args[1]
    message = " ".join(args[2:])
    with engine.begin() as conn:
        uid = services.get_or_create_user(conn, username)
        bid = services.get_or_create_board(conn, board)
        services.create_post(conn, uid, bid, message)
        services.check_achievements(conn, uid)
    print("Posted.")


def cmd_read(args):
    board = None
    sort_mode = "default"
    for a in args:
        if a.startswith("--sort="):
            sort_mode = a.split("=", 1)[1]
        else:
            board = a
    with engine.begin() as conn:
        posts = services.get_posts(conn, board_name=board, sort_mode=sort_mode)
    if not posts:
        print("No posts." if not board else f"No posts in board '{board}'.")
        return
    roots, children = _build_tree(posts)
    _print_tree(roots, children)


def cmd_reply(args):
    if len(args) < 3:
        print("Usage: python bbs_db.py reply <post_id> <username> <message>")
        return
    try:
        post_id = int(args[0])
    except ValueError:
        print("Error: post_id must be an integer.")
        return
    username = args[1]
    message = " ".join(args[2:])
    with engine.begin() as conn:
        parent = services.get_post_by_id(conn, post_id)
        if not parent:
            print(f"Error: post #{post_id} not found.")
            return
        if parent.get("is_locked"):
            print("Error: this thread is locked.")
            return
        uid = services.get_or_create_user(conn, username)
        bid = services.get_or_create_board(conn, parent["board"])
        services.create_post(conn, uid, bid, message, reply_to=post_id)
        services.check_achievements(conn, uid)
    print("Posted.")


def cmd_users(args):
    with engine.begin() as conn:
        users = services.list_users(conn)
    if not users:
        print("No users.")
        return
    for u in users:
        print(display.fmt_user(u["username"], u["post_count"]))


def cmd_boards(args):
    with engine.begin() as conn:
        boards = services.list_boards(conn)
    if not boards:
        print("No boards.")
        return
    for b in boards:
        print(display.fmt_board(b["name"], b["post_count"]))


def cmd_search(args):
    if not args:
        print("Usage: python bbs_db.py search <keyword>")
        return
    keyword = " ".join(args)
    with engine.begin() as conn:
        results = services.search_posts(conn, keyword)
    if not results:
        print(f"No posts matching '{keyword}'.")
        return
    for p in results:
        print(display.fmt_post(p))


def cmd_profile(args):
    if not args:
        print("Usage: python bbs_db.py profile <username>")
        return
    with engine.begin() as conn:
        profile = services.get_user_profile(conn, args[0])
    if not profile:
        print(f"User '{args[0]}' not found.")
        return
    print(display.fmt_profile(profile))


def cmd_bio(args):
    if len(args) < 2:
        print("Usage: python bbs_db.py bio <username> <text>")
        return
    username = args[0]
    text = " ".join(args[1:])
    with engine.begin() as conn:
        uid = services.get_or_create_user(conn, username)
        services.update_bio(conn, username, text)
    print("Bio updated.")


def cmd_dm(args):
    if len(args) < 3:
        print("Usage: python bbs_db.py dm <from_user> <to_user> <message>")
        return
    sender, recipient = args[0], args[1]
    body = " ".join(args[2:])
    with engine.begin() as conn:
        sid = services.get_or_create_user(conn, sender)
        rid = services.require_user(conn, recipient)
        if rid is None:
            print(f"User '{recipient}' not found.")
            return
        services.send_dm(conn, sid, rid, body)
        services.check_achievements(conn, sid)
    print("Message sent.")


def cmd_inbox(args):
    if not args:
        print("Usage: python bbs_db.py inbox <username>")
        return
    with engine.begin() as conn:
        uid = services.require_user(conn, args[0])
        if uid is None:
            print(f"User '{args[0]}' not found.")
            return
        msgs = services.get_inbox(conn, uid)
        services.mark_read(conn, uid)
    if not msgs:
        print("Inbox empty.")
        return
    for m in msgs:
        print(display.fmt_dm(m))


def cmd_react(args):
    if len(args) < 3:
        print("Usage: python bbs_db.py react <username> <post_id> <emoji>")
        return
    username = args[0]
    try:
        post_id = int(args[1])
    except ValueError:
        print("Error: post_id must be an integer.")
        return
    emoji = args[2]
    with engine.begin() as conn:
        uid = services.get_or_create_user(conn, username)
        result = services.add_reaction(conn, uid, post_id, emoji)
        services.check_achievements(conn, uid)
    print(result)


def cmd_vote(args, value):
    if len(args) < 2:
        print(f"Usage: python bbs_db.py {'upvote' if value > 0 else 'downvote'} <username> <post_id>")
        return
    username = args[0]
    try:
        post_id = int(args[1])
    except ValueError:
        print("Error: post_id must be an integer.")
        return
    with engine.begin() as conn:
        uid = services.get_or_create_user(conn, username)
        result = services.cast_vote(conn, uid, post_id, value)
        services.check_achievements(conn, uid)
    print(result)


def cmd_trending(args):
    with engine.begin() as conn:
        posts = services.get_trending(conn)
    if not posts:
        print("No trending posts.")
        return
    print(display.paint("═══ Trending Posts ═══", display.FG_CYAN, display.BOLD))
    for i, p in enumerate(posts, 1):
        print(display.fmt_trending(i, p))


def cmd_pin(args):
    if not args:
        print("Usage: python bbs_db.py pin <post_id>")
        return
    try:
        post_id = int(args[0])
    except ValueError:
        print("Error: post_id must be an integer.")
        return
    with engine.begin() as conn:
        result = services.pin_post(conn, post_id)
    if result is None:
        print(f"Post #{post_id} not found.")
    elif result:
        print(f"Post #{post_id} pinned.")
    else:
        print(f"Post #{post_id} unpinned.")


def cmd_badges(args):
    if not args:
        print("Usage: python bbs_db.py badges <username>")
        return
    with engine.begin() as conn:
        uid = services.require_user(conn, args[0])
        if uid is None:
            print(f"User '{args[0]}' not found.")
            return
        badges = services.get_badges(conn, uid)
    if not badges:
        print("No badges yet.")
        return
    print(display.paint(f"═══ Badges: {args[0]} ═══", display.FG_YELLOW, display.BOLD))
    for b, desc, awarded in badges:
        print(display.fmt_badge(b, desc))


def cmd_export(args):
    filename = args[0] if args else "bbs_export.json"
    with engine.begin() as conn:
        data = services.export_all(conn)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Exported to {filename}.")


def cmd_import(args):
    if not args:
        print("Usage: python bbs_db.py import <filename>")
        return
    try:
        with open(args[0], "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File '{args[0]}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: '{args[0]}' is not valid JSON.")
        return
    with engine.begin() as conn:
        stats = services.import_all(conn, data)
    print(f"Imported: {stats['users']} users, {stats['boards']} boards, "
          f"{stats['posts']} posts, {stats['messages']} messages.")


def cmd_leaderboard(args):
    game = args[0] if args else None
    with engine.begin() as conn:
        entries = services.get_leaderboard(conn, game=game)
    if not entries:
        print("No scores yet." if not game else f"No scores for '{game}'.")
        return
    title = f"═══ Leaderboard{': ' + game if game else ''} ═══"
    print(display.paint(title, display.FG_YELLOW, display.BOLD))
    for i, e in enumerate(entries, 1):
        print(display.fmt_leaderboard_entry(i, e))


# ---------------------------------------------------------------------------
# Tree display helpers
# ---------------------------------------------------------------------------

def _build_tree(posts):
    children = {}
    roots = []
    for p in posts:
        if p.get("reply_to") is None:
            roots.append(p)
        else:
            children.setdefault(p["reply_to"], []).append(p)
    return roots, children


def _print_tree(roots, children, indent=0):
    for post in roots:
        print(display.fmt_post_with_id(post, indent=indent))
        kids = children.get(post["id"], [])
        if kids:
            _print_tree(kids, children, indent + 1)


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def interactive_mode():
    display.print_banner()
    username = input(display.paint("Enter your username: ", display.FG_GREEN, display.BOLD)).strip()
    if not username:
        print("Username required.")
        return

    with engine.begin() as conn:
        uid = services.get_or_create_user(conn, username)
        unread = services.count_unread(conn, uid)
        new_badges = services.check_achievements(conn, uid)

    if unread:
        print(display.paint(f"  You have {unread} unread message(s)!", display.FG_RED, display.BOLD))
    if new_badges:
        for b in new_badges:
            print(display.paint(f"  🏆 New badge unlocked: [{b}]!", display.FG_YELLOW, display.BOLD))
    print()
    display.print_interactive_help()

    while True:
        try:
            raw = input(display.paint(f"{username}@bbs> ", display.FG_CYAN, display.BOLD)).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not raw:
            continue

        parts = raw.split(None, 1)
        cmd = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        if cmd in ("quit", "exit"):
            print("Goodbye!")
            break

        elif cmd == "help":
            display.print_interactive_help()

        elif cmd == "post":
            iparts = rest.split(None, 1)
            if len(iparts) < 2:
                print("Usage: post <board> <message>")
                continue
            board, message = iparts[0], iparts[1]
            with engine.begin() as conn:
                uid = services.get_or_create_user(conn, username)
                bid = services.get_or_create_board(conn, board)
                services.create_post(conn, uid, bid, message)
                new_badges = services.check_achievements(conn, uid)
            print("Posted.")
            for b in new_badges:
                print(display.paint(f"  🏆 New badge unlocked: [{b}]!", display.FG_YELLOW, display.BOLD))

        elif cmd == "read":
            board_name = None
            sort_mode = "default"
            for token in rest.split():
                if token.startswith("--sort="):
                    sort_mode = token.split("=", 1)[1]
                else:
                    board_name = token
            with engine.begin() as conn:
                posts = services.get_posts(conn, board_name=board_name, sort_mode=sort_mode)
            if not posts:
                print("No posts.")
            else:
                roots, children = _build_tree(posts)
                _print_tree(roots, children)

        elif cmd == "reply":
            iparts = rest.split(None, 1)
            if len(iparts) < 2:
                print("Usage: reply <post_id> <message>")
                continue
            try:
                post_id = int(iparts[0])
            except ValueError:
                print("Error: post_id must be an integer.")
                continue
            message = iparts[1]
            with engine.begin() as conn:
                parent = services.get_post_by_id(conn, post_id)
                if not parent:
                    print(f"Post #{post_id} not found.")
                    continue
                if parent.get("is_locked"):
                    print("This thread is locked.")
                    continue
                uid = services.get_or_create_user(conn, username)
                bid = services.get_or_create_board(conn, parent["board"])
                services.create_post(conn, uid, bid, message, reply_to=post_id)
                new_badges = services.check_achievements(conn, uid)
            print("Posted.")
            for b in new_badges:
                print(display.paint(f"  🏆 New badge unlocked: [{b}]!", display.FG_YELLOW, display.BOLD))

        elif cmd == "search":
            if not rest:
                print("Usage: search <keyword>")
                continue
            with engine.begin() as conn:
                results = services.search_posts(conn, rest)
            if not results:
                print(f"No posts matching '{rest}'.")
            else:
                for p in results:
                    print(display.fmt_post(p))

        elif cmd == "users":
            with engine.begin() as conn:
                users = services.list_users(conn)
            for u in users:
                print(display.fmt_user(u["username"], u["post_count"]))

        elif cmd == "boards":
            with engine.begin() as conn:
                boards = services.list_boards(conn)
            for b in boards:
                print(display.fmt_board(b["name"], b["post_count"]))

        elif cmd == "trending":
            with engine.begin() as conn:
                posts = services.get_trending(conn)
            if not posts:
                print("No trending posts.")
            else:
                print(display.paint("═══ Trending ═══", display.FG_CYAN, display.BOLD))
                for i, p in enumerate(posts, 1):
                    print(display.fmt_trending(i, p))

        elif cmd == "pin":
            if not rest:
                print("Usage: pin <post_id>")
                continue
            try:
                post_id = int(rest)
            except ValueError:
                print("Error: post_id must be an integer.")
                continue
            with engine.begin() as conn:
                result = services.pin_post(conn, post_id)
            if result is None:
                print(f"Post #{post_id} not found.")
            elif result:
                print(f"Post #{post_id} pinned.")
            else:
                print(f"Post #{post_id} unpinned.")

        elif cmd == "dm":
            iparts = rest.split(None, 1)
            if len(iparts) < 2:
                print("Usage: dm <user> <message>")
                continue
            recipient, body = iparts[0], iparts[1]
            with engine.begin() as conn:
                uid = services.get_or_create_user(conn, username)
                rid = services.require_user(conn, recipient)
                if rid is None:
                    print(f"User '{recipient}' not found.")
                    continue
                services.send_dm(conn, uid, rid, body)
                new_badges = services.check_achievements(conn, uid)
            print("Message sent.")
            for b in new_badges:
                print(display.paint(f"  🏆 New badge unlocked: [{b}]!", display.FG_YELLOW, display.BOLD))

        elif cmd == "inbox":
            with engine.begin() as conn:
                uid = services.get_or_create_user(conn, username)
                msgs = services.get_inbox(conn, uid)
                services.mark_read(conn, uid)
            if not msgs:
                print("Inbox empty.")
            else:
                for m in msgs:
                    print(display.fmt_dm(m))

        elif cmd == "react":
            iparts = rest.split()
            if len(iparts) < 2:
                print("Usage: react <post_id> <emoji>")
                continue
            try:
                post_id = int(iparts[0])
            except ValueError:
                print("Error: post_id must be an integer.")
                continue
            emoji = iparts[1]
            with engine.begin() as conn:
                uid = services.get_or_create_user(conn, username)
                result = services.add_reaction(conn, uid, post_id, emoji)
                services.check_achievements(conn, uid)
            print(result)

        elif cmd == "upvote":
            if not rest:
                print("Usage: upvote <post_id>")
                continue
            try:
                post_id = int(rest)
            except ValueError:
                print("Error: post_id must be an integer.")
                continue
            with engine.begin() as conn:
                uid = services.get_or_create_user(conn, username)
                result = services.cast_vote(conn, uid, post_id, 1)
                services.check_achievements(conn, uid)
            print(result)

        elif cmd == "downvote":
            if not rest:
                print("Usage: downvote <post_id>")
                continue
            try:
                post_id = int(rest)
            except ValueError:
                print("Error: post_id must be an integer.")
                continue
            with engine.begin() as conn:
                uid = services.get_or_create_user(conn, username)
                result = services.cast_vote(conn, uid, post_id, -1)
                services.check_achievements(conn, uid)
            print(result)

        elif cmd == "profile":
            target = rest.strip() or username
            with engine.begin() as conn:
                profile = services.get_user_profile(conn, target)
            if not profile:
                print(f"User '{target}' not found.")
            else:
                print(display.fmt_profile(profile))

        elif cmd == "bio":
            if not rest:
                print("Usage: bio <text>")
                continue
            with engine.begin() as conn:
                services.get_or_create_user(conn, username)
                services.update_bio(conn, username, rest)
            print("Bio updated.")

        elif cmd == "avatar":
            if not rest:
                print("Usage: avatar <ascii art>")
                continue
            with engine.begin() as conn:
                services.update_avatar(conn, username, rest)
            print("Avatar updated.")

        elif cmd == "badges":
            with engine.begin() as conn:
                uid = services.get_or_create_user(conn, username)
                badges = services.get_badges(conn, uid)
            if not badges:
                print("No badges yet.")
            else:
                print(display.paint(f"═══ Your Badges ═══", display.FG_YELLOW, display.BOLD))
                for b, desc, awarded in badges:
                    print(display.fmt_badge(b, desc))

        elif cmd == "export":
            filename = rest.strip() or "bbs_export.json"
            with engine.begin() as conn:
                data = services.export_all(conn)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Exported to {filename}.")

        elif cmd == "import":
            if not rest:
                print("Usage: import <filename>")
                continue
            filename = rest.strip()
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except FileNotFoundError:
                print(f"File '{filename}' not found.")
                continue
            with engine.begin() as conn:
                stats = services.import_all(conn, data)
            print(f"Imported: {stats['users']} users, {stats['boards']} boards, {stats['posts']} posts.")

        elif cmd == "leaderboard":
            game = rest.strip() or None
            with engine.begin() as conn:
                entries = services.get_leaderboard(conn, game=game)
            if not entries:
                print("No scores yet.")
            else:
                title = f"═══ Leaderboard{': ' + game if game else ''} ═══"
                print(display.paint(title, display.FG_YELLOW, display.BOLD))
                for i, e in enumerate(entries, 1):
                    print(display.fmt_leaderboard_entry(i, e))

        elif cmd == "games":
            try:
                from games import games_menu
                games_menu(username)
            except ImportError:
                print("Games module not available.")

        else:
            print(f"Unknown command: {cmd}. Type 'help' for commands.")


# ---------------------------------------------------------------------------
# Main CLI dispatch
# ---------------------------------------------------------------------------

def main():
    init_db()
    args = sys.argv[1:]
    if not args:
        print("Usage: python bbs_db.py <command> [args...]")
        print("Commands: post, read, reply, users, boards, search, profile, bio,")
        print("          dm, inbox, react, upvote, downvote, trending, pin, badges,")
        print("          export, import, leaderboard, interactive")
        return

    cmd = args[0].lower()
    rest = args[1:]

    dispatch = {
        "post": cmd_post,
        "read": cmd_read,
        "reply": cmd_reply,
        "users": cmd_users,
        "boards": cmd_boards,
        "search": cmd_search,
        "profile": cmd_profile,
        "bio": cmd_bio,
        "dm": cmd_dm,
        "inbox": cmd_inbox,
        "react": cmd_react,
        "trending": cmd_trending,
        "pin": cmd_pin,
        "badges": cmd_badges,
        "export": cmd_export,
        "import": cmd_import,
        "leaderboard": cmd_leaderboard,
    }

    if cmd == "interactive":
        interactive_mode()
    elif cmd == "upvote":
        cmd_vote(rest, 1)
    elif cmd == "downvote":
        cmd_vote(rest, -1)
    elif cmd in dispatch:
        dispatch[cmd](rest)
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
