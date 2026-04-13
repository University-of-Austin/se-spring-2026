import os
import sys

# ANSI color codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Foreground colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# Bright foreground
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"


def _supports_color():
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


USE_COLOR = _supports_color()


def c(text, *codes):
    if not USE_COLOR:
        return text
    prefix = "".join(codes)
    return f"{prefix}{text}{RESET}"


# Cycling colors for usernames so each user stands out
_USER_COLORS = [BRIGHT_CYAN, BRIGHT_GREEN, BRIGHT_MAGENTA, BRIGHT_YELLOW, BRIGHT_RED, BRIGHT_BLUE]
_user_color_map = {}


def user_color(username):
    if username not in _user_color_map:
        _user_color_map[username] = _USER_COLORS[len(_user_color_map) % len(_USER_COLORS)]
    return _user_color_map[username]


SPHEAL_LINES = [
    (r"            #+++**++++++++**#@                           ", BRIGHT_CYAN),
    (r"           #+=---------====+++++**                       ", BRIGHT_CYAN),
    (r"        %#*=-----------======++===+**                    ", BRIGHT_CYAN),
    (r"     %##%*=-------===========+=======+#                  ", BRIGHT_BLUE),
    (r"  #*+==+*+=======+%=-*+================*%                ", BRIGHT_BLUE),
    (r"  *=-============*@@##+=================+#               ", BLUE),
    (r"  %+===============++=============..:===+*#              ", BLUE),
    (r"  =:=+*+=++=========+++==========-:..-=+++*              ", BLUE),
    (r" *.::::.:::-++++++++=::-===========-.:=++++*             ", BRIGHT_BLUE),
    (r"@-...........-..:-.........-+========+++++++@            ", WHITE),
    (r"+............-.=.............:=======+++++++*            ", WHITE),
    (r"-..............................:====--=+++++*            ", WHITE),
    (r"=................................-==+-=+++++*@           ", WHITE),
    (r"=.................................-++++++:++*@           ", WHITE),
    (r"#.................................:=++++=:.=*@@          ", WHITE),
    (r" -.................................-=++++-.+*++==*@      ", BRIGHT_CYAN),
    (r" *...............................:::=++++++*+++*++++==*% ", BRIGHT_CYAN),
    (r"  =............................:::::=+++++++++*++++++++=*", BRIGHT_BLUE),
    (r"   +:.......................::::::::=+++++*+++++++++++++%", BRIGHT_BLUE),
    (r"   *+-.................:::::::::::::-+++++++++++++++++*% ", BLUE),
    (r"  +:::--:.........:::::::::::::::::-+++++++++++++++**#%  ", BLUE),
    (r" #=====++=:::::::::::::::::::::::::::-*#**++++***##%     ", BLUE),
    (r"          %==--::::::::::::--::::......-*@@@@@           ", BRIGHT_CYAN),
    (r"               %+====------=+*=-........:+               ", BRIGHT_CYAN),
    (r"                                *==--:--=#               ", BRIGHT_CYAN),
]

SPHEAL_PLAIN = r"""
            #+++**++++++++**#@
           #+=---------====+++++**
        %#*=-----------======++===+**
     %##%*=-------===========+=======+#
  #*+==+*+=======+%=-*+================*%
  *=-============*@@##+=================+#
  %+===============++=============..:===+*#
  =:=+*+=++=========+++==========-:..-=+++*
 *.::::.:::-++++++++=::-===========-.:=++++*
@-...........-..:-.........-+========+++++++@
+............-.=.............:=======+++++++*
-..............................:====--=+++++*
=................................-==+-=+++++*@
=.................................-++++++:++*@
#.................................:=++++=:.=*@@
 -.................................-=++++-.+*++==*@
 *...............................:::=++++++*+++*++++==*%
  =............................:::::=+++++++++*++++++++=*
   +:.......................::::::::=+++++*+++++++++++++%
   *+-.................:::::::::::::-+++++++++++++++++*%
  +:::--:.........:::::::::::::::::-+++++++++++++++**#%
 #=====++=:::::::::::::::::::::::::::-*#**++++***##%
          %==--::::::::::::--::::......-*@@@@@
               %+====------=+*=-........:+
                                *==--:--=#
"""

TITLE_LINES = [
    " ____  ____  ____  ",
    "| __ )| __ )/ ___| ",
    "|  _ \\|  _ \\\\___ \\ ",
    "| |_) | |_) |___) |",
    "|____/|____/|____/ ",
]


def print_welcome():
    if USE_COLOR:
        # Print Spheal
        for line, color in SPHEAL_LINES:
            print(f"  {color}{line}{RESET}")
        print()
        # Print BBS title
        title_colors = [BRIGHT_CYAN, BRIGHT_BLUE, BLUE, BRIGHT_MAGENTA, MAGENTA]
        for i, line in enumerate(TITLE_LINES):
            color = title_colors[i % len(title_colors)]
            print(f"    {color}{line}{RESET}")
        print()
        print(f"    {DIM}Bulletin Board System{RESET}  {BRIGHT_YELLOW}v2.0{RESET}")
        print(f"    {DIM}{'=' * 30}{RESET}")
    else:
        print(SPHEAL_PLAIN.strip("\n"))
        print()
        for line in TITLE_LINES:
            print(f"    {line}")
        print()
        print("    Bulletin Board System  v2.0")
        print("    " + "=" * 30)
    print()


def fmt_post_line(ts, board, pid, username, message, indent=0):
    prefix = "  " * indent
    if indent > 0:
        connector = c("+-", DIM)
        prefix = "  " * (indent - 1) + connector
    ts_str = c(f"[{ts}]", DIM)
    board_str = c(f"[{board}]", YELLOW)
    id_str = c(f"#{pid}", DIM)
    user_str = c(username, BOLD, user_color(username))
    msg_str = c(message, WHITE)
    return f"{prefix}{ts_str} {board_str} {id_str} {user_str}: {msg_str}"


def fmt_search_line(ts, board, username, message):
    ts_str = c(f"[{ts}]", DIM)
    board_str = c(f"[{board}]", YELLOW)
    user_str = c(username, BOLD, user_color(username))
    msg_str = c(message, WHITE)
    return f"{ts_str} {board_str} {user_str}: {msg_str}"


def fmt_board_line(name, count):
    board_str = c(name, BOLD, YELLOW)
    count_str = c(f"({count} posts)", DIM)
    return f"  {board_str}  {count_str}"


def fmt_user_line(username):
    return f"  {c(username, BOLD, user_color(username))}"


def fmt_posted():
    return c("  Posted.", GREEN)


def fmt_error(msg):
    return c(f"  Error: {msg}", BRIGHT_RED)


def fmt_info(msg):
    return c(f"  {msg}", DIM)


def print_profile(username, joined, post_count, bio):
    sep = c("-" * 30, DIM)
    print(sep)
    print(f"  {c('User:', DIM)}    {c(username, BOLD, user_color(username))}")
    print(f"  {c('Joined:', DIM)}  {c(joined, WHITE)}")
    print(f"  {c('Posts:', DIM)}   {c(str(post_count), BRIGHT_YELLOW)}")
    bio_display = bio if bio else c("(no bio set)", DIM)
    if bio:
        bio_display = c(bio, WHITE)
    print(f"  {c('Bio:', DIM)}     {bio_display}")
    print(sep)


def print_usage(script_name):
    print_welcome()
    print(f"  {c('Commands:', BOLD, BRIGHT_WHITE)}")
    print()
    cmds = [
        (f"python {script_name} post <user> <board> <msg>", "Post a message to a board"),
        (f"python {script_name} reply <id> <user> <msg>", "Reply to a post"),
        (f"python {script_name} read [board]", "Read posts (optionally filter by board)"),
        (f"python {script_name} users", "List all users"),
        (f"python {script_name} boards", "List all boards"),
        (f"python {script_name} search <keyword>", "Search posts by keyword"),
        (f"python {script_name} profile <user>", "View a user's profile"),
        (f"python {script_name} bio <user> <text>", "Set your bio"),
        (f"python {script_name} export [file.json]", "Export DB to JSON"),
        (f"python {script_name} import <file.json>", "Import JSON into DB"),
    ]
    for cmd, desc in cmds:
        print(f"  {c(cmd, CYAN)}  {c(desc, DIM)}")
    print()


def print_section_header(title):
    print(f"\n  {c(title, BOLD, BRIGHT_WHITE)}")
    print(f"  {c('-' * len(title), DIM)}")
