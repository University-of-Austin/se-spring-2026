"""Shared business logic for the BBS.

Every function takes a SQLAlchemy connection (`conn`) as its first argument.
The caller is responsible for transaction management (engine.begin() or similar).
All SQL uses text() with parameterized :param syntax — no string interpolation.
"""

import uuid
from datetime import datetime, timedelta
from sqlalchemy import text

# ---------------------------------------------------------------------------
# Badge definitions
# ---------------------------------------------------------------------------

BADGE_DEFS = {
    "First Post": "Made your first post",
    "Chatterbox": "Posted 10 or more messages",
    "Reply King": "Replied to 5 or more posts",
    "Board Explorer": "Posted in 3 or more boards",
    "Social Butterfly": "Sent 5 or more DMs",
    "Popular": "Received 10 or more reactions on posts",
    "Democracy!": "Cast 10 or more votes",
    "Gamer": "Played a door game",
    "High Roller": "Achieved a top-3 score in any game",
}

# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

def get_or_create_user(conn, username):
    """Get user ID for username, creating the user if needed. Returns user ID."""
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()
    if row:
        return row[0]
    conn.execute(
        text("INSERT INTO users (username, bio, joined) VALUES (:u, '', :j)"),
        {"u": username, "j": datetime.now().isoformat()},
    )
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()
    return row[0]


def require_user(conn, username):
    """Look up a user by name. Returns user ID or None."""
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()
    return row[0] if row else None


def get_user_profile(conn, username):
    """Return a dict with full profile info, or None if user not found."""
    row = conn.execute(
        text("SELECT id, username, bio, joined, avatar_ascii, role, is_banned FROM users WHERE username = :u"),
        {"u": username},
    ).fetchone()
    if not row:
        return None
    uid = row[0]
    post_count = conn.execute(
        text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"),
        {"uid": uid},
    ).fetchone()[0]
    badges = get_badges(conn, uid)
    return {
        "id": uid,
        "username": row[1],
        "bio": row[2] or "",
        "joined": row[3],
        "avatar_ascii": row[4] or "",
        "role": row[5] or "user",
        "is_banned": row[6],
        "post_count": post_count,
        "badges": badges,
    }


def update_bio(conn, username, bio_text):
    conn.execute(
        text("UPDATE users SET bio = :bio WHERE username = :u"),
        {"bio": bio_text, "u": username},
    )


def update_avatar(conn, username, ascii_art):
    conn.execute(
        text("UPDATE users SET avatar_ascii = :av WHERE username = :u"),
        {"av": ascii_art, "u": username},
    )


def set_user_role(conn, user_id, role):
    conn.execute(
        text("UPDATE users SET role = :r WHERE id = :uid"),
        {"r": role, "uid": user_id},
    )


def ban_user(conn, mod_id, target_user_id, reason=""):
    conn.execute(
        text("UPDATE users SET is_banned = 1 WHERE id = :uid"),
        {"uid": target_user_id},
    )
    log_mod_action(conn, mod_id, target_user_id, "ban", reason)


def unban_user(conn, mod_id, target_user_id):
    conn.execute(
        text("UPDATE users SET is_banned = 0 WHERE id = :uid"),
        {"uid": target_user_id},
    )
    log_mod_action(conn, mod_id, target_user_id, "unban", "")


def list_users(conn):
    """Return list of dicts with username and post_count."""
    rows = conn.execute(text("""
        SELECT u.username, COUNT(p.id) as post_count
        FROM users u LEFT JOIN posts p ON u.id = p.user_id
        GROUP BY u.username ORDER BY u.username
    """)).fetchall()
    return [{"username": r[0], "post_count": r[1]} for r in rows]


# ---------------------------------------------------------------------------
# Board management
# ---------------------------------------------------------------------------

def get_or_create_board(conn, name):
    """Get board ID for name, creating the board if needed."""
    row = conn.execute(
        text("SELECT id FROM boards WHERE name = :n"),
        {"n": name},
    ).fetchone()
    if row:
        return row[0]
    conn.execute(
        text("INSERT INTO boards (name) VALUES (:n)"),
        {"n": name},
    )
    row = conn.execute(
        text("SELECT id FROM boards WHERE name = :n"),
        {"n": name},
    ).fetchone()
    return row[0]


def list_boards(conn):
    """Return list of dicts with board name and post_count."""
    rows = conn.execute(text("""
        SELECT b.name, COUNT(p.id) as post_count
        FROM boards b LEFT JOIN posts p ON b.id = p.board_id
        GROUP BY b.name ORDER BY b.name
    """)).fetchall()
    return [{"name": r[0], "post_count": r[1]} for r in rows]


# ---------------------------------------------------------------------------
# Post management
# ---------------------------------------------------------------------------

def create_post(conn, user_id, board_id, message, reply_to=None, scheduled_at=None):
    """Create a new post and return its ID."""
    now = datetime.now().isoformat()
    conn.execute(
        text("""
            INSERT INTO posts (user_id, board_id, message, timestamp, reply_to, scheduled_at)
            VALUES (:uid, :bid, :msg, :ts, :rt, :sa)
        """),
        {"uid": user_id, "bid": board_id, "msg": message, "ts": now, "rt": reply_to, "sa": scheduled_at},
    )
    row = conn.execute(text("SELECT last_insert_rowid()")).fetchone()
    return row[0]


def get_posts(conn, board_name=None, sort_mode="default"):
    """Return list of post dicts, optionally filtered by board.

    sort_mode: 'default' (chronological), 'new', 'top', 'hot'
    """
    now = datetime.now().isoformat()

    if board_name:
        rows = conn.execute(text("""
            SELECT p.id, u.username, b.name as board, p.message, p.timestamp,
                   p.reply_to, p.is_pinned, p.is_locked, p.scheduled_at
            FROM posts p
            JOIN users u ON p.user_id = u.id
            JOIN boards b ON p.board_id = b.id
            WHERE b.name = :board AND (p.scheduled_at IS NULL OR p.scheduled_at <= :now)
            ORDER BY p.is_pinned DESC, p.timestamp ASC
        """), {"board": board_name, "now": now}).fetchall()
    else:
        rows = conn.execute(text("""
            SELECT p.id, u.username, b.name as board, p.message, p.timestamp,
                   p.reply_to, p.is_pinned, p.is_locked, p.scheduled_at
            FROM posts p
            JOIN users u ON p.user_id = u.id
            JOIN boards b ON p.board_id = b.id
            WHERE p.scheduled_at IS NULL OR p.scheduled_at <= :now
            ORDER BY p.is_pinned DESC, p.timestamp ASC
        """), {"now": now}).fetchall()

    posts = []
    for r in rows:
        post = {
            "id": r[0], "username": r[1], "board": r[2], "message": r[3],
            "timestamp": r[4], "reply_to": r[5], "is_pinned": r[6],
            "is_locked": r[7], "scheduled_at": r[8],
        }
        posts.append(post)

    # Enrich with vote scores and reactions
    vote_counts = get_vote_counts(conn)
    reaction_counts = get_reaction_counts(conn)
    for p in posts:
        p["vote_score"] = vote_counts.get(p["id"], 0)
        p["reactions"] = reaction_counts.get(p["id"], [])

    # Sort
    if sort_mode == "new":
        posts.sort(key=lambda p: p["timestamp"], reverse=True)
    elif sort_mode == "top":
        posts.sort(key=lambda p: p["vote_score"], reverse=True)
    elif sort_mode == "hot":
        posts.sort(key=lambda p: _hot_score(p), reverse=True)

    return posts


def _hot_score(post):
    """Calculate a trending score combining votes, reactions, and recency."""
    score = post.get("vote_score", 0) + len(post.get("reactions", []))
    try:
        age_hours = (datetime.now() - datetime.fromisoformat(post["timestamp"])).total_seconds() / 3600
    except (ValueError, KeyError):
        age_hours = 9999
    # Bonus for posts less than 24h old
    if age_hours < 24:
        score += max(0, 10 - age_hours / 2.4)
    return score


def search_posts(conn, keyword):
    """Search posts by keyword using SQL LIKE."""
    now = datetime.now().isoformat()
    rows = conn.execute(text("""
        SELECT p.id, u.username, b.name as board, p.message, p.timestamp,
               p.reply_to, p.is_pinned
        FROM posts p
        JOIN users u ON p.user_id = u.id
        JOIN boards b ON p.board_id = b.id
        WHERE p.message LIKE :kw AND (p.scheduled_at IS NULL OR p.scheduled_at <= :now)
        ORDER BY p.timestamp ASC
    """), {"kw": f"%{keyword}%", "now": now}).fetchall()
    return [
        {"id": r[0], "username": r[1], "board": r[2], "message": r[3],
         "timestamp": r[4], "reply_to": r[5], "is_pinned": r[6]}
        for r in rows
    ]


def pin_post(conn, post_id):
    """Toggle pin status on a post. Returns new pin state."""
    row = conn.execute(
        text("SELECT is_pinned FROM posts WHERE id = :pid"),
        {"pid": post_id},
    ).fetchone()
    if not row:
        return None
    new_val = 0 if row[0] else 1
    conn.execute(
        text("UPDATE posts SET is_pinned = :v WHERE id = :pid"),
        {"v": new_val, "pid": post_id},
    )
    return bool(new_val)


def lock_post(conn, post_id):
    """Toggle lock status on a post. Returns new lock state."""
    row = conn.execute(
        text("SELECT is_locked FROM posts WHERE id = :pid"),
        {"pid": post_id},
    ).fetchone()
    if not row:
        return None
    new_val = 0 if row[0] else 1
    conn.execute(
        text("UPDATE posts SET is_locked = :v WHERE id = :pid"),
        {"v": new_val, "pid": post_id},
    )
    return bool(new_val)


def delete_post(conn, post_id):
    """Delete a post by ID. Returns True if deleted."""
    conn.execute(text("DELETE FROM reactions WHERE post_id = :pid"), {"pid": post_id})
    conn.execute(text("DELETE FROM votes WHERE post_id = :pid"), {"pid": post_id})
    conn.execute(text("DELETE FROM attachments WHERE post_id = :pid"), {"pid": post_id})
    conn.execute(text("UPDATE posts SET reply_to = NULL WHERE reply_to = :pid"), {"pid": post_id})
    result = conn.execute(text("DELETE FROM posts WHERE id = :pid"), {"pid": post_id})
    return result.rowcount > 0


def get_post_by_id(conn, post_id):
    """Get a single post by ID."""
    row = conn.execute(text("""
        SELECT p.id, u.username, b.name as board, p.message, p.timestamp,
               p.reply_to, p.is_pinned, p.is_locked, p.user_id
        FROM posts p
        JOIN users u ON p.user_id = u.id
        JOIN boards b ON p.board_id = b.id
        WHERE p.id = :pid
    """), {"pid": post_id}).fetchone()
    if not row:
        return None
    return {
        "id": row[0], "username": row[1], "board": row[2], "message": row[3],
        "timestamp": row[4], "reply_to": row[5], "is_pinned": row[6],
        "is_locked": row[7], "user_id": row[8],
    }


def publish_scheduled_posts(conn):
    """No-op marker — scheduled posts are filtered by timestamp in get_posts()."""
    pass


# ---------------------------------------------------------------------------
# Reactions
# ---------------------------------------------------------------------------

def add_reaction(conn, user_id, post_id, emoji):
    """Add or remove a reaction. Returns status message."""
    existing = conn.execute(
        text("SELECT id FROM reactions WHERE post_id = :pid AND user_id = :uid AND emoji = :e"),
        {"pid": post_id, "uid": user_id, "e": emoji},
    ).fetchone()
    if existing:
        conn.execute(text("DELETE FROM reactions WHERE id = :rid"), {"rid": existing[0]})
        return f"Removed {emoji} reaction."
    conn.execute(
        text("INSERT INTO reactions (post_id, user_id, emoji) VALUES (:pid, :uid, :e)"),
        {"pid": post_id, "uid": user_id, "e": emoji},
    )
    return f"Reacted with {emoji}."


def get_reaction_counts(conn):
    """Return {post_id: [emoji_str, ...]} for display."""
    rows = conn.execute(text("""
        SELECT post_id, emoji, COUNT(*) as cnt
        FROM reactions GROUP BY post_id, emoji
    """)).fetchall()
    result = {}
    for r in rows:
        entry = f"{r[1]}×{r[2]}" if r[2] > 1 else r[1]
        result.setdefault(r[0], []).append(entry)
    return result


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------

def cast_vote(conn, user_id, post_id, value):
    """Cast or toggle a vote (+1 or -1). Returns status message."""
    existing = conn.execute(
        text("SELECT id, value FROM votes WHERE post_id = :pid AND user_id = :uid"),
        {"pid": post_id, "uid": user_id},
    ).fetchone()
    if existing:
        if existing[1] == value:
            conn.execute(text("DELETE FROM votes WHERE id = :vid"), {"vid": existing[0]})
            return "Vote removed."
        conn.execute(
            text("UPDATE votes SET value = :v WHERE id = :vid"),
            {"v": value, "vid": existing[0]},
        )
        return "Vote changed."
    conn.execute(
        text("INSERT INTO votes (post_id, user_id, value) VALUES (:pid, :uid, :v)"),
        {"pid": post_id, "uid": user_id, "v": value},
    )
    return "Voted."


def get_vote_counts(conn):
    """Return {post_id: net_score} for all posts."""
    rows = conn.execute(text("""
        SELECT post_id, SUM(value) as score FROM votes GROUP BY post_id
    """)).fetchall()
    return {r[0]: r[1] for r in rows}


def get_trending(conn, limit=10):
    """Return top trending posts."""
    posts = get_posts(conn, sort_mode="hot")
    # Only root posts (not replies) for trending
    root_posts = [p for p in posts if not p.get("reply_to")]
    return root_posts[:limit]


# ---------------------------------------------------------------------------
# Private messages
# ---------------------------------------------------------------------------

def send_dm(conn, sender_id, recipient_id, body):
    now = datetime.now().isoformat()
    conn.execute(
        text("INSERT INTO messages (sender_id, recipient_id, body, timestamp, is_read) VALUES (:s, :r, :b, :ts, 0)"),
        {"s": sender_id, "r": recipient_id, "b": body, "ts": now},
    )


def get_inbox(conn, user_id):
    rows = conn.execute(text("""
        SELECT m.id, u.username as sender, m.body, m.timestamp, m.is_read
        FROM messages m JOIN users u ON m.sender_id = u.id
        WHERE m.recipient_id = :uid
        ORDER BY m.timestamp DESC
    """), {"uid": user_id}).fetchall()
    return [
        {"id": r[0], "sender": r[1], "body": r[2], "timestamp": r[3], "is_read": r[4]}
        for r in rows
    ]


def get_sent(conn, user_id):
    rows = conn.execute(text("""
        SELECT m.id, u.username as recipient, m.body, m.timestamp, m.is_read
        FROM messages m JOIN users u ON m.recipient_id = u.id
        WHERE m.sender_id = :uid
        ORDER BY m.timestamp DESC
    """), {"uid": user_id}).fetchall()
    return [
        {"id": r[0], "recipient": r[1], "body": r[2], "timestamp": r[3], "is_read": r[4]}
        for r in rows
    ]


def mark_read(conn, user_id):
    """Mark all messages in user's inbox as read."""
    conn.execute(
        text("UPDATE messages SET is_read = 1 WHERE recipient_id = :uid AND is_read = 0"),
        {"uid": user_id},
    )


def count_unread(conn, user_id):
    row = conn.execute(
        text("SELECT COUNT(*) FROM messages WHERE recipient_id = :uid AND is_read = 0"),
        {"uid": user_id},
    ).fetchone()
    return row[0]


# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------

def check_achievements(conn, user_id):
    """Check and award any new badges for the user. Returns list of newly awarded badge names."""
    awarded = []

    # First Post
    pc = conn.execute(text("SELECT COUNT(*) FROM posts WHERE user_id = :uid"), {"uid": user_id}).fetchone()[0]
    if pc >= 1:
        awarded += _try_award(conn, user_id, "First Post")
    if pc >= 10:
        awarded += _try_award(conn, user_id, "Chatterbox")

    # Reply King
    rc = conn.execute(text("SELECT COUNT(*) FROM posts WHERE user_id = :uid AND reply_to IS NOT NULL"), {"uid": user_id}).fetchone()[0]
    if rc >= 5:
        awarded += _try_award(conn, user_id, "Reply King")

    # Board Explorer
    bc = conn.execute(text("SELECT COUNT(DISTINCT board_id) FROM posts WHERE user_id = :uid"), {"uid": user_id}).fetchone()[0]
    if bc >= 3:
        awarded += _try_award(conn, user_id, "Board Explorer")

    # Social Butterfly
    dc = conn.execute(text("SELECT COUNT(*) FROM messages WHERE sender_id = :uid"), {"uid": user_id}).fetchone()[0]
    if dc >= 5:
        awarded += _try_award(conn, user_id, "Social Butterfly")

    # Popular
    rxc = conn.execute(text("""
        SELECT COUNT(*) FROM reactions r
        JOIN posts p ON r.post_id = p.id
        WHERE p.user_id = :uid
    """), {"uid": user_id}).fetchone()[0]
    if rxc >= 10:
        awarded += _try_award(conn, user_id, "Popular")

    # Democracy!
    vc = conn.execute(text("SELECT COUNT(*) FROM votes WHERE user_id = :uid"), {"uid": user_id}).fetchone()[0]
    if vc >= 10:
        awarded += _try_award(conn, user_id, "Democracy!")

    # Gamer
    gc = conn.execute(text("SELECT COUNT(*) FROM high_scores WHERE user_id = :uid"), {"uid": user_id}).fetchone()[0]
    if gc >= 1:
        awarded += _try_award(conn, user_id, "Gamer")

    # High Roller
    top3 = conn.execute(text("""
        SELECT COUNT(*) FROM (
            SELECT user_id, game, score,
                   ROW_NUMBER() OVER (PARTITION BY game ORDER BY score DESC) as rn
            FROM high_scores
        ) WHERE rn <= 3 AND user_id = :uid
    """), {"uid": user_id}).fetchone()[0]
    if top3 >= 1:
        awarded += _try_award(conn, user_id, "High Roller")

    return awarded


def _try_award(conn, user_id, badge):
    """Try to award a badge. Returns [badge] if newly awarded, [] if already had it."""
    existing = conn.execute(
        text("SELECT id FROM achievements WHERE user_id = :uid AND badge = :b"),
        {"uid": user_id, "b": badge},
    ).fetchone()
    if existing:
        return []
    conn.execute(
        text("INSERT INTO achievements (user_id, badge, description, awarded) VALUES (:uid, :b, :d, :a)"),
        {"uid": user_id, "b": badge, "d": BADGE_DEFS[badge], "a": datetime.now().isoformat()},
    )
    return [badge]


def get_badges(conn, user_id):
    rows = conn.execute(
        text("SELECT badge, description, awarded FROM achievements WHERE user_id = :uid ORDER BY awarded"),
        {"uid": user_id},
    ).fetchall()
    return [(r[0], r[1], r[2]) for r in rows]


# ---------------------------------------------------------------------------
# Import / Export
# ---------------------------------------------------------------------------

def export_all(conn):
    """Export all data to a JSON-serializable dict."""
    users = conn.execute(text("SELECT id, username, bio, joined, avatar_ascii, role FROM users")).fetchall()
    boards = conn.execute(text("SELECT id, name FROM boards")).fetchall()
    posts = conn.execute(text("""
        SELECT p.id, u.username, b.name, p.message, p.timestamp, p.reply_to, p.is_pinned
        FROM posts p JOIN users u ON p.user_id = u.id JOIN boards b ON p.board_id = b.id
        ORDER BY p.id
    """)).fetchall()
    msgs = conn.execute(text("""
        SELECT m.id, s.username, r.username, m.body, m.timestamp, m.is_read
        FROM messages m
        JOIN users s ON m.sender_id = s.id
        JOIN users r ON m.recipient_id = r.id
        ORDER BY m.id
    """)).fetchall()
    rxns = conn.execute(text("""
        SELECT r.id, r.post_id, u.username, r.emoji
        FROM reactions r JOIN users u ON r.user_id = u.id
    """)).fetchall()
    vts = conn.execute(text("""
        SELECT v.id, v.post_id, u.username, v.value
        FROM votes v JOIN users u ON v.user_id = u.id
    """)).fetchall()

    return {
        "users": [{"username": r[1], "bio": r[2], "joined": r[3], "avatar_ascii": r[4], "role": r[5]} for r in users],
        "boards": [{"name": r[1]} for r in boards],
        "posts": [{"id": r[0], "username": r[1], "board": r[2], "message": r[3], "timestamp": r[4], "reply_to": r[5], "is_pinned": r[6]} for r in posts],
        "messages": [{"sender": r[1], "recipient": r[2], "body": r[3], "timestamp": r[4], "is_read": r[5]} for r in msgs],
        "reactions": [{"post_id": r[1], "username": r[2], "emoji": r[3]} for r in rxns],
        "votes": [{"post_id": r[1], "username": r[2], "value": r[3]} for r in vts],
    }


def import_all(conn, data):
    """Import data from a JSON dict. Wipes existing data first. Returns stats dict."""
    # Clear in FK order
    conn.execute(text("DELETE FROM reactions"))
    conn.execute(text("DELETE FROM votes"))
    conn.execute(text("DELETE FROM attachments"))
    conn.execute(text("DELETE FROM messages"))
    conn.execute(text("DELETE FROM mod_actions"))
    conn.execute(text("DELETE FROM sessions"))
    conn.execute(text("DELETE FROM achievements"))
    conn.execute(text("DELETE FROM high_scores"))
    conn.execute(text("DELETE FROM posts"))
    conn.execute(text("DELETE FROM boards"))
    conn.execute(text("DELETE FROM users"))

    stats = {"users": 0, "boards": 0, "posts": 0, "messages": 0, "reactions": 0, "votes": 0}

    # Users
    uid_map = {}
    for u in data.get("users", []):
        conn.execute(
            text("INSERT INTO users (username, bio, joined, avatar_ascii, role) VALUES (:u, :b, :j, :a, :r)"),
            {"u": u["username"], "b": u.get("bio", ""), "j": u.get("joined", datetime.now().isoformat()),
             "a": u.get("avatar_ascii", ""), "r": u.get("role", "user")},
        )
        uid_map[u["username"]] = conn.execute(text("SELECT last_insert_rowid()")).fetchone()[0]
        stats["users"] += 1

    # Boards
    bid_map = {}
    for b in data.get("boards", []):
        conn.execute(text("INSERT INTO boards (name) VALUES (:n)"), {"n": b["name"]})
        bid_map[b["name"]] = conn.execute(text("SELECT last_insert_rowid()")).fetchone()[0]
        stats["boards"] += 1

    # Posts — need ID remapping for reply_to
    old_to_new = {}
    for p in data.get("posts", []):
        username = p["username"]
        if username not in uid_map:
            uid_map[username] = get_or_create_user(conn, username)
            stats["users"] += 1
        board = p.get("board", "general")
        if board not in bid_map:
            bid_map[board] = get_or_create_board(conn, board)
            stats["boards"] += 1
        rt = old_to_new.get(p.get("reply_to"))
        conn.execute(
            text("""INSERT INTO posts (user_id, board_id, message, timestamp, reply_to, is_pinned)
                     VALUES (:uid, :bid, :msg, :ts, :rt, :pin)"""),
            {"uid": uid_map[username], "bid": bid_map[board], "msg": p["message"],
             "ts": p["timestamp"], "rt": rt, "pin": p.get("is_pinned", 0)},
        )
        new_id = conn.execute(text("SELECT last_insert_rowid()")).fetchone()[0]
        old_to_new[p.get("id")] = new_id
        stats["posts"] += 1

    # Messages
    for m in data.get("messages", []):
        s_username = m["sender"]
        r_username = m["recipient"]
        if s_username not in uid_map:
            uid_map[s_username] = get_or_create_user(conn, s_username)
        if r_username not in uid_map:
            uid_map[r_username] = get_or_create_user(conn, r_username)
        conn.execute(
            text("INSERT INTO messages (sender_id, recipient_id, body, timestamp, is_read) VALUES (:s, :r, :b, :ts, :rd)"),
            {"s": uid_map[s_username], "r": uid_map[r_username], "b": m["body"],
             "ts": m["timestamp"], "rd": m.get("is_read", 0)},
        )
        stats["messages"] += 1

    # Reactions
    for rx in data.get("reactions", []):
        pid = old_to_new.get(rx.get("post_id"))
        username = rx["username"]
        if pid and username in uid_map:
            conn.execute(
                text("INSERT OR IGNORE INTO reactions (post_id, user_id, emoji) VALUES (:pid, :uid, :e)"),
                {"pid": pid, "uid": uid_map[username], "e": rx["emoji"]},
            )
            stats["reactions"] += 1

    # Votes
    for v in data.get("votes", []):
        pid = old_to_new.get(v.get("post_id"))
        username = v["username"]
        if pid and username in uid_map:
            conn.execute(
                text("INSERT OR IGNORE INTO votes (post_id, user_id, value) VALUES (:pid, :uid, :v)"),
                {"pid": pid, "uid": uid_map[username], "v": v["value"]},
            )
            stats["votes"] += 1

    return stats


# ---------------------------------------------------------------------------
# Attachments
# ---------------------------------------------------------------------------

def add_attachment(conn, post_id, filename, filepath, content_type=""):
    now = datetime.now().isoformat()
    conn.execute(
        text("""INSERT INTO attachments (post_id, filename, filepath, content_type, uploaded_at)
                 VALUES (:pid, :fn, :fp, :ct, :ua)"""),
        {"pid": post_id, "fn": filename, "fp": filepath, "ct": content_type, "ua": now},
    )
    conn.execute(text("UPDATE posts SET has_attachment = 1 WHERE id = :pid"), {"pid": post_id})


def get_attachments(conn, post_id):
    rows = conn.execute(
        text("SELECT id, filename, filepath, content_type, uploaded_at FROM attachments WHERE post_id = :pid"),
        {"pid": post_id},
    ).fetchall()
    return [{"id": r[0], "filename": r[1], "filepath": r[2], "content_type": r[3], "uploaded_at": r[4]} for r in rows]


# ---------------------------------------------------------------------------
# Moderation
# ---------------------------------------------------------------------------

def log_mod_action(conn, mod_id, target_user_id, action, reason=""):
    now = datetime.now().isoformat()
    conn.execute(
        text("INSERT INTO mod_actions (mod_id, target_user_id, action, reason, timestamp) VALUES (:m, :t, :a, :r, :ts)"),
        {"m": mod_id, "t": target_user_id, "a": action, "r": reason, "ts": now},
    )


def get_mod_log(conn, limit=50):
    rows = conn.execute(text("""
        SELECT ma.id, m.username as mod, t.username as target, ma.action, ma.reason, ma.timestamp
        FROM mod_actions ma
        JOIN users m ON ma.mod_id = m.id
        JOIN users t ON ma.target_user_id = t.id
        ORDER BY ma.timestamp DESC LIMIT :lim
    """), {"lim": limit}).fetchall()
    return [{"id": r[0], "mod": r[1], "target": r[2], "action": r[3], "reason": r[4], "timestamp": r[5]} for r in rows]


def is_admin_or_mod(conn, user_id):
    row = conn.execute(
        text("SELECT role FROM users WHERE id = :uid"),
        {"uid": user_id},
    ).fetchone()
    return row and row[0] in ("admin", "mod")


# ---------------------------------------------------------------------------
# Sessions (for web auth)
# ---------------------------------------------------------------------------

def create_session(conn, user_id):
    """Create a new session token. Returns the token string."""
    token = uuid.uuid4().hex
    now = datetime.now()
    expires = (now + timedelta(days=7)).isoformat()
    conn.execute(
        text("INSERT INTO sessions (user_id, token, created_at, expires_at) VALUES (:uid, :t, :c, :e)"),
        {"uid": user_id, "t": token, "c": now.isoformat(), "e": expires},
    )
    return token


def validate_session(conn, token):
    """Validate a session token. Returns user_id or None."""
    row = conn.execute(
        text("SELECT user_id, expires_at FROM sessions WHERE token = :t"),
        {"t": token},
    ).fetchone()
    if not row:
        return None
    if row[1] < datetime.now().isoformat():
        conn.execute(text("DELETE FROM sessions WHERE token = :t"), {"t": token})
        return None
    return row[0]


def expire_session(conn, token):
    conn.execute(text("DELETE FROM sessions WHERE token = :t"), {"t": token})


# ---------------------------------------------------------------------------
# High scores (for games)
# ---------------------------------------------------------------------------

def save_score(conn, user_id, game, score):
    now = datetime.now().isoformat()
    conn.execute(
        text("INSERT INTO high_scores (user_id, game, score, timestamp) VALUES (:uid, :g, :s, :ts)"),
        {"uid": user_id, "g": game, "s": score, "ts": now},
    )


def get_leaderboard(conn, game=None, limit=10):
    if game:
        rows = conn.execute(text("""
            SELECT u.username, hs.score, hs.timestamp
            FROM high_scores hs JOIN users u ON hs.user_id = u.id
            WHERE hs.game = :g
            ORDER BY hs.score DESC LIMIT :lim
        """), {"g": game, "lim": limit}).fetchall()
    else:
        rows = conn.execute(text("""
            SELECT u.username, hs.game, hs.score, hs.timestamp
            FROM high_scores hs JOIN users u ON hs.user_id = u.id
            ORDER BY hs.score DESC LIMIT :lim
        """), {"lim": limit}).fetchall()
    if game:
        return [{"username": r[0], "score": r[1], "timestamp": r[2]} for r in rows]
    return [{"username": r[0], "game": r[1], "score": r[2], "timestamp": r[3]} for r in rows]
