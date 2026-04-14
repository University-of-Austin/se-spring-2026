import sys
from cmd import Cmd
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import text

from db import engine, init_db

# ANSI styling — only active in interactive mode
_color = False


@contextmanager
def _color_mode():
    global _color
    _color = True
    try:
        yield
    finally:
        _color = False
BOLD = "1"
NAVY = "1;34"
GOLD = "1;33"
GRAY = "90"

BANNER = """\
╔══════════════════════════════════════╗
║                                      ║
║          U A T X  ·  B B S          ║
║        Bulletin Board System         ║
║                                      ║
╚══════════════════════════════════════╝"""


def style(s, code):
    return f"\033[{code}m{s}\033[0m" if _color else str(s)


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def fmt_ts(timestamp):
    ts = datetime.fromisoformat(timestamp)
    return style(f"[{ts:%Y-%m-%d %H:%M}]", GRAY)


def fmt_post(username, message, timestamp):
    return f"{fmt_ts(timestamp)} {style(username, GOLD)}: {message}"


def require_user(conn, username):
    user_id = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    ).scalar()
    if not user_id:
        die(f"No user '{username}' found. Users are created when they first post.")
    return user_id


def get_or_create_user(conn, username, now=None):
    if now is None:
        now = datetime.now().replace(microsecond=0).isoformat()
    result = conn.execute(
        text("INSERT OR IGNORE INTO users (username, created_at) VALUES (:username, :now)"),
        {"username": username, "now": now},
    )
    is_new = result.rowcount > 0
    user_id = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    ).scalar()
    return user_id, is_new


def cmd_post(args):
    if len(args) != 2:
        die("Usage: bbs_db.py post <username> <message>")
    username, message = args[0].lower(), args[1]
    now = datetime.now().replace(microsecond=0).isoformat()
    with engine.begin() as conn:
        user_id, is_new = get_or_create_user(conn, username, now)
        conn.execute(
            text("""
                INSERT INTO posts (user_id, message, timestamp)
                VALUES (:user_id, :message, :ts)
            """),
            {"user_id": user_id, "message": message, "ts": now},
        )
    print("Posted.")
    if is_new:
        if _color:
            print(f"Welcome to UATX BBS! Log in anytime with {style('login', GOLD)} to manage your profile.")
        else:
            print(f"Welcome to UATX BBS, {username}! Log in with: bbs_db.py login {username}")


def cmd_read(args):
    if args:
        die("Usage: bbs_db.py read")
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT u.username, p.message, p.timestamp
            FROM posts p JOIN users u ON p.user_id = u.id
            ORDER BY p.timestamp ASC, p.id ASC
        """))
        for row in rows:
            print(fmt_post(row.username, row.message, row.timestamp))


def cmd_users(args):
    if args:
        die("Usage: bbs_db.py users")
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT username FROM users ORDER BY id ASC"))
        for row in rows:
            print(row.username)


def cmd_search(args):
    if len(args) != 1:
        die("Usage: bbs_db.py search <keyword>")
    keyword = args[0].replace("%", "\\%").replace("_", "\\_")
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT u.username, p.message, p.timestamp
                FROM posts p JOIN users u ON p.user_id = u.id
                WHERE p.message LIKE :pattern ESCAPE '\\'
                ORDER BY p.timestamp ASC, p.id ASC
            """),
            {"pattern": f"%{keyword}%"},
        )
        for row in rows:
            print(fmt_post(row.username, row.message, row.timestamp))


def cmd_profile(args):
    if len(args) != 1 or not args[0].strip():
        die("Usage: bbs_db.py profile <username>")
    username = args[0].lower()
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT u.id, u.username, u.created_at, u.bio,
                       (SELECT COUNT(*) FROM posts WHERE user_id = u.id) AS post_count,
                       (SELECT COUNT(*) FROM messages WHERE sender_id = u.id) AS dms_sent
                FROM users u WHERE u.username = :username
            """),
            {"username": username},
        ).fetchone()
        if not row:
            die(f"No user '{username}' found. Users are created when they first post.")

        joined = datetime.fromisoformat(row.created_at)
        divider = "─" * max(0, 35 - len(row.username))
        print(style(f"─── {row.username} {divider}", NAVY))
        print()
        print(f"  Joined:   {joined:%Y-%m-%d}")
        print(f"  Posts:    {row.post_count}")
        if row.dms_sent:
            print(f"  DMs sent: {row.dms_sent}")
        if row.bio:
            print(f"  Bio:      {row.bio}")

        posts = conn.execute(
            text("""
                SELECT message, timestamp FROM posts
                WHERE user_id = :user_id
                ORDER BY timestamp DESC, id DESC LIMIT 5
            """),
            {"user_id": row.id},
        ).fetchall()
        if posts:
            print()
            print(f"  {style('Recent:', BOLD)}")
            for post in reversed(posts):
                print(f"    {fmt_ts(post.timestamp)} {post.message}")


def cmd_set_bio(args):
    if len(args) != 2:
        die("Usage: bbs_db.py set-bio <username> <bio>")
    username, bio = args[0].lower(), args[1]
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE users SET bio = :bio WHERE username = :username"),
            {"username": username, "bio": bio},
        )
        if result.rowcount == 0:
            die(f"No user '{username}' found. Users are created when they first post.")
    print("Bio updated.")


def cmd_dm(args):
    if len(args) != 3:
        die("Usage: bbs_db.py dm <from> <to> <message>")
    sender_name, recipient_name, message = args[0].lower(), args[1].lower(), args[2]
    now = datetime.now().replace(microsecond=0).isoformat()
    with engine.begin() as conn:
        sender_id = require_user(conn, sender_name)
        recipient_id = require_user(conn, recipient_name)
        conn.execute(
            text("""
                INSERT INTO messages (sender_id, recipient_id, message, timestamp)
                VALUES (:sender_id, :recipient_id, :message, :ts)
            """),
            {"sender_id": sender_id, "recipient_id": recipient_id,
             "message": message, "ts": now},
        )
    print("Message sent.")


def cmd_inbox(args):
    if len(args) != 1:
        die("Usage: bbs_db.py inbox <username>")
    username = args[0].lower()
    with engine.begin() as conn:
        user_id = require_user(conn, username)

        rows = conn.execute(
            text("""
                SELECT m.id, m.is_read, u.username AS sender, m.message, m.timestamp
                FROM messages m JOIN users u ON m.sender_id = u.id
                WHERE m.recipient_id = :user_id
                ORDER BY m.timestamp ASC, m.id ASC
            """),
            {"user_id": user_id},
        ).fetchall()

        unread = sum(1 for r in rows if not r.is_read)
        if unread:
            print(style(f"{unread} new message{'s' if unread != 1 else ''}", GOLD))
            print()

        for row in rows:
            if not row.is_read:
                print(f"{style('(new)', GOLD)} {fmt_ts(row.timestamp)} from {style(row.sender, GOLD)}: {row.message}")
            else:
                print(f"      {fmt_ts(row.timestamp)} from {style(row.sender, GOLD)}: {row.message}")

        if rows:
            conn.execute(
                text("UPDATE messages SET is_read = 1 WHERE recipient_id = :user_id AND is_read = 0"),
                {"user_id": user_id},
            )


def cmd_sent(args):
    if len(args) != 1:
        die("Usage: bbs_db.py sent <username>")
    username = args[0].lower()
    with engine.connect() as conn:
        user_id = require_user(conn, username)

        rows = conn.execute(
            text("""
                SELECT u.username AS recipient, m.message, m.timestamp
                FROM messages m JOIN users u ON m.recipient_id = u.id
                WHERE m.sender_id = :user_id
                ORDER BY m.timestamp ASC, m.id ASC
            """),
            {"user_id": user_id},
        )
        for row in rows:
            print(f"{fmt_ts(row.timestamp)} to {style(row.recipient, GOLD)}: {row.message}")


class BBSSession(Cmd):

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.prompt = f"\033[{NAVY}mbbs>\033[0m " if _color else "bbs> "

    def preloop(self):
        with engine.begin() as conn:
            _, is_new = get_or_create_user(conn, self.username)
        print()
        print(style(BANNER, NAVY))
        print()
        print(f"  Welcome, {style(self.username, GOLD)}!")
        if is_new:
            print(f"  Set up your profile with {style('bio', GOLD)} <text>")
        print(f"  Type {style('help', BOLD)} for available commands.")
        print()

    def emptyline(self):
        pass

    def _run(self, fn, args):
        try:
            fn(args)
        except SystemExit as e:
            if e.code not in (0, 1):
                raise

    def do_post(self, arg):
        if not arg:
            print("Usage: post <message>")
            return
        self._run(cmd_post, [self.username, arg])

    def do_read(self, arg):
        self._run(cmd_read, [])

    def do_users(self, arg):
        self._run(cmd_users, [])

    def do_search(self, arg):
        if not arg:
            print("Usage: search <keyword>")
            return
        self._run(cmd_search, [arg])

    def do_profile(self, arg):
        self._run(cmd_profile, [arg if arg else self.username])

    def do_bio(self, arg):
        if not arg:
            print("Usage: bio <text>")
            return
        self._run(cmd_set_bio, [self.username, arg])

    def do_dm(self, arg):
        parts = arg.split(None, 1)
        if len(parts) < 2:
            print("Usage: dm <username> <message>")
            return
        self._run(cmd_dm, [self.username, parts[0], parts[1]])

    def do_inbox(self, arg):
        self._run(cmd_inbox, [self.username])

    def do_sent(self, arg):
        self._run(cmd_sent, [self.username])

    def do_help(self, arg):
        print(style("Commands:", BOLD))
        print(f"  {style('post', GOLD)} <message>          Post a message")
        print(f"  {style('read', GOLD)}                    Read all messages")
        print(f"  {style('users', GOLD)}                   List all users")
        print(f"  {style('search', GOLD)} <keyword>        Search posts by keyword")
        print(f"  {style('profile', GOLD)} [username]      View a profile (default: yours)")
        print(f"  {style('bio', GOLD)} <text>              Set your bio")
        print(f"  {style('dm', GOLD)} <username> <message> Send a private message")
        print(f"  {style('inbox', GOLD)}                   View received messages")
        print(f"  {style('sent', GOLD)}                    View sent messages")
        print(f"  {style('quit', GOLD)}                    Exit the BBS")

    def do_quit(self, arg):
        print(f"Goodbye, {style(self.username, GOLD)}.")
        return True

    do_exit = do_quit
    do_logout = do_quit

    def do_EOF(self, arg):
        print()
        return self.do_quit(arg)

    def default(self, line):
        name = line.split()[0]
        if name == "set-bio":
            self.do_bio(line[len("set-bio"):].strip())
        else:
            print(f"Unknown command: {name}. Type 'help' for available commands.")


def cmd_login(args):
    if len(args) != 1:
        die("Usage: bbs_db.py login <username>")
    username = args[0].lower()
    with _color_mode():
        try:
            BBSSession(username).cmdloop()
        except KeyboardInterrupt:
            print(f"\nGoodbye, {username}.")


def cmd_usage(_args):
    print("Usage: bbs_db.py <command> [args]")
    print()
    print("Commands:")
    print("  post <username> <message>   Post a message")
    print("  read                        Read all messages")
    print("  users                       List all users")
    print("  search <keyword>            Search posts by keyword")
    print("  profile <username>          View a user's profile")
    print("  set-bio <username> <bio>    Set your bio")
    print("  dm <from> <to> <message>    Send a private message")
    print("  inbox <username>            View received messages")
    print("  sent <username>             View sent messages")
    print("  login <username>            Start interactive session")


commands = {
    "post": cmd_post,
    "read": cmd_read,
    "users": cmd_users,
    "search": cmd_search,
    "profile": cmd_profile,
    "set-bio": cmd_set_bio,
    "dm": cmd_dm,
    "inbox": cmd_inbox,
    "sent": cmd_sent,
    "login": cmd_login,
}

if __name__ == "__main__":
    init_db()
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd and cmd not in commands:
        die(f"Unknown command: {cmd}. Run with no arguments for usage.")
    commands.get(cmd, cmd_usage)(sys.argv[2:])
