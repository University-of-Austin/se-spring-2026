import sys
import shlex
import argparse
from datetime import datetime
from sqlalchemy import text
from db import engine, init_db


def fmt(username, message, timestamp):
    dt = datetime.fromisoformat(timestamp)
    return f"[{dt.strftime('%Y-%m-%d %H:%M')}] {username}: {message}"


def get_or_create_user(conn, username):
    row = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username}).fetchone()
    if row:
        return row[0]
    result = conn.execute(text("INSERT INTO users (username) VALUES (:u)"), {"u": username})
    return result.lastrowid


def cmd_post(args):
    with engine.begin() as conn:
        uid = get_or_create_user(conn, args.username)
        conn.execute(text(
            "INSERT INTO posts (user_id, message, timestamp, parent_id) VALUES (:uid, :msg, :ts, NULL)"
        ), {"uid": uid, "msg": args.message, "ts": datetime.now().isoformat()})
    print("Posted.")


def cmd_reply(args):
    with engine.begin() as conn:
        parent = conn.execute(text("SELECT id FROM posts WHERE id = :pid"), {"pid": args.post_id}).fetchone()
        if not parent:
            print(f"Error: no post with ID {args.post_id}.", file=sys.stderr)
            sys.exit(1)
        uid = get_or_create_user(conn, args.username)
        conn.execute(text(
            "INSERT INTO posts (user_id, message, timestamp, parent_id) VALUES (:uid, :msg, :ts, :pid)"
        ), {"uid": uid, "msg": args.message, "ts": datetime.now().isoformat(), "pid": args.post_id})
    print("Posted.")


def cmd_read(args):
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT p.id, u.username, p.message, p.timestamp, p.parent_id "
            "FROM posts p JOIN users u ON p.user_id = u.id "
            "ORDER BY p.timestamp"
        )).fetchall()

    posts = {}
    children = {}
    roots = []
    for pid, username, message, timestamp, parent_id in rows:
        posts[pid] = (username, message, timestamp)
        if parent_id is None:
            roots.append(pid)
        else:
            children.setdefault(parent_id, []).append(pid)

    def print_tree(pid, depth=0):
        username, message, timestamp = posts[pid]
        print("  " * depth + fmt(username, message, timestamp))
        for child_id in children.get(pid, []):
            print_tree(child_id, depth + 1)

    for root_id in roots:
        print_tree(root_id)


def cmd_users(args):
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT username FROM users ORDER BY username")).fetchall()
    for row in rows:
        print(row[0])


def cmd_search(args):
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT u.username, p.message, p.timestamp "
            "FROM posts p JOIN users u ON p.user_id = u.id "
            "WHERE p.message LIKE :kw "
            "ORDER BY p.timestamp"
        ), {"kw": f"%{args.keyword}%"}).fetchall()
    for username, message, timestamp in rows:
        print(fmt(username, message, timestamp))


HELP_TEXT = """\
Commands:
  post <message>       Post a new message
  reply <id> <message> Reply to a post by ID
  read                 Read all posts
  users                List all users
  search <keyword>     Search posts
  help                 Show this help
  quit / exit          Leave the BBS
"""


def interactive(username):
    print(f"Logged in as {username}. Type 'help' for commands.\n")
    while True:
        try:
            raw = input("bbs> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not raw:
            continue

        try:
            parts = shlex.split(raw)
        except ValueError as e:
            print(f"Parse error: {e}")
            continue

        cmd = parts[0].lower()

        if cmd in ("quit", "exit"):
            print("Goodbye.")
            break
        elif cmd == "help":
            print(HELP_TEXT, end="")
        elif cmd == "post":
            if len(parts) < 2:
                print("Usage: post <message>")
                continue
            message = " ".join(parts[1:])

            class A:
                pass

            a = A()
            a.username = username
            a.message = message
            cmd_post(a)
        elif cmd == "reply":
            if len(parts) < 3:
                print("Usage: reply <id> <message>")
                continue
            try:
                post_id = int(parts[1])
            except ValueError:
                print("Post ID must be a number.")
                continue
            message = " ".join(parts[2:])

            class A:
                pass

            a = A()
            a.post_id = post_id
            a.username = username
            a.message = message
            cmd_reply(a)
        elif cmd == "read":
            cmd_read(None)
        elif cmd == "users":
            cmd_users(None)
        elif cmd == "search":
            if len(parts) < 2:
                print("Usage: search <keyword>")
                continue

            class A:
                pass

            a = A()
            a.keyword = parts[1]
            cmd_search(a)
        else:
            print(f"Unknown command '{cmd}'. Type 'help' for commands.")


def main():
    init_db()

    if len(sys.argv) == 1:
        print("=== Welcome to BBS ===")
        try:
            username = input("Username: ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit(0)
        if not username:
            print("Username cannot be empty.")
            sys.exit(1)
        interactive(username)
        return

    parser = argparse.ArgumentParser(description="BBS - SQLite storage with threads")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("post")
    p.add_argument("username")
    p.add_argument("message")
    p.set_defaults(func=cmd_post)

    rep = sub.add_parser("reply")
    rep.add_argument("post_id", type=int, help="ID of the post to reply to")
    rep.add_argument("username")
    rep.add_argument("message")
    rep.set_defaults(func=cmd_reply)

    r = sub.add_parser("read")
    r.set_defaults(func=cmd_read)

    u = sub.add_parser("users")
    u.set_defaults(func=cmd_users)

    s = sub.add_parser("search")
    s.add_argument("keyword")
    s.set_defaults(func=cmd_search)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
