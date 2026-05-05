"""Terminal display formatting for the BBS.

Handles ANSI color output, ASCII art banner, and all fmt_* helpers.
Respects NO_COLOR and FORCE_COLOR environment variables.
"""

import os
import sys

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
UNDERLINE = "\033[4m"

FG_BLACK = "\033[30m"
FG_RED = "\033[31m"
FG_GREEN = "\033[32m"
FG_YELLOW = "\033[33m"
FG_BLUE = "\033[34m"
FG_MAGENTA = "\033[35m"
FG_CYAN = "\033[36m"
FG_WHITE = "\033[37m"

BG_BLACK = "\033[40m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"

USER_COLORS = [FG_CYAN, FG_GREEN, FG_YELLOW, FG_MAGENTA, FG_BLUE, FG_RED]


def _color_enabled():
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def paint(text, *codes):
    if not _color_enabled() or not codes:
        return text
    return "".join(codes) + str(text) + RESET


def color_for(username):
    idx = sum(ord(c) for c in username) % len(USER_COLORS)
    return USER_COLORS[idx]


# ---------------------------------------------------------------------------
# ASCII art banner
# ---------------------------------------------------------------------------

BANNER = r"""
  ____  ____  ____    ____            _   _
 | __ )| __ )/ ___|  | __ ) _   _ ___| |_(_)_ __
 |  _ \|  _ \\___ \  |  _ \| | | / __| __| | '_ \
 | |_) | |_) |___) | | |_) | |_| \__ \ |_| | | | |
 |____/|____/|____/  |____/ \__,_|___/\__|_|_| |_|

              ╔═══════════════════════════╗
              ║   Welcome to the Board!   ║
              ║      v1.0 — Gold+         ║
              ╚═══════════════════════════╝
"""


def print_banner():
    if _color_enabled():
        lines = BANNER.strip().split("\n")
        for i, line in enumerate(lines):
            if i < 5:
                print(paint(line, FG_CYAN, BOLD))
            else:
                print(paint(line, FG_GREEN))
    else:
        print(BANNER.strip())
    print()


# ---------------------------------------------------------------------------
# Format helpers
# ---------------------------------------------------------------------------

def fmt_timestamp(ts):
    """Format an ISO timestamp to [YYYY-MM-DD HH:MM]."""
    if not ts:
        return ""
    return f"[{ts[:16].replace('T', ' ')}]"


def fmt_post(post, indent=0):
    """Format a single post dict for terminal display.

    Expected keys: timestamp, username, message, board (optional),
                   is_pinned (optional), vote_score (optional),
                   reactions (optional list of emoji strings).
    """
    prefix = "  " * indent
    ts = fmt_timestamp(post.get("timestamp", ""))
    user = post.get("username", "???")
    msg = post.get("message", "")
    parts = []

    # Pinned tag
    if post.get("is_pinned"):
        parts.append(paint("[PINNED]", FG_YELLOW, BOLD))

    # Timestamp and user
    parts.append(paint(ts, DIM))
    parts.append(paint(user + ":", color_for(user), BOLD))
    parts.append(msg)

    # Vote score
    score = post.get("vote_score")
    if score is not None and score != 0:
        if score > 0:
            parts.append(paint(f"[+{score}]", FG_GREEN))
        else:
            parts.append(paint(f"[{score}]", FG_RED))

    # Reactions
    reactions = post.get("reactions")
    if reactions:
        parts.append(" ".join(reactions))

    line = f"{prefix}" + " ".join(parts)
    return line


def fmt_post_with_id(post, indent=0):
    """Like fmt_post but prefixes with the post ID."""
    prefix = "  " * indent
    pid = post.get("id", "?")
    id_str = paint(f"#{pid}", DIM)
    rest = fmt_post(post, indent=0)
    return f"{prefix}{id_str} {rest}"


def fmt_board(name, post_count=None):
    """Format a board name for listing."""
    s = paint(f"  [{name}]", FG_YELLOW, BOLD)
    if post_count is not None:
        s += paint(f"  ({post_count} posts)", DIM)
    return s


def fmt_user(username, post_count=None):
    """Format a username for listing."""
    s = paint(f"  {username}", color_for(username), BOLD)
    if post_count is not None:
        s += paint(f"  ({post_count} posts)", DIM)
    return s


def fmt_profile(profile):
    """Format a user profile dict for display.

    Expected keys: username, joined, bio, post_count, badges (list of tuples).
    """
    lines = []
    user = profile.get("username", "???")
    lines.append(paint(f"═══ Profile: {user} ═══", color_for(user), BOLD))
    lines.append(f"  Joined:  {profile.get('joined', 'unknown')}")
    lines.append(f"  Posts:   {profile.get('post_count', 0)}")
    bio = profile.get("bio", "")
    if bio:
        lines.append(f"  Bio:     {bio}")
    avatar = profile.get("avatar_ascii", "")
    if avatar:
        lines.append(paint("  Avatar:", DIM))
        for aline in avatar.split("\n"):
            lines.append(paint(f"    {aline}", FG_GREEN))
    badges = profile.get("badges", [])
    if badges:
        badge_strs = [paint(f"[{b[0]}]", FG_YELLOW) for b in badges]
        lines.append(f"  Badges:  {' '.join(badge_strs)}")
    role = profile.get("role", "user")
    if role != "user":
        lines.append(f"  Role:    {paint(role.upper(), FG_RED, BOLD)}")
    return "\n".join(lines)


def fmt_dm(dm):
    """Format a DM dict for inbox display.

    Expected keys: id, sender, body, timestamp, is_read.
    """
    ts = fmt_timestamp(dm.get("timestamp", ""))
    sender = dm.get("sender", "???")
    body = dm.get("body", "")
    tag = paint("[NEW]", FG_RED, BOLD) + " " if not dm.get("is_read") else "      "
    return f"  {tag}{ts} {paint(sender, color_for(sender), BOLD)}: {body}"


def fmt_badge(badge, description):
    """Format a single badge."""
    return f"  {paint('[' + badge + ']', FG_YELLOW, BOLD)}  {description}"


def fmt_trending(rank, post):
    """Format a trending post with rank number."""
    score = post.get("trend_score", 0)
    medal = {1: paint("🥇", FG_YELLOW), 2: paint("🥈", DIM), 3: paint("🥉", FG_RED)}.get(rank, f"  {rank}.")
    ts = fmt_timestamp(post.get("timestamp", ""))
    user = post.get("username", "???")
    msg = post.get("message", "")
    score_str = paint(f"[score: {score:.1f}]", FG_GREEN)
    return f"  {medal} {ts} {paint(user, color_for(user), BOLD)}: {msg} {score_str}"


def fmt_leaderboard_entry(rank, entry):
    """Format a leaderboard entry."""
    medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
    user = entry.get("username", "???")
    score = entry.get("score", 0)
    return f"  {medal} {paint(user, color_for(user), BOLD)} — {paint(score, FG_YELLOW, BOLD)} pts"


def fmt_mod_action(action):
    """Format a moderation action log entry."""
    ts = fmt_timestamp(action.get("timestamp", ""))
    mod = action.get("mod", "???")
    target = action.get("target", "???")
    act = action.get("action", "???")
    reason = action.get("reason", "")
    s = f"  {ts} {paint(mod, FG_RED)}: {act} → {target}"
    if reason:
        s += f" ({reason})"
    return s


def fmt_attachment(filename):
    """Format an attachment indicator."""
    return paint(f"  📎 {filename}", DIM)


def fmt_scheduled(ts):
    """Format a scheduled post time."""
    return paint(f"  ⏰ Scheduled for {ts[:16].replace('T', ' ')}", FG_YELLOW)


# ---------------------------------------------------------------------------
# Interactive mode help
# ---------------------------------------------------------------------------

INTERACTIVE_HELP = """
{header}

{section_posts}
  post <board> <message>   Post to a board
  read [board]             Read posts (optionally filter by board)
  reply <id> <message>     Reply to a post
  search <keyword>         Search posts
  boards                   List all boards
  trending                 Show trending posts
  pin <id>                 Pin/unpin a post

{section_social}
  dm <user> <message>      Send a private message
  inbox                    View your inbox
  react <id> <emoji>       React to a post
  upvote <id>              Upvote a post
  downvote <id>            Downvote a post

{section_profile}
  profile [user]           View a profile
  bio <text>               Set your bio
  avatar <text>            Set your ASCII avatar
  badges                   View your badges
  users                    List all users

{section_fun}
  games                    Play door games
  leaderboard [game]       View high scores

{section_system}
  export [file]            Export DB to JSON
  import <file>            Import JSON to DB
  help                     Show this help
  quit / exit              Leave the BBS
"""


def print_interactive_help():
    help_text = INTERACTIVE_HELP.format(
        header=paint("═══ BBS Commands ═══", FG_CYAN, BOLD),
        section_posts=paint("── Posts ──", FG_GREEN, BOLD),
        section_social=paint("── Social ──", FG_GREEN, BOLD),
        section_profile=paint("── Profile ──", FG_GREEN, BOLD),
        section_fun=paint("── Fun ──", FG_GREEN, BOLD),
        section_system=paint("── System ──", FG_GREEN, BOLD),
    )
    print(help_text)
