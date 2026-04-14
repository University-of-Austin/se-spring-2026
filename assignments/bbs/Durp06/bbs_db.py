"""BBS -- Part B: SQLite-backed bulletin board system (Gold tier).

Gold features beyond Silver:
  - Interactive mode (live bbs> prompt with login)
  - Private messages (dm / inbox / sent)
  - Post reactions with trending algorithm
  - Import / export (full round-trip DB <-> JSON)
  - Upvote / downvote with hot/new/top sorting
  - Achievements / badges
  - Post pinning
  - Door games (trivia, hangman, number guessing) with leaderboard
  - Full-screen curses TUI
"""

import json
import sys
from datetime import datetime

from sqlalchemy import text

from db import engine, init_db
from display import (
    fmt_badge, fmt_board, fmt_dim, fmt_dm, fmt_err, fmt_ok, fmt_post,
    fmt_search_hit, fmt_trending, fmt_user, fmt_vote_score, paint,
    print_banner, print_header, print_interactive_help, print_profile,
    print_usage,
    BOLD, BR_CYAN, BR_WHITE, BR_YELLOW, CYAN, DIM, GREEN, COLOR, RESET,
)


# ── Helpers ─────────────────────────────────────────────────────

def _get_or_create_user(conn, username):
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"), {"u": username},
    ).fetchone()
    if row:
        return row[0]
    ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return conn.execute(
        text("INSERT INTO users (username, joined) VALUES (:u, :j)"),
        {"u": username, "j": ts},
    ).lastrowid


def _get_or_create_board(conn, name):
    row = conn.execute(
        text("SELECT id FROM boards WHERE name = :n"), {"n": name},
    ).fetchone()
    if row:
        return row[0]
    return conn.execute(
        text("INSERT INTO boards (name) VALUES (:n)"), {"n": name},
    ).lastrowid


def _require_user(conn, username):
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"), {"u": username},
    ).fetchone()
    return row[0] if row else None


def _fmt_ts(ts):
    return datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")


def _reaction_counts(conn):
    rows = conn.execute(
        text("SELECT post_id, emoji, COUNT(*) FROM reactions GROUP BY post_id, emoji")
    ).fetchall()
    result = {}
    for pid, emoji, cnt in rows:
        result.setdefault(pid, {})[emoji] = cnt
    return result


def _vote_counts(conn):
    rows = conn.execute(
        text("SELECT post_id, "
             "SUM(CASE WHEN value > 0 THEN 1 ELSE 0 END), "
             "SUM(CASE WHEN value < 0 THEN 1 ELSE 0 END) "
             "FROM votes GROUP BY post_id")
    ).fetchall()
    return {pid: (up, down) for pid, up, down in rows}


def _format_reaction_str(counts_for_post: dict) -> str:
    if not counts_for_post:
        return ""
    parts = []
    for emoji, count in sorted(counts_for_post.items(), key=lambda x: -x[1]):
        parts.append(f"[{emoji} x{count}]")
    return " ".join(parts)


# ── Achievements ────────────────────────────────────────────────

BADGE_DEFS = {
    "first_post":    ("First Post",        "Made your first post"),
    "chatterbox":    ("Chatterbox",         "Posted 10 messages"),
    "reply_king":    ("Reply King",         "Replied to 5 posts"),
    "explorer":      ("Board Explorer",     "Posted in 3 different boards"),
    "social":        ("Social Butterfly",   "Sent 5 private messages"),
    "popular":       ("Popular",            "Got 5 upvotes on a single post"),
    "voter":         ("Democracy!",         "Voted on 10 posts"),
    "gamer":         ("Gamer",              "Played a door game"),
    "high_roller":   ("High Roller",        "Scored 80+ in a door game"),
}


def check_achievements(username):
    """Check and award any new badges for this user. Returns list of newly awarded badges."""
    newly_awarded = []
    with engine.begin() as conn:
        uid = _require_user(conn, username)
        if uid is None:
            return []

        existing = {row[0] for row in conn.execute(
            text("SELECT badge FROM achievements WHERE user_id = :uid"), {"uid": uid},
        ).fetchall()}

        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        def award(key):
            if key not in existing:
                name, desc = BADGE_DEFS[key]
                conn.execute(
                    text("INSERT OR IGNORE INTO achievements (user_id, badge, description, awarded) "
                         "VALUES (:uid, :b, :d, :ts)"),
                    {"uid": uid, "b": name, "d": desc, "ts": ts},
                )
                newly_awarded.append(name)

        # First post
        post_count = conn.execute(
            text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"), {"uid": uid},
        ).fetchone()[0]
        if post_count >= 1:
            award("first_post")
        if post_count >= 10:
            award("chatterbox")

        # Replies
        reply_count = conn.execute(
            text("SELECT COUNT(*) FROM posts WHERE user_id = :uid AND reply_to IS NOT NULL"),
            {"uid": uid},
        ).fetchone()[0]
        if reply_count >= 5:
            award("reply_king")

        # Board explorer
        board_count = conn.execute(
            text("SELECT COUNT(DISTINCT board_id) FROM posts WHERE user_id = :uid"),
            {"uid": uid},
        ).fetchone()[0]
        if board_count >= 3:
            award("explorer")

        # Social
        dm_count = conn.execute(
            text("SELECT COUNT(*) FROM messages WHERE sender_id = :uid"), {"uid": uid},
        ).fetchone()[0]
        if dm_count >= 5:
            award("social")

        # Popular
        max_upvotes = conn.execute(
            text("SELECT MAX(cnt) FROM ("
                 "  SELECT COUNT(*) as cnt FROM votes "
                 "  WHERE value > 0 AND post_id IN "
                 "    (SELECT id FROM posts WHERE user_id = :uid) "
                 "  GROUP BY post_id)"),
            {"uid": uid},
        ).fetchone()[0]
        if max_upvotes and max_upvotes >= 5:
            award("popular")

        # Voter
        vote_count = conn.execute(
            text("SELECT COUNT(*) FROM votes WHERE user_id = :uid"), {"uid": uid},
        ).fetchone()[0]
        if vote_count >= 10:
            award("voter")

        # Gamer
        game_count = conn.execute(
            text("SELECT COUNT(*) FROM high_scores WHERE user_id = :uid"), {"uid": uid},
        ).fetchone()[0]
        if game_count >= 1:
            award("gamer")

        # High roller
        best_score = conn.execute(
            text("SELECT MAX(score) FROM high_scores WHERE user_id = :uid"), {"uid": uid},
        ).fetchone()[0]
        if best_score and best_score >= 80:
            award("high_roller")

    return newly_awarded


def _notify_badges(badges):
    for b in badges:
        print(paint(f"  ** Achievement Unlocked: {b}! **", BOLD, BR_YELLOW))


# ── Commands ────────────────────────────────────────────────────

def cmd_post(username, board_name, message, reply_to=None):
    with engine.begin() as conn:
        uid = _get_or_create_user(conn, username)
        bid = _get_or_create_board(conn, board_name)
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if reply_to is not None:
            parent = conn.execute(
                text("SELECT id FROM posts WHERE id = :id"), {"id": reply_to},
            ).fetchone()
            if not parent:
                print(fmt_err(f"Post #{reply_to} not found."))
                return False
        conn.execute(
            text(
                "INSERT INTO posts (user_id, board_id, message, timestamp, reply_to) "
                "VALUES (:uid, :bid, :msg, :ts, :rt)"
            ),
            {"uid": uid, "bid": bid, "msg": message, "ts": ts, "rt": reply_to},
        )
    print(fmt_ok("Posted."))
    _notify_badges(check_achievements(username))
    return True


def cmd_read(board_name=None, sort_mode="default"):
    q = (
        "SELECT p.id, u.username, b.name, p.message, p.timestamp, p.reply_to, "
        "COALESCE(p.is_pinned, 0) as is_pinned "
        "FROM posts p "
        "JOIN users u ON p.user_id = u.id "
        "JOIN boards b ON p.board_id = b.id "
    )
    params = {}
    if board_name:
        q += "WHERE b.name = :board "
        params["board"] = board_name

    if sort_mode == "top":
        q += ("ORDER BY (SELECT COALESCE(SUM(value), 0) FROM votes v "
              "WHERE v.post_id = p.id) DESC, p.id DESC")
    elif sort_mode == "new":
        q += "ORDER BY p.id DESC"
    elif sort_mode == "hot":
        # Hot = votes + recency (posts from last 24h get a boost)
        q += ("ORDER BY COALESCE(p.is_pinned, 0) DESC, "
              "(SELECT COALESCE(SUM(value), 0) FROM votes v WHERE v.post_id = p.id) "
              "+ CASE WHEN p.timestamp > datetime('now', '-1 day') THEN 5 ELSE 0 END DESC, "
              "p.id DESC")
    else:
        q += "ORDER BY COALESCE(p.is_pinned, 0) DESC, p.id"

    with engine.connect() as conn:
        rows = conn.execute(text(q), params).fetchall()
        rcounts = _reaction_counts(conn)
        vcounts = _vote_counts(conn)

    if board_name:
        print_header(f"Board: {board_name}" + (f" (sort: {sort_mode})" if sort_mode != "default" else ""))
    else:
        print_banner()

    if not rows:
        print(fmt_dim("No posts yet."))
        print()
        return

    roots, children = [], {}
    for pid, user, board, msg, ts, reply_to, pinned in rows:
        post = {"id": pid, "username": user, "board": board,
                "message": msg, "timestamp": ts, "reply_to": reply_to,
                "pinned": bool(pinned)}
        if reply_to is None:
            roots.append(post)
        else:
            children.setdefault(reply_to, []).append(post)

    def walk(post, depth=0):
        ts = _fmt_ts(post["timestamp"])
        rstr = _format_reaction_str(rcounts.get(post["id"], {}))
        up, down = vcounts.get(post["id"], (0, 0))
        vstr = fmt_vote_score(up, down)
        print(fmt_post(ts, post["board"], post["id"], post["username"],
                        post["message"], depth, rstr, vstr, post["pinned"]))
        for child in children.get(post["id"], []):
            walk(child, depth + 1)

    for r in roots:
        walk(r)
    print()


def cmd_users():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT username FROM users ORDER BY username")
        ).fetchall()
    print_header("Users")
    if not rows:
        print(fmt_dim("No users yet."))
        return
    for (name,) in rows:
        print(fmt_user(name))
    print()


def cmd_boards():
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT b.name, COUNT(p.id) "
                "FROM boards b LEFT JOIN posts p ON b.id = p.board_id "
                "GROUP BY b.name ORDER BY b.name"
            )
        ).fetchall()
    print_header("Boards")
    if not rows:
        print(fmt_dim("No boards yet."))
        return
    for name, count in rows:
        print(fmt_board(name, count))
    print()


def cmd_search(keyword):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT u.username, b.name, p.message, p.timestamp "
                "FROM posts p "
                "JOIN users u ON p.user_id = u.id "
                "JOIN boards b ON p.board_id = b.id "
                "WHERE p.message LIKE :kw "
                "ORDER BY p.id"
            ),
            {"kw": f"%{keyword}%"},
        ).fetchall()
    print_header(f'Search: "{keyword}"')
    if not rows:
        print(fmt_dim("No posts found."))
        return
    for user, board, msg, ts in rows:
        print(fmt_search_hit(_fmt_ts(ts), board, user, msg))
    print()


def cmd_profile(username):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, username, bio, joined FROM users WHERE username = :u"),
            {"u": username},
        ).fetchone()
        if not row:
            print(fmt_err(f"User '{username}' not found."))
            return
        uid, uname, bio, joined = row
        count = conn.execute(
            text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"), {"uid": uid},
        ).fetchone()[0]
        badge_rows = conn.execute(
            text("SELECT badge, description FROM achievements WHERE user_id = :uid ORDER BY awarded"),
            {"uid": uid},
        ).fetchall()
    badges = [(b, d) for b, d in badge_rows]
    print_profile(uname, _fmt_ts(joined), count, bio, badges)


def cmd_bio(username, bio_text):
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM users WHERE username = :u"), {"u": username},
        ).fetchone()
        if not row:
            _get_or_create_user(conn, username)
        conn.execute(
            text("UPDATE users SET bio = :bio WHERE username = :u"),
            {"bio": bio_text, "u": username},
        )
    print(fmt_dim("Bio updated."))


# ── Upvote / Downvote ───────────────────────────────────────────

def cmd_vote(username, post_id, value):
    """value: +1 for upvote, -1 for downvote."""
    label = "Upvoted" if value > 0 else "Downvoted"
    with engine.begin() as conn:
        uid = _require_user(conn, username)
        if uid is None:
            print(fmt_err(f"User '{username}' not found."))
            return
        post = conn.execute(
            text("SELECT id FROM posts WHERE id = :id"), {"id": post_id},
        ).fetchone()
        if not post:
            print(fmt_err(f"Post #{post_id} not found."))
            return
        existing = conn.execute(
            text("SELECT id, value FROM votes WHERE post_id = :pid AND user_id = :uid"),
            {"pid": post_id, "uid": uid},
        ).fetchone()
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if existing:
            if existing[1] == value:
                # Remove vote (toggle off)
                conn.execute(text("DELETE FROM votes WHERE id = :id"), {"id": existing[0]})
                print(fmt_ok(f"Vote removed from post #{post_id}."))
                return
            conn.execute(
                text("UPDATE votes SET value = :v, timestamp = :ts WHERE id = :id"),
                {"v": value, "ts": ts, "id": existing[0]},
            )
        else:
            conn.execute(
                text("INSERT INTO votes (post_id, user_id, value, timestamp) "
                     "VALUES (:pid, :uid, :v, :ts)"),
                {"pid": post_id, "uid": uid, "v": value, "ts": ts},
            )
    print(fmt_ok(f"{label} post #{post_id}."))
    _notify_badges(check_achievements(username))


# ── Pin ─────────────────────────────────────────────────────────

def cmd_pin(username, post_id):
    with engine.begin() as conn:
        uid = _require_user(conn, username)
        if uid is None:
            print(fmt_err(f"User '{username}' not found."))
            return
        post = conn.execute(
            text("SELECT id, user_id, COALESCE(is_pinned, 0) FROM posts WHERE id = :id"),
            {"id": post_id},
        ).fetchone()
        if not post:
            print(fmt_err(f"Post #{post_id} not found."))
            return
        new_val = 0 if post[2] else 1
        conn.execute(
            text("UPDATE posts SET is_pinned = :v WHERE id = :id"),
            {"v": new_val, "id": post_id},
        )
    action = "Pinned" if new_val else "Unpinned"
    print(fmt_ok(f"{action} post #{post_id}."))


# ── Private Messages ────────────────────────────────────────────

def cmd_dm(sender, recipient, body):
    with engine.begin() as conn:
        sid = _require_user(conn, sender)
        if sid is None:
            print(fmt_err(f"Sender '{sender}' not found. Post something first."))
            return
        rid = _require_user(conn, recipient)
        if rid is None:
            print(fmt_err(f"User '{recipient}' not found."))
            return
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            text("INSERT INTO messages (sender_id, recipient_id, body, timestamp) "
                 "VALUES (:sid, :rid, :body, :ts)"),
            {"sid": sid, "rid": rid, "body": body, "ts": ts},
        )
    print(fmt_ok(f"Message sent to {recipient}."))
    _notify_badges(check_achievements(sender))


def cmd_inbox(username):
    with engine.connect() as conn:
        uid = _require_user(conn, username)
        if uid is None:
            print(fmt_err(f"User '{username}' not found."))
            return
        rows = conn.execute(
            text(
                "SELECT m.id, s.username, u.username, m.body, m.timestamp, m.is_read "
                "FROM messages m "
                "JOIN users s ON m.sender_id = s.id "
                "JOIN users u ON m.recipient_id = u.id "
                "WHERE m.recipient_id = :uid "
                "ORDER BY m.id DESC"
            ),
            {"uid": uid},
        ).fetchall()
    print_header(f"Inbox for {username}")
    if not rows:
        print(fmt_dim("No messages."))
        return
    for mid, sender, recip, body, ts, is_read in rows:
        print(fmt_dm(_fmt_ts(ts), sender, recip, body, unread=not is_read))
    print()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE messages SET is_read = 1 WHERE recipient_id = :uid AND is_read = 0"),
            {"uid": uid},
        )


def cmd_sent(username):
    with engine.connect() as conn:
        uid = _require_user(conn, username)
        if uid is None:
            print(fmt_err(f"User '{username}' not found."))
            return
        rows = conn.execute(
            text(
                "SELECT m.id, s.username, u.username, m.body, m.timestamp "
                "FROM messages m "
                "JOIN users s ON m.sender_id = s.id "
                "JOIN users u ON m.recipient_id = u.id "
                "WHERE m.sender_id = :uid "
                "ORDER BY m.id DESC"
            ),
            {"uid": uid},
        ).fetchall()
    print_header(f"Sent by {username}")
    if not rows:
        print(fmt_dim("No sent messages."))
        return
    for mid, sender, recip, body, ts in rows:
        print(fmt_dm(_fmt_ts(ts), sender, recip, body))
    print()


# ── Reactions & Trending ────────────────────────────────────────

def cmd_react(username, post_id, emoji="+1"):
    with engine.begin() as conn:
        uid = _require_user(conn, username)
        if uid is None:
            print(fmt_err(f"User '{username}' not found. Post something first."))
            return
        post = conn.execute(
            text("SELECT id FROM posts WHERE id = :id"), {"id": post_id},
        ).fetchone()
        if not post:
            print(fmt_err(f"Post #{post_id} not found."))
            return
        existing = conn.execute(
            text("SELECT id FROM reactions WHERE post_id = :pid AND user_id = :uid"),
            {"pid": post_id, "uid": uid},
        ).fetchone()
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if existing:
            conn.execute(
                text("UPDATE reactions SET emoji = :e, timestamp = :ts WHERE id = :id"),
                {"e": emoji, "ts": ts, "id": existing[0]},
            )
            print(fmt_ok(f"Reaction updated to [{emoji}] on post #{post_id}."))
        else:
            conn.execute(
                text("INSERT INTO reactions (post_id, user_id, emoji, timestamp) "
                     "VALUES (:pid, :uid, :e, :ts)"),
                {"pid": post_id, "uid": uid, "e": emoji, "ts": ts},
            )
            print(fmt_ok(f"Reacted [{emoji}] to post #{post_id}."))


def cmd_trending(limit=10):
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT p.id, u.username, b.name, p.message, p.timestamp, "
                "  COALESCE((SELECT SUM(value) FROM votes v WHERE v.post_id = p.id), 0) "
                "  + COUNT(r.id) as score "
                "FROM posts p "
                "JOIN users u ON p.user_id = u.id "
                "JOIN boards b ON p.board_id = b.id "
                "LEFT JOIN reactions r ON r.post_id = p.id "
                "GROUP BY p.id "
                "HAVING score > 0 "
                "ORDER BY score DESC, p.timestamp DESC "
                "LIMIT :lim"
            ),
            {"lim": limit},
        ).fetchall()
        rcounts = _reaction_counts(conn)
    print_header("Trending Posts")
    if not rows:
        print(fmt_dim("No reactions or votes yet."))
        return
    for rank, (pid, user, board, msg, ts, score) in enumerate(rows, 1):
        rstr = _format_reaction_str(rcounts.get(pid, {}))
        print(fmt_trending(rank, pid, user, board, msg, score, rstr))
    print()


# ── Badges display ──────────────────────────────────────────────

def cmd_badges(username):
    with engine.connect() as conn:
        uid = _require_user(conn, username)
        if uid is None:
            print(fmt_err(f"User '{username}' not found."))
            return
        rows = conn.execute(
            text("SELECT badge, description, awarded FROM achievements "
                 "WHERE user_id = :uid ORDER BY awarded"),
            {"uid": uid},
        ).fetchall()
    print_header(f"Badges for {username}")
    if not rows:
        print(fmt_dim("No badges yet. Keep posting!"))
        return
    for badge, desc, awarded in rows:
        print(fmt_badge(badge, desc))
    earned = len(rows)
    total = len(BADGE_DEFS)
    print(f"\n  {paint(f'{earned}/{total} badges earned', DIM)}")
    print()


# ── Import / Export ─────────────────────────────────────────────

def cmd_export(filepath="export.json"):
    with engine.connect() as conn:
        posts = conn.execute(
            text(
                "SELECT p.id, u.username, b.name, p.message, p.timestamp, p.reply_to "
                "FROM posts p JOIN users u ON p.user_id = u.id "
                "JOIN boards b ON p.board_id = b.id ORDER BY p.id"
            )
        ).fetchall()
        user_rows = conn.execute(
            text("SELECT username, joined, bio FROM users ORDER BY username")
        ).fetchall()
        msg_rows = conn.execute(
            text(
                "SELECT s.username, r.username, m.body, m.timestamp, m.is_read "
                "FROM messages m JOIN users s ON m.sender_id = s.id "
                "JOIN users r ON m.recipient_id = r.id ORDER BY m.id"
            )
        ).fetchall()
        react_rows = conn.execute(
            text(
                "SELECT r.post_id, u.username, r.emoji, r.timestamp "
                "FROM reactions r JOIN users u ON r.user_id = u.id ORDER BY r.id"
            )
        ).fetchall()
        vote_rows = conn.execute(
            text(
                "SELECT v.post_id, u.username, v.value, v.timestamp "
                "FROM votes v JOIN users u ON v.user_id = u.id ORDER BY v.id"
            )
        ).fetchall()

    data = {
        "posts": [{"id": pid, "username": u, "board": b, "message": m,
                    "timestamp": ts, "reply_to": rt}
                   for pid, u, b, m, ts, rt in posts],
        "users": {u: {"joined": j, "bio": bio or ""} for u, j, bio in user_rows},
        "messages": [{"sender": s, "recipient": r, "body": body,
                       "timestamp": ts, "is_read": bool(ir)}
                      for s, r, body, ts, ir in msg_rows],
        "reactions": [{"post_id": pid, "username": u, "emoji": e, "timestamp": ts}
                       for pid, u, e, ts in react_rows],
        "votes": [{"post_id": pid, "username": u, "value": v, "timestamp": ts}
                   for pid, u, v, ts in vote_rows],
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
    print(fmt_dim(f"Exported {len(data['posts'])} posts, {len(data['users'])} users, "
                  f"{len(data['messages'])} msgs, {len(data['reactions'])} reactions, "
                  f"{len(data['votes'])} votes to {filepath}"))


def cmd_import(filepath):
    try:
        with open(filepath) as f:
            data = json.load(f)
    except FileNotFoundError:
        print(fmt_err(f"{filepath} not found."))
        return
    except json.JSONDecodeError:
        print(fmt_err(f"{filepath} is not valid JSON."))
        return

    posts = data.get("posts", [])
    user_profiles = data.get("users", {})
    messages = data.get("messages", [])
    reactions = data.get("reactions", [])
    votes = data.get("votes", [])

    if not posts:
        print(fmt_dim("No posts to import."))
        return

    with engine.begin() as conn:
        all_usernames = sorted({p["username"] for p in posts})
        uid_map = {}
        for uname in all_usernames:
            row = conn.execute(text("SELECT id FROM users WHERE username = :u"), {"u": uname}).fetchone()
            if row:
                uid_map[uname] = row[0]
            else:
                profile = user_profiles.get(uname, {})
                uid_map[uname] = conn.execute(
                    text("INSERT INTO users (username, joined, bio) VALUES (:u, :j, :b)"),
                    {"u": uname, "j": profile.get("joined", posts[0]["timestamp"]),
                     "b": profile.get("bio", "")},
                ).lastrowid

        board_names = sorted({p.get("board", "general") for p in posts})
        bid_map = {}
        for bname in board_names:
            row = conn.execute(text("SELECT id FROM boards WHERE name = :n"), {"n": bname}).fetchone()
            bid_map[bname] = row[0] if row else conn.execute(
                text("INSERT INTO boards (name) VALUES (:n)"), {"n": bname}).lastrowid

        old_to_new = {}
        added, skipped = 0, 0
        for p in posts:
            board = p.get("board", "general")
            existing = conn.execute(
                text("SELECT p.id FROM posts p JOIN users u ON p.user_id = u.id "
                     "WHERE u.username = :u AND p.message = :m AND p.timestamp = :ts"),
                {"u": p["username"], "m": p["message"], "ts": p["timestamp"]},
            ).fetchone()
            if existing:
                if p.get("id") is not None:
                    old_to_new[p["id"]] = existing[0]
                skipped += 1
                continue
            reply_to = p.get("reply_to")
            new_reply = old_to_new.get(reply_to) if reply_to is not None else None
            new_id = conn.execute(
                text("INSERT INTO posts (user_id, board_id, message, timestamp, reply_to) "
                     "VALUES (:uid, :bid, :msg, :ts, :rt)"),
                {"uid": uid_map[p["username"]], "bid": bid_map[board],
                 "msg": p["message"], "ts": p["timestamp"], "rt": new_reply},
            ).lastrowid
            if p.get("id") is not None:
                old_to_new[p["id"]] = new_id
            added += 1

        msg_added = 0
        for m in messages:
            sid, rid = uid_map.get(m["sender"]), uid_map.get(m["recipient"])
            if sid and rid:
                conn.execute(
                    text("INSERT INTO messages (sender_id, recipient_id, body, timestamp, is_read) "
                         "VALUES (:s, :r, :b, :ts, :ir)"),
                    {"s": sid, "r": rid, "b": m["body"], "ts": m["timestamp"],
                     "ir": int(m.get("is_read", False))},
                )
                msg_added += 1

        react_added = 0
        for r in reactions:
            uid = uid_map.get(r["username"])
            new_pid = old_to_new.get(r["post_id"], r["post_id"])
            if uid:
                try:
                    conn.execute(
                        text("INSERT OR IGNORE INTO reactions (post_id, user_id, emoji, timestamp) "
                             "VALUES (:pid, :uid, :e, :ts)"),
                        {"pid": new_pid, "uid": uid, "e": r["emoji"], "ts": r["timestamp"]},
                    )
                    react_added += 1
                except Exception:
                    pass

        vote_added = 0
        for v in votes:
            uid = uid_map.get(v["username"])
            new_pid = old_to_new.get(v["post_id"], v["post_id"])
            if uid:
                try:
                    conn.execute(
                        text("INSERT OR IGNORE INTO votes (post_id, user_id, value, timestamp) "
                             "VALUES (:pid, :uid, :v, :ts)"),
                        {"pid": new_pid, "uid": uid, "v": v["value"], "ts": v["timestamp"]},
                    )
                    vote_added += 1
                except Exception:
                    pass

    print(fmt_dim(f"Import: {added} posts added, {skipped} skipped, "
                  f"{msg_added} msgs, {react_added} reactions, {vote_added} votes."))


# ── Interactive Mode ────────────────────────────────────────────

def interactive_mode():
    from games import games_menu, show_leaderboard

    print_banner()
    print(fmt_dim("Welcome to interactive mode!"))
    print()

    while True:
        try:
            username = input(paint("  Enter username: ", BOLD, BR_CYAN) if COLOR
                            else "  Enter username: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not username:
            continue
        with engine.begin() as conn:
            _get_or_create_user(conn, username)
        break

    with engine.connect() as conn:
        uid = _require_user(conn, username)
        unread = conn.execute(
            text("SELECT COUNT(*) FROM messages WHERE recipient_id = :uid AND is_read = 0"),
            {"uid": uid},
        ).fetchone()[0]
    print(fmt_ok(f"Logged in as {username}."))
    if unread > 0:
        print(paint(f"  You have {unread} unread message(s). Type 'inbox' to read.", BR_YELLOW))

    # Check for new achievements on login
    _notify_badges(check_achievements(username))
    print(f"  {paint('Type', DIM)} {paint('help', CYAN)} {paint('for commands.', DIM)}")
    print()

    prompt = paint(f"  {username}@bbs> ", BOLD, GREEN) if COLOR else f"  {username}@bbs> "
    while True:
        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{fmt_dim('Goodbye!')}")
            return

        if not line:
            continue

        parts = line.split(None, 2)
        cmd = parts[0].lower()

        if cmd in ("quit", "exit", "q"):
            print(fmt_dim("Goodbye!"))
            return
        elif cmd == "help":
            print_interactive_help()
        elif cmd == "whoami":
            print(fmt_dim(f"You are {username}."))
        elif cmd == "post":
            if len(parts) < 3:
                print(fmt_err("Usage: post <board> <message>"))
                continue
            cmd_post(username, parts[1], parts[2])
        elif cmd == "reply":
            sub = line.split(None, 2)
            if len(sub) < 3:
                print(fmt_err("Usage: reply <post_id> <message>"))
                continue
            try:
                reply_id = int(sub[1])
            except ValueError:
                print(fmt_err("post_id must be a number."))
                continue
            with engine.connect() as conn:
                parent = conn.execute(
                    text("SELECT b.name FROM posts p JOIN boards b ON p.board_id = b.id "
                         "WHERE p.id = :id"), {"id": reply_id},
                ).fetchone()
            if not parent:
                print(fmt_err(f"Post #{reply_id} not found."))
                continue
            cmd_post(username, parent[0], sub[2], reply_to=reply_id)
        elif cmd == "read":
            board = None
            sort_mode = "default"
            rest = parts[1] if len(parts) >= 2 else ""
            if rest in ("hot", "new", "top"):
                sort_mode = rest
            elif rest:
                board = rest
            cmd_read(board, sort_mode)
        elif cmd == "users":
            cmd_users()
        elif cmd == "boards":
            cmd_boards()
        elif cmd == "search":
            if len(parts) < 2:
                print(fmt_err("Usage: search <keyword>"))
                continue
            cmd_search(parts[1])
        elif cmd == "profile":
            cmd_profile(parts[1] if len(parts) >= 2 else username)
        elif cmd == "bio":
            if len(parts) < 2:
                print(fmt_err("Usage: bio <text>"))
                continue
            cmd_bio(username, line.split(None, 1)[1])
        elif cmd == "upvote":
            if len(parts) < 2:
                print(fmt_err("Usage: upvote <post_id>"))
                continue
            try:
                cmd_vote(username, int(parts[1]), +1)
            except ValueError:
                print(fmt_err("post_id must be a number."))
        elif cmd == "downvote":
            if len(parts) < 2:
                print(fmt_err("Usage: downvote <post_id>"))
                continue
            try:
                cmd_vote(username, int(parts[1]), -1)
            except ValueError:
                print(fmt_err("post_id must be a number."))
        elif cmd == "pin":
            if len(parts) < 2:
                print(fmt_err("Usage: pin <post_id>"))
                continue
            try:
                cmd_pin(username, int(parts[1]))
            except ValueError:
                print(fmt_err("post_id must be a number."))
        elif cmd == "dm":
            sub = line.split(None, 2)
            if len(sub) < 3:
                print(fmt_err("Usage: dm <user> <message>"))
                continue
            cmd_dm(username, sub[1], sub[2])
        elif cmd == "inbox":
            cmd_inbox(username)
        elif cmd == "sent":
            cmd_sent(username)
        elif cmd == "react":
            if len(parts) < 2:
                print(fmt_err("Usage: react <post_id> [emoji]"))
                continue
            try:
                pid = int(parts[1])
            except ValueError:
                print(fmt_err("post_id must be a number."))
                continue
            emoji = parts[2] if len(parts) >= 3 else "+1"
            cmd_react(username, pid, emoji)
        elif cmd == "trending":
            cmd_trending()
        elif cmd == "badges":
            cmd_badges(username)
        elif cmd == "games":
            games_menu(username)
        elif cmd == "leaderboard":
            show_leaderboard()
        elif cmd == "export":
            cmd_export(parts[1] if len(parts) >= 2 else "export.json")
        elif cmd == "import":
            if len(parts) < 2:
                print(fmt_err("Usage: import <file.json>"))
                continue
            cmd_import(parts[1])
        else:
            print(fmt_err(f"Unknown command: {cmd}. Type 'help' for commands."))


# ── CLI dispatch ────────────────────────────────────────────────

def main():
    init_db()
    args = sys.argv[1:]

    if not args:
        print_usage("bbs_db.py")
        sys.exit(1)

    cmd = args[0]

    if cmd == "interactive":
        interactive_mode()
    elif cmd == "tui":
        from tui import run_tui
        run_tui()
    elif cmd == "post" and len(args) >= 4:
        cmd_post(args[1], args[2], args[3])
    elif cmd == "reply" and len(args) >= 4:
        try:
            reply_id = int(args[1])
        except ValueError:
            print(fmt_err("post_id must be a number."))
            sys.exit(1)
        with engine.connect() as conn:
            parent = conn.execute(
                text("SELECT b.name FROM posts p JOIN boards b ON p.board_id = b.id "
                     "WHERE p.id = :id"), {"id": reply_id},
            ).fetchone()
        if not parent:
            print(fmt_err(f"Post #{reply_id} not found."))
            sys.exit(1)
        cmd_post(args[2], parent[0], args[3], reply_to=reply_id)
    elif cmd == "read":
        board = None
        sort_mode = "default"
        rest = args[1:]
        for a in rest:
            if a.startswith("--sort"):
                continue
            elif a in ("hot", "new", "top"):
                sort_mode = a
            else:
                board = a
        cmd_read(board, sort_mode)
    elif cmd == "users":
        cmd_users()
    elif cmd == "boards":
        cmd_boards()
    elif cmd == "search" and len(args) >= 2:
        cmd_search(args[1])
    elif cmd == "profile" and len(args) >= 2:
        cmd_profile(args[1])
    elif cmd == "bio" and len(args) >= 3:
        cmd_bio(args[1], args[2])
    elif cmd == "upvote" and len(args) >= 3:
        try:
            cmd_vote(args[1], int(args[2]), +1)
        except ValueError:
            print(fmt_err("post_id must be a number."))
    elif cmd == "downvote" and len(args) >= 3:
        try:
            cmd_vote(args[1], int(args[2]), -1)
        except ValueError:
            print(fmt_err("post_id must be a number."))
    elif cmd == "pin" and len(args) >= 3:
        try:
            cmd_pin(args[1], int(args[2]))
        except ValueError:
            print(fmt_err("post_id must be a number."))
    elif cmd == "dm" and len(args) >= 4:
        cmd_dm(args[1], args[2], args[3])
    elif cmd == "inbox" and len(args) >= 2:
        cmd_inbox(args[1])
    elif cmd == "sent" and len(args) >= 2:
        cmd_sent(args[1])
    elif cmd == "react" and len(args) >= 3:
        emoji = args[3] if len(args) >= 4 else "+1"
        try:
            cmd_react(args[1], int(args[2]), emoji)
        except ValueError:
            print(fmt_err("post_id must be a number."))
    elif cmd == "trending":
        cmd_trending()
    elif cmd == "badges" and len(args) >= 2:
        cmd_badges(args[1])
    elif cmd == "games" and len(args) >= 2:
        from games import games_menu
        games_menu(args[1])
    elif cmd == "leaderboard":
        from games import show_leaderboard
        show_leaderboard()
    elif cmd == "export":
        cmd_export(args[1] if len(args) >= 2 else "export.json")
    elif cmd == "import" and len(args) >= 2:
        cmd_import(args[1])
    else:
        print_usage("bbs_db.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
