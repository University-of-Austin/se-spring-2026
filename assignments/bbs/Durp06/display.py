"""Terminal display helpers with ANSI color support."""

import os
import sys

# ANSI escape codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

BR_RED = "\033[91m"
BR_GREEN = "\033[92m"
BR_YELLOW = "\033[93m"
BR_BLUE = "\033[94m"
BR_MAGENTA = "\033[95m"
BR_CYAN = "\033[96m"
BR_WHITE = "\033[97m"

_PALETTE = [BR_CYAN, BR_GREEN, BR_MAGENTA, BR_YELLOW, BR_RED, BR_BLUE]
_color_cache: dict[str, str] = {}


def _color_enabled() -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


COLOR = _color_enabled()


def paint(text: str, *codes: str) -> str:
    if not COLOR:
        return text
    return "".join(codes) + text + RESET


def color_for(username: str) -> str:
    if username not in _color_cache:
        _color_cache[username] = _PALETTE[len(_color_cache) % len(_PALETTE)]
    return _color_cache[username]


# ── Banner ──────────────────────────────────────────────────────

BANNER = r"""
   ___  ___  ___
  | _ )| _ )/ __|
  | _ \| _ \\__ \
  |___/|___/|___/
"""

BANNER_COLORED = [
    ("   ___  ___  ___", BR_CYAN),
    ("  | _ )| _ )/ __|", BR_BLUE),
    ("  | _ \\| _ \\\\__ \\", BLUE),
    ("  |___/|___/|___/", MAGENTA),
]


def print_banner() -> None:
    if COLOR:
        for line, clr in BANNER_COLORED:
            print(f"{clr}{line}{RESET}")
        print(f"  {DIM}Bulletin Board System{RESET}  {BR_YELLOW}v1.0{RESET}")
        print(f"  {DIM}{'-' * 28}{RESET}")
    else:
        for line in BANNER.strip("\n").splitlines():
            print(line)
        print("  Bulletin Board System  v1.0")
        print("  " + "-" * 28)
    print()


# ── Formatting helpers ──────────────────────────────────────────

def fmt_post(ts: str, board: str, pid: int, user: str, msg: str, depth: int = 0) -> str:
    indent = "  " * depth
    if depth > 0:
        indent = "  " * (depth - 1) + paint("+-", DIM)
    parts = [
        indent,
        paint(f"[{ts}]", DIM),
        " ",
        paint(f"[{board}]", YELLOW),
        " ",
        paint(f"#{pid}", DIM),
        " ",
        paint(user, BOLD, color_for(user)),
        ": ",
        paint(msg, WHITE),
    ]
    return "".join(parts)


def fmt_search_hit(ts: str, board: str, user: str, msg: str) -> str:
    return (
        f"{paint(f'[{ts}]', DIM)} "
        f"{paint(f'[{board}]', YELLOW)} "
        f"{paint(user, BOLD, color_for(user))}: "
        f"{paint(msg, WHITE)}"
    )


def fmt_board(name: str, count: int) -> str:
    return f"  {paint(name, BOLD, YELLOW)}  {paint(f'({count} posts)', DIM)}"


def fmt_user(username: str) -> str:
    return f"  {paint(username, BOLD, color_for(username))}"


def fmt_ok(msg: str) -> str:
    return paint(f"  {msg}", GREEN)


def fmt_err(msg: str) -> str:
    return paint(f"  Error: {msg}", BR_RED)


def fmt_dim(msg: str) -> str:
    return paint(f"  {msg}", DIM)


def print_header(title: str) -> None:
    print(f"\n  {paint(title, BOLD, BR_WHITE)}")
    print(f"  {paint('-' * len(title), DIM)}")


def print_profile(user: str, joined: str, posts: int, bio: str) -> None:
    sep = paint("-" * 30, DIM)
    print(sep)
    print(f"  {paint('User:', DIM)}    {paint(user, BOLD, color_for(user))}")
    print(f"  {paint('Joined:', DIM)}  {paint(joined, WHITE)}")
    print(f"  {paint('Posts:', DIM)}   {paint(str(posts), BR_YELLOW)}")
    bio_str = paint(bio, WHITE) if bio else paint("(none)", DIM)
    print(f"  {paint('Bio:', DIM)}     {bio_str}")
    print(sep)


def print_usage(script: str) -> None:
    print_banner()
    print(f"  {paint('Commands:', BOLD, BR_WHITE)}\n")
    cmds = [
        (f"python {script} post <user> <board> <msg>", "Post a message"),
        (f"python {script} reply <id> <user> <msg>", "Reply to a post"),
        (f"python {script} read [board]", "Read posts"),
        (f"python {script} users", "List users"),
        (f"python {script} boards", "List boards"),
        (f"python {script} search <keyword>", "Search posts"),
        (f"python {script} profile <user>", "View profile"),
        (f"python {script} bio <user> <text>", "Set bio"),
    ]
    for cmd, desc in cmds:
        print(f"  {paint(cmd, CYAN)}  {paint(desc, DIM)}")
    print()
