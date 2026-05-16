"""Full-screen curses TUI for the BBS.

Launch:  python bbs_db.py tui
         python tui.py

Requires: pip install windows-curses  (on Windows)
"""

import curses
import sys
from datetime import datetime

from sqlalchemy import text

from db import engine, init_db


# ── Color pairs ─────────────────────────────────────────────────

C_HEADER = 1
C_MENU_KEY = 2
C_MENU_DESC = 3
C_POST_USER = 4
C_POST_META = 5
C_STATUS = 6
C_INPUT = 7
C_HIGHLIGHT = 8
C_ERROR = 9
C_OK = 10
C_VOTE_UP = 11
C_VOTE_DOWN = 12
C_PINNED = 13


def _init_colors():
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(C_HEADER, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(C_MENU_KEY, curses.COLOR_YELLOW, -1)
    curses.init_pair(C_MENU_DESC, curses.COLOR_WHITE, -1)
    curses.init_pair(C_POST_USER, curses.COLOR_CYAN, -1)
    curses.init_pair(C_POST_META, curses.COLOR_WHITE, -1)
    curses.init_pair(C_STATUS, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(C_INPUT, curses.COLOR_GREEN, -1)
    curses.init_pair(C_HIGHLIGHT, curses.COLOR_YELLOW, -1)
    curses.init_pair(C_ERROR, curses.COLOR_RED, -1)
    curses.init_pair(C_OK, curses.COLOR_GREEN, -1)
    curses.init_pair(C_VOTE_UP, curses.COLOR_GREEN, -1)
    curses.init_pair(C_VOTE_DOWN, curses.COLOR_RED, -1)
    curses.init_pair(C_PINNED, curses.COLOR_YELLOW, -1)


# ── Database queries (return data, don't print) ─────────────────

def db_get_or_create_user(username):
    with engine.begin() as conn:
        row = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username}).fetchone()
        if row:
            return row[0]
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        return conn.execute(
            text("INSERT INTO users (username, joined) VALUES (:u, :j)"),
            {"u": username, "j": ts},
        ).lastrowid


def db_get_posts(board=None, sort="default"):
    q = ("SELECT p.id, u.username, b.name, p.message, p.timestamp, p.reply_to, "
         "COALESCE(p.is_pinned, 0), "
         "COALESCE((SELECT SUM(value) FROM votes v WHERE v.post_id = p.id), 0) as net_votes "
         "FROM posts p JOIN users u ON p.user_id = u.id "
         "JOIN boards b ON p.board_id = b.id ")
    params = {}
    if board:
        q += "WHERE b.name = :board "
        params["board"] = board
    if sort == "top":
        q += "ORDER BY net_votes DESC, p.id DESC"
    elif sort == "new":
        q += "ORDER BY p.id DESC"
    elif sort == "hot":
        q += "ORDER BY COALESCE(p.is_pinned, 0) DESC, net_votes DESC, p.id DESC"
    else:
        q += "ORDER BY COALESCE(p.is_pinned, 0) DESC, p.id"
    with engine.connect() as conn:
        return conn.execute(text(q), params).fetchall()


def db_get_boards():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT b.name, COUNT(p.id) FROM boards b "
                 "LEFT JOIN posts p ON b.id = p.board_id "
                 "GROUP BY b.name ORDER BY b.name")
        ).fetchall()


def db_get_users():
    with engine.connect() as conn:
        return conn.execute(text("SELECT username FROM users ORDER BY username")).fetchall()


def db_get_inbox(username):
    with engine.connect() as conn:
        uid = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username}).fetchone()
        if not uid:
            return []
        rows = conn.execute(
            text("SELECT s.username, m.body, m.timestamp, m.is_read "
                 "FROM messages m JOIN users s ON m.sender_id = s.id "
                 "WHERE m.recipient_id = :uid ORDER BY m.id DESC"),
            {"uid": uid[0]},
        ).fetchall()
        conn.execute(text("UPDATE messages SET is_read = 1 "
                          "WHERE recipient_id = :uid AND is_read = 0"), {"uid": uid[0]})
        return rows


def db_get_unread_count(username):
    with engine.connect() as conn:
        uid = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username}).fetchone()
        if not uid:
            return 0
        return conn.execute(
            text("SELECT COUNT(*) FROM messages WHERE recipient_id = :uid AND is_read = 0"),
            {"uid": uid[0]},
        ).fetchone()[0]


def db_get_profile(username):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, username, bio, joined FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if not row:
            return None
        uid = row[0]
        count = conn.execute(
            text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"), {"uid": uid},
        ).fetchone()[0]
        badges = conn.execute(
            text("SELECT badge FROM achievements WHERE user_id = :uid"), {"uid": uid},
        ).fetchall()
        return {"username": row[1], "bio": row[2], "joined": row[3],
                "posts": count, "badges": [b[0] for b in badges]}


def db_get_trending():
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT p.id, u.username, b.name, p.message, "
                 "  COALESCE((SELECT SUM(value) FROM votes v WHERE v.post_id = p.id), 0) "
                 "  + (SELECT COUNT(*) FROM reactions r WHERE r.post_id = p.id) as score "
                 "FROM posts p JOIN users u ON p.user_id = u.id "
                 "JOIN boards b ON p.board_id = b.id "
                 "HAVING score > 0 ORDER BY score DESC LIMIT 15")
        ).fetchall()


def db_post(username, board, message, reply_to=None):
    with engine.begin() as conn:
        uid_row = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username}).fetchone()
        uid = uid_row[0] if uid_row else db_get_or_create_user(username)
        bid_row = conn.execute(text("SELECT id FROM boards WHERE name = :n"), {"n": board}).fetchone()
        if bid_row:
            bid = bid_row[0]
        else:
            bid = conn.execute(text("INSERT INTO boards (name) VALUES (:n)"), {"n": board}).lastrowid
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            text("INSERT INTO posts (user_id, board_id, message, timestamp, reply_to) "
                 "VALUES (:uid, :bid, :msg, :ts, :rt)"),
            {"uid": uid, "bid": bid, "msg": message, "ts": ts, "rt": reply_to},
        )


def db_vote(username, post_id, value):
    with engine.begin() as conn:
        uid = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": username}).fetchone()
        if not uid:
            return "User not found"
        existing = conn.execute(
            text("SELECT id, value FROM votes WHERE post_id = :pid AND user_id = :uid"),
            {"pid": post_id, "uid": uid[0]},
        ).fetchone()
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if existing:
            if existing[1] == value:
                conn.execute(text("DELETE FROM votes WHERE id = :id"), {"id": existing[0]})
                return "Vote removed"
            conn.execute(text("UPDATE votes SET value = :v, timestamp = :ts WHERE id = :id"),
                         {"v": value, "ts": ts, "id": existing[0]})
        else:
            conn.execute(text("INSERT INTO votes (post_id, user_id, value, timestamp) "
                              "VALUES (:pid, :uid, :v, :ts)"),
                         {"pid": post_id, "uid": uid[0], "v": value, "ts": ts})
        return "Upvoted" if value > 0 else "Downvoted"


def db_send_dm(sender, recipient, body):
    with engine.begin() as conn:
        sid = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": sender}).fetchone()
        rid = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": recipient}).fetchone()
        if not sid or not rid:
            return False
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(text("INSERT INTO messages (sender_id, recipient_id, body, timestamp) "
                          "VALUES (:s, :r, :b, :ts)"),
                     {"s": sid[0], "r": rid[0], "b": body, "ts": ts})
        return True


# ── TUI Application ─────────────────────────────────────────────

class BBSTUI:
    def __init__(self, stdscr):
        self.scr = stdscr
        self.username = None
        self.status_msg = ""
        self.view = "menu"
        self.scroll = 0

        _init_colors()
        curses.curs_set(0)
        self.scr.keypad(True)

    def run(self):
        if not self.login():
            return
        while True:
            if self.view == "menu":
                if not self.main_menu():
                    break
            elif self.view == "posts":
                self.posts_view()
            elif self.view == "boards":
                self.boards_view()
            elif self.view == "users":
                self.users_view()
            elif self.view == "inbox":
                self.inbox_view()
            elif self.view == "trending":
                self.trending_view()
            elif self.view == "profile":
                self.profile_view()
            elif self.view == "games":
                self.games_view()

    def _dims(self):
        h, w = self.scr.getmaxyx()
        return h, w

    def _draw_header(self):
        h, w = self._dims()
        unread = db_get_unread_count(self.username) if self.username else 0
        title = f" BBS v2.0 Gold"
        user_info = f" [{self.username}]" if self.username else ""
        dm_info = f" [{unread} unread]" if unread > 0 else ""
        header = title + " " * max(0, w - len(title) - len(user_info) - len(dm_info)) + dm_info + user_info
        try:
            self.scr.addnstr(0, 0, header[:w], w, curses.color_pair(C_HEADER) | curses.A_BOLD)
        except curses.error:
            pass

    def _draw_status(self, msg=""):
        h, w = self._dims()
        status = msg or self.status_msg or " q=back | arrows=scroll | enter=select"
        try:
            self.scr.addnstr(h - 1, 0, status[:w].ljust(w), w, curses.color_pair(C_STATUS))
        except curses.error:
            pass

    def _get_input(self, prompt, y=None):
        h, w = self._dims()
        if y is None:
            y = h - 2
        curses.curs_set(1)
        self.scr.move(y, 0)
        self.scr.clrtoeol()
        try:
            self.scr.addstr(y, 0, prompt, curses.color_pair(C_INPUT))
        except curses.error:
            pass
        self.scr.refresh()
        curses.echo()
        try:
            val = self.scr.getstr(y, len(prompt), w - len(prompt) - 1).decode("utf-8", errors="replace").strip()
        except (curses.error, UnicodeDecodeError):
            val = ""
        curses.noecho()
        curses.curs_set(0)
        return val

    def _show_lines(self, lines, title="", allow_input=None):
        """Generic scrollable view. Returns input string if allow_input is set."""
        self.scroll = 0
        while True:
            self.scr.clear()
            h, w = self._dims()
            self._draw_header()

            if title:
                try:
                    self.scr.addstr(1, 1, title, curses.color_pair(C_HIGHLIGHT) | curses.A_BOLD)
                except curses.error:
                    pass

            start_y = 3 if title else 2
            visible = h - start_y - 2
            end = min(self.scroll + visible, len(lines))

            for i, line in enumerate(lines[self.scroll:end]):
                y = start_y + i
                try:
                    if isinstance(line, tuple):
                        text_str, attr = line
                        self.scr.addnstr(y, 1, text_str[:w-2], w-2, attr)
                    else:
                        self.scr.addnstr(y, 1, str(line)[:w-2], w-2)
                except curses.error:
                    pass

            scroll_info = f" [{self.scroll+1}-{end}/{len(lines)}]" if len(lines) > visible else ""
            self._draw_status(f" q=back | up/down=scroll{scroll_info}" +
                            (f" | type to {allow_input}" if allow_input else ""))
            self.scr.refresh()

            key = self.scr.getch()
            if key == ord("q") or key == 27:  # q or Esc
                return None
            elif key == curses.KEY_UP and self.scroll > 0:
                self.scroll -= 1
            elif key == curses.KEY_DOWN and self.scroll < max(0, len(lines) - visible):
                self.scroll += 1
            elif key == curses.KEY_PPAGE:  # Page Up
                self.scroll = max(0, self.scroll - visible)
            elif key == curses.KEY_NPAGE:  # Page Down
                self.scroll = min(max(0, len(lines) - visible), self.scroll + visible)
            elif allow_input and (key == ord(":") or key == ord("/")):
                return self._get_input(f" {allow_input}: ")

    # ── Login ───────────────────────────────────────────────────

    def login(self):
        self.scr.clear()
        h, w = self._dims()
        banner = [
            "   ___  ___  ___",
            "  | _ )| _ )/ __|",
            "  | _ \\| _ \\\\__ \\",
            "  |___/|___/|___/",
            "",
            "  Bulletin Board System v2.0 Gold",
            "  " + "-" * 28,
        ]
        start_y = max(1, h // 2 - 5)
        for i, line in enumerate(banner):
            try:
                self.scr.addstr(start_y + i, max(0, w // 2 - 18), line,
                                curses.color_pair(C_POST_USER) | curses.A_BOLD)
            except curses.error:
                pass

        username = self._get_input("  Enter username: ", start_y + len(banner) + 1)
        if not username:
            return False
        self.username = username
        db_get_or_create_user(username)
        return True

    # ── Main Menu ───────────────────────────────────────────────

    def main_menu(self):
        items = [
            ("1", "Read Posts"),
            ("2", "Post Message"),
            ("3", "Boards"),
            ("4", "Users"),
            ("5", "Search"),
            ("6", "Inbox / DMs"),
            ("7", "Trending"),
            ("8", "Profile"),
            ("9", "Games"),
            ("0", "Badges"),
            ("q", "Quit"),
        ]
        selected = 0
        while True:
            self.scr.clear()
            h, w = self._dims()
            self._draw_header()

            try:
                self.scr.addstr(2, 2, "Main Menu", curses.color_pair(C_HIGHLIGHT) | curses.A_BOLD)
            except curses.error:
                pass

            for i, (key, label) in enumerate(items):
                y = 4 + i
                attr = curses.A_REVERSE if i == selected else 0
                try:
                    self.scr.addstr(y, 3, f" [{key}] ", curses.color_pair(C_MENU_KEY) | curses.A_BOLD | attr)
                    self.scr.addstr(y, 9, f" {label} ", curses.color_pair(C_MENU_DESC) | attr)
                except curses.error:
                    pass

            self._draw_status(" Enter=select | arrows=move | q=quit")
            self.scr.refresh()

            key = self.scr.getch()
            if key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(items) - 1:
                selected += 1
            elif key in (curses.KEY_ENTER, 10, 13):
                return self._dispatch_menu(items[selected][0])
            elif key == ord("q"):
                return False
            else:
                ch = chr(key) if 0 <= key < 256 else ""
                for k, _ in items:
                    if ch == k:
                        return self._dispatch_menu(k)

    def _dispatch_menu(self, key):
        views = {
            "1": "posts", "2": "new_post", "3": "boards",
            "4": "users", "5": "search", "6": "inbox",
            "7": "trending", "8": "profile", "9": "games",
            "0": "badges", "q": None,
        }
        target = views.get(key)
        if target is None:
            return False

        if target == "new_post":
            board = self._get_input(" Board: ")
            if not board:
                return True
            msg = self._get_input(" Message: ")
            if msg:
                db_post(self.username, board, msg)
                self.status_msg = "Posted!"
            return True
        elif target == "search":
            kw = self._get_input(" Search: ")
            if kw:
                self._search_view(kw)
            return True
        elif target == "badges":
            self._badges_view()
            return True
        else:
            self.view = target
            return True

    # ── Posts View ──────────────────────────────────────────────

    def posts_view(self):
        rows = db_get_posts()
        lines = []
        if not rows:
            lines.append(("No posts yet.", curses.color_pair(C_POST_META)))
        else:
            for pid, user, board, msg, ts, reply_to, pinned, votes in rows:
                ts_str = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
                prefix = "[PINNED] " if pinned else ""
                vote_str = f" [{'+' if votes > 0 else ''}{votes}]" if votes != 0 else ""
                indent = "  " if reply_to else ""
                line = f"{indent}{prefix}[{ts_str}] [{board}] #{pid} {user}: {msg}{vote_str}"
                attr = curses.color_pair(C_PINNED) | curses.A_BOLD if pinned else curses.color_pair(C_POST_META)
                lines.append((line, attr))

        result = self._show_lines(lines, "Posts (u=upvote d=downvote r=reply)", allow_input="command")
        if result:
            parts = result.split(None, 1)
            cmd = parts[0].lower() if parts else ""
            arg = parts[1] if len(parts) > 1 else ""
            if cmd in ("u", "upvote") and arg:
                try:
                    db_vote(self.username, int(arg), +1)
                except ValueError:
                    pass
                self.posts_view()
                return
            elif cmd in ("d", "downvote") and arg:
                try:
                    db_vote(self.username, int(arg), -1)
                except ValueError:
                    pass
                self.posts_view()
                return
            elif cmd in ("r", "reply") and arg:
                sub = arg.split(None, 1)
                if len(sub) == 2:
                    try:
                        db_post(self.username, "general", sub[1], reply_to=int(sub[0]))
                    except ValueError:
                        pass
                self.posts_view()
                return
        self.view = "menu"

    # ── Boards View ─────────────────────────────────────────────

    def boards_view(self):
        rows = db_get_boards()
        lines = []
        if not rows:
            lines.append(("No boards yet.", curses.color_pair(C_POST_META)))
        else:
            for name, count in rows:
                lines.append((f"  {name}  ({count} posts)", curses.color_pair(C_HIGHLIGHT)))
        self._show_lines(lines, "Boards")
        self.view = "menu"

    # ── Users View ──────────────────────────────────────────────

    def users_view(self):
        rows = db_get_users()
        lines = [(f"  {r[0]}", curses.color_pair(C_POST_USER) | curses.A_BOLD) for r in rows]
        if not lines:
            lines = [("No users yet.", curses.color_pair(C_POST_META))]
        self._show_lines(lines, "Users")
        self.view = "menu"

    # ── Inbox View ──────────────────────────────────────────────

    def inbox_view(self):
        rows = db_get_inbox(self.username)
        lines = []
        if not rows:
            lines.append(("No messages.", curses.color_pair(C_POST_META)))
        else:
            for sender, body, ts, is_read in rows:
                ts_str = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
                marker = " [NEW]" if not is_read else ""
                attr = curses.color_pair(C_OK) | curses.A_BOLD if not is_read else curses.color_pair(C_POST_META)
                lines.append((f"  [{ts_str}] {sender}: {body}{marker}", attr))

        result = self._show_lines(lines, f"Inbox for {self.username} (type :dm user msg)",
                                  allow_input="dm <user> <msg>")
        if result:
            parts = result.split(None, 1)
            if len(parts) == 2:
                dm_parts = parts[0], parts[1] if len(parts) > 1 else ""
                # parse as: user message
                sub = result.split(None, 1)
                if len(sub) >= 2:
                    recip = sub[0]
                    body = sub[1]
                    db_send_dm(self.username, recip, body)
                    self.inbox_view()
                    return
        self.view = "menu"

    # ── Trending View ───────────────────────────────────────────

    def trending_view(self):
        rows = db_get_trending()
        lines = []
        if not rows:
            lines.append(("No trending posts yet.", curses.color_pair(C_POST_META)))
        else:
            for i, (pid, user, board, msg, score) in enumerate(rows, 1):
                lines.append((f"  {i}. #{pid} [{board}] {user}: {msg}  (score: {score})",
                               curses.color_pair(C_HIGHLIGHT)))
        self._show_lines(lines, "Trending Posts")
        self.view = "menu"

    # ── Profile View ────────────────────────────────────────────

    def profile_view(self):
        data = db_get_profile(self.username)
        if not data:
            self.view = "menu"
            return
        joined = datetime.fromisoformat(data["joined"]).strftime("%Y-%m-%d %H:%M")
        lines = [
            (f"  User:    {data['username']}", curses.color_pair(C_POST_USER) | curses.A_BOLD),
            (f"  Joined:  {joined}", curses.color_pair(C_POST_META)),
            (f"  Posts:   {data['posts']}", curses.color_pair(C_HIGHLIGHT)),
            (f"  Bio:     {data['bio'] or '(none)'}", curses.color_pair(C_POST_META)),
        ]
        if data["badges"]:
            lines.append(("", 0))
            lines.append(("  Badges:", curses.color_pair(C_HIGHLIGHT) | curses.A_BOLD))
            for b in data["badges"]:
                lines.append((f"    [*] {b}", curses.color_pair(C_MENU_KEY)))
        self._show_lines(lines, "Profile")
        self.view = "menu"

    # ── Search View ─────────────────────────────────────────────

    def _search_view(self, keyword):
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT u.username, b.name, p.message, p.timestamp "
                     "FROM posts p JOIN users u ON p.user_id = u.id "
                     "JOIN boards b ON p.board_id = b.id "
                     "WHERE p.message LIKE :kw ORDER BY p.id"),
                {"kw": f"%{keyword}%"},
            ).fetchall()
        lines = []
        if not rows:
            lines.append(("No results.", curses.color_pair(C_POST_META)))
        else:
            for user, board, msg, ts in rows:
                ts_str = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
                lines.append((f"  [{ts_str}] [{board}] {user}: {msg}", curses.color_pair(C_POST_META)))
        self._show_lines(lines, f'Search: "{keyword}"')

    # ── Badges View ─────────────────────────────────────────────

    def _badges_view(self):
        data = db_get_profile(self.username)
        lines = []
        if not data or not data["badges"]:
            lines.append(("No badges yet. Keep posting!", curses.color_pair(C_POST_META)))
        else:
            for b in data["badges"]:
                lines.append((f"  [*] {b}", curses.color_pair(C_MENU_KEY) | curses.A_BOLD))
        self._show_lines(lines, f"Badges for {self.username}")

    # ── Games View ──────────────────────────────────────────────

    def games_view(self):
        """Temporarily exit curses to play door games in normal terminal mode."""
        curses.endwin()
        try:
            from games import games_menu
            games_menu(self.username)
            # Check achievements after playing
            from bbs_db import check_achievements
            check_achievements(self.username)
        except Exception as e:
            print(f"Error: {e}")
        input("\n  Press Enter to return to the TUI...")
        self.scr.refresh()
        self.view = "menu"


def _main(stdscr):
    init_db()
    app = BBSTUI(stdscr)
    app.run()


def run_tui():
    curses.wrapper(_main)


if __name__ == "__main__":
    init_db()
    run_tui()
