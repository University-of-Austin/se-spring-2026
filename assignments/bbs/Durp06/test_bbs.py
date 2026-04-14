"""Automated test suite for BBS (Gold tier).

Run:  python test_bbs.py
Exercises both JSON and SQLite backends plus all Gold features.
"""

import json
import os
import subprocess
import sys

PASSED = 0
FAILED = 0


def check(name, cond, detail=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print(f"  PASS  {name}")
    else:
        FAILED += 1
        msg = f"  FAIL  {name}"
        if detail:
            msg += f"  ({detail})"
        print(msg)


def run(cmd):
    env = {**os.environ, "NO_COLOR": "1"}
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=env)
    return result.returncode, result.stdout + result.stderr


def cleanup():
    for f in ["bbs.json", "bbs_users.json", "bbs.db", "export.json", "test_export.json"]:
        try:
            os.remove(f)
        except FileNotFoundError:
            pass


# ════════════════════════════════════════════════════════════════
# Part A: JSON backend
# ════════════════════════════════════════════════════════════════

def test_json():
    print("\n== Part A: JSON backend (bbs.py) ==\n")
    cleanup()

    rc, out = run('python bbs.py post alice general "Hello world"')
    check("post creates a message", rc == 0 and "Posted" in out)

    rc, out = run('python bbs.py post bob tech "Tech talk"')
    check("post second user", rc == 0 and "Posted" in out)

    with open("bbs.json") as f:
        posts = json.load(f)
    check("bbs.json has 2 posts", len(posts) == 2)
    check("post has required fields", all(k in posts[0] for k in ("username", "timestamp", "board", "message")))

    rc, out = run("python bbs.py read")
    check("read shows all posts", "alice" in out and "bob" in out)

    rc, out = run("python bbs.py read tech")
    check("read board filter works", "Tech talk" in out and "Hello world" not in out)

    rc, out = run('python bbs.py reply 1 bob "Hi Alice!"')
    check("reply works", rc == 0 and "Posted" in out)

    rc, out = run("python bbs.py read")
    check("reply indented under parent", "+-" in out)

    rc, out = run('python bbs.py reply 999 bob "nope"')
    check("reply to nonexistent post fails", rc != 0)

    rc, out = run("python bbs.py users")
    check("users lists both", "alice" in out and "bob" in out)

    rc, out = run("python bbs.py boards")
    check("boards shows both", "general" in out and "tech" in out)

    rc, out = run('python bbs.py search "Hello"')
    check("search finds match", "Hello world" in out)

    rc, out = run('python bbs.py search "xyznothing"')
    check("search miss", "No posts found" in out)

    run('python bbs.py bio alice "Test bio"')
    rc, out = run("python bbs.py profile alice")
    check("profile shows bio", "Test bio" in out)

    rc, out = run("python bbs.py profile nobody")
    check("profile nonexistent errors", "not found" in out.lower())


# ════════════════════════════════════════════════════════════════
# Part B: SQLite backend (base)
# ════════════════════════════════════════════════════════════════

def test_sqlite_base():
    print("\n== Part B: SQLite backend - base ==\n")
    cleanup()

    rc, out = run('python bbs_db.py post alice general "Hello from DB"')
    check("post creates message", rc == 0 and "Posted" in out)

    run('python bbs_db.py post bob tech "DB tech post"')

    rc, out = run("python bbs_db.py read")
    check("read shows all", "alice" in out and "bob" in out)

    rc, out = run("python bbs_db.py read tech")
    check("read board filter", "DB tech post" in out and "Hello from DB" not in out)

    run('python bbs_db.py reply 1 bob "Reply"')
    rc, out = run("python bbs_db.py read")
    check("reply indented", "+-" in out)

    rc, out = run("python bbs_db.py users")
    check("users lists both", "alice" in out and "bob" in out)

    rc, out = run("python bbs_db.py boards")
    check("boards lists both", "general" in out and "tech" in out)

    rc, out = run('python bbs_db.py search "Hello"')
    check("search finds match", "Hello from DB" in out)

    run('python bbs_db.py bio alice "DB bio"')
    rc, out = run("python bbs_db.py profile alice")
    check("profile shows bio", "DB bio" in out)


# ════════════════════════════════════════════════════════════════
# Part C: Migration
# ════════════════════════════════════════════════════════════════

def test_migration():
    print("\n== Part C: Migration ==\n")
    cleanup()

    run('python bbs.py post alice general "Migration test"')
    run('python bbs.py post bob tech "Second post"')
    run('python bbs.py reply 1 bob "Reply"')
    run('python bbs.py bio alice "Migrated bio"')

    rc, out = run("python migrate.py")
    check("migration completes", rc == 0 and "complete" in out.lower())

    rc, out = run("python bbs_db.py read")
    check("migrated posts readable", "Migration test" in out)
    check("migrated replies preserved", "+-" in out)

    rc, out = run("python bbs_db.py profile alice")
    check("migrated profile preserved", "Migrated bio" in out)

    rc, out = run("python migrate.py")
    check("migration is idempotent", rc == 0)


# ════════════════════════════════════════════════════════════════
# Gold: Private Messages
# ════════════════════════════════════════════════════════════════

def test_dms():
    print("\n== Gold: Private Messages ==\n")
    cleanup()

    run('python bbs_db.py post alice general "setup"')
    run('python bbs_db.py post bob general "setup"')

    rc, out = run('python bbs_db.py dm alice bob "Secret"')
    check("dm sends", "sent to bob" in out.lower())

    rc, out = run("python bbs_db.py inbox bob")
    check("inbox shows message", "Secret" in out)
    check("inbox shows NEW", "NEW" in out)

    rc, out = run("python bbs_db.py inbox bob")
    check("inbox marks read", "NEW" not in out)

    rc, out = run("python bbs_db.py sent alice")
    check("sent shows message", "Secret" in out)

    rc, out = run('python bbs_db.py dm alice nobody "hello"')
    check("dm to nonexistent user fails", "not found" in out.lower())


# ════════════════════════════════════════════════════════════════
# Gold: Reactions & Trending
# ════════════════════════════════════════════════════════════════

def test_reactions():
    print("\n== Gold: Reactions & Trending ==\n")
    cleanup()

    run('python bbs_db.py post alice general "Popular"')
    run('python bbs_db.py post bob general "Less popular"')

    rc, out = run("python bbs_db.py react alice 1")
    check("react works", "+1" in out)

    rc, out = run("python bbs_db.py react bob 1 fire")
    check("custom emoji", "fire" in out)

    rc, out = run("python bbs_db.py read")
    check("reactions display", "+1" in out and "fire" in out)

    rc, out = run("python bbs_db.py react alice 1 heart")
    check("reaction update", "updated" in out.lower())

    rc, out = run("python bbs_db.py trending")
    check("trending shows posts", "Popular" in out)


# ════════════════════════════════════════════════════════════════
# Gold: Upvote / Downvote
# ════════════════════════════════════════════════════════════════

def test_votes():
    print("\n== Gold: Upvote / Downvote ==\n")
    cleanup()

    run('python bbs_db.py post alice general "Vote me"')
    run('python bbs_db.py post bob general "Other"')

    rc, out = run("python bbs_db.py upvote alice 1")
    check("upvote works", "Upvoted" in out)

    rc, out = run("python bbs_db.py upvote bob 1")
    check("second upvote", "Upvoted" in out)

    rc, out = run("python bbs_db.py downvote alice 2")
    check("downvote works", "Downvoted" in out)

    rc, out = run("python bbs_db.py read")
    check("vote scores display", "+2" in out and "-1" in out)

    # Toggle off
    rc, out = run("python bbs_db.py upvote alice 1")
    check("vote toggle off", "removed" in out.lower())

    # Sort modes
    rc, out = run("python bbs_db.py read top")
    check("sort by top works", rc == 0 and "Vote me" in out)

    rc, out = run("python bbs_db.py read new")
    check("sort by new works", rc == 0)

    rc, out = run("python bbs_db.py read hot")
    check("sort by hot works", rc == 0)


# ════════════════════════════════════════════════════════════════
# Gold: Pinning
# ════════════════════════════════════════════════════════════════

def test_pinning():
    print("\n== Gold: Pinning ==\n")
    cleanup()

    run('python bbs_db.py post alice general "Normal post"')
    run('python bbs_db.py post bob general "Pin me"')

    rc, out = run("python bbs_db.py pin alice 2")
    check("pin works", "Pinned" in out)

    rc, out = run("python bbs_db.py read")
    check("pinned post shown first", out.index("PINNED") < out.index("Normal post"))

    rc, out = run("python bbs_db.py pin alice 2")
    check("unpin works", "Unpinned" in out)


# ════════════════════════════════════════════════════════════════
# Gold: Achievements
# ════════════════════════════════════════════════════════════════

def test_achievements():
    print("\n== Gold: Achievements ==\n")
    cleanup()

    rc, out = run('python bbs_db.py post alice general "First!"')
    check("first post badge awarded", "First Post" in out)

    rc, out = run("python bbs_db.py badges alice")
    check("badges command works", "First Post" in out)
    check("badge count shown", "1/9" in out)

    rc, out = run("python bbs_db.py profile alice")
    check("profile shows badges", "First Post" in out)


# ════════════════════════════════════════════════════════════════
# Gold: Import / Export
# ════════════════════════════════════════════════════════════════

def test_import_export():
    print("\n== Gold: Import / Export ==\n")
    cleanup()

    run('python bbs_db.py post alice general "Export test"')
    run('python bbs_db.py post bob tech "Another"')
    run('python bbs_db.py dm alice bob "Secret DM"')
    run('python bbs_db.py react alice 2 fire')
    run('python bbs_db.py upvote alice 1')

    rc, out = run("python bbs_db.py export test_export.json")
    check("export succeeds", "Exported" in out)

    with open("test_export.json") as f:
        data = json.load(f)
    check("export has posts", len(data["posts"]) == 2)
    check("export has messages", len(data["messages"]) == 1)
    check("export has reactions", len(data["reactions"]) == 1)
    check("export has votes", len(data["votes"]) == 1)

    os.remove("bbs.db")
    rc, out = run("python bbs_db.py import test_export.json")
    check("import succeeds", "Import" in out and "2 posts added" in out)

    rc, out = run("python bbs_db.py read")
    check("imported posts readable", "Export test" in out)

    rc, out = run("python bbs_db.py inbox bob")
    check("imported DMs preserved", "Secret DM" in out)


# ════════════════════════════════════════════════════════════════
# Gold: Games (menu only - can't play interactively)
# ════════════════════════════════════════════════════════════════

def test_games():
    print("\n== Gold: Door Games ==\n")
    cleanup()

    run('python bbs_db.py post alice general "setup"')

    # Just test menu appears and exits
    rc, out = run('printf "q\\n" | python bbs_db.py games alice')
    check("games menu shows", "Door Games" in out or "Trivia" in out)
    check("games menu has all 3 games", "Trivia" in out and "Hangman" in out and "Number" in out)

    # Test leaderboard with no scores
    rc, out = run("python bbs_db.py leaderboard")
    check("leaderboard works (empty)", "No scores" in out or "Leaderboard" in out)


# ════════════════════════════════════════════════════════════════
# Gold: Interactive Mode
# ════════════════════════════════════════════════════════════════

def test_interactive():
    print("\n== Gold: Interactive Mode ==\n")
    cleanup()

    commands = 'testuser\npost general "Hello"\nread\nupvote 1\nread\nbadges\nwhoami\nquit\n'
    env = {**os.environ, "NO_COLOR": "1"}
    result = subprocess.run(
        ["python", "bbs_db.py", "interactive"],
        input=commands, capture_output=True, text=True, env=env
    )
    out = result.stdout + result.stderr

    check("interactive starts", "Welcome" in out or "Enter username" in out)
    check("interactive login", "Logged in" in out)
    check("interactive post", "Posted" in out)
    check("interactive read", "Hello" in out)
    check("interactive upvote", "Upvoted" in out)
    check("interactive badges", "badges" in out.lower())
    check("interactive quit", "Goodbye" in out)


# ════════════════════════════════════════════════════════════════
# Gold: TUI (import only - can't test curses in subprocess)
# ════════════════════════════════════════════════════════════════

def test_tui_import():
    print("\n== Gold: TUI Module ==\n")
    rc, out = run('python -c "from tui import BBSTUI, run_tui; print(\'TUI OK\')"')
    check("TUI module imports", rc == 0 and "TUI OK" in out)


# ════════════════════════════════════════════════════════════════

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    test_json()
    test_sqlite_base()
    test_migration()
    test_dms()
    test_reactions()
    test_votes()
    test_pinning()
    test_achievements()
    test_import_export()
    test_games()
    test_interactive()
    test_tui_import()

    cleanup()

    print(f"\n{'=' * 40}")
    print(f"  {PASSED} passed, {FAILED} failed")
    print(f"{'=' * 40}")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
