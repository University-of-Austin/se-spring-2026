# BBS — fullystackedglitch

A terminal bulletin board system built for the UATX Software Engineering course.

## Setup

```bash
# From this directory
python bbs.py post alice "Hello world"   # Part A (JSON)
python bbs_db.py post alice "Hello"      # Part B (SQLite)
python migrate.py                        # Part C (migration)
```

The venv already has SQLAlchemy installed. Activate it or invoke Python directly:

```bash
source venv/bin/activate
```

No other dependencies beyond the standard library (Part A) and SQLAlchemy (Parts B/C).

## Tier

**Gold** — threaded replies (Silver) plus an interactive REPL mode (Gold).

## Part A commands

```
python bbs.py post <username> <message>
python bbs.py read
python bbs.py users
python bbs.py search <keyword>
```

## Part B commands

```
python bbs_db.py post <username> <message>
python bbs_db.py reply <post_id> <username> <message>   # Silver feature
python bbs_db.py read
python bbs_db.py users
python bbs_db.py search <keyword>
python bbs_db.py                                        # Gold: interactive mode
```

## Search: JSON vs SQL

In `bbs.py`, search loads the entire `bbs.json` file into memory and iterates
over every post with a Python `in` check. Every search is O(n) in both time and
memory — for a million posts you'd be reading and parsing tens or hundreds of
megabytes before you see a single result. There's no way to short-circuit or
index the data.

In `bbs_db.py`, the search is a single SQL `LIKE` query pushed down to SQLite.
The database engine scans only the relevant column and returns only matching
rows; your Python process never loads the rest. More importantly, if you added
a full-text index (e.g., SQLite FTS5), searches could become sub-millisecond
regardless of table size. With a million posts the SQL version stays fast;
the JSON version becomes unusable.

## migrate.py behavior

`migrate.py` reads `bbs.json` and inserts records into `bbs.db`.

- **Duplicate users:** `INSERT OR IGNORE` — if the username already exists in
  the `users` table it is reused; no error, no duplicate row.
- **Duplicate posts:** before inserting each post, the script checks for an
  existing row with the same `user_id`, `message`, and `timestamp`. If one is
  found the post is skipped and counted as "already present". This means
  running `migrate.py` twice is safe — idempotent — without wiping existing
  data.
- **bbs.db already has data:** data already in the database is left untouched.
  Only genuinely new posts (not matching the triple above) are inserted.

I chose skip-duplicates over wipe-and-reload because Claude tells me it's the safer default:
`bbs_db.py` can create replies that never existed in `bbs.json`,
and a wipe-and-reload would destroy them. Skip-duplicates lets the database
grow independently of the JSON source, and lets me re-run the migration at
any time without worrying about losing data.

## Silver feature: Threads

`bbs_db.py` supports threaded replies. The `posts` table gains a `parent_id`
column (`INTEGER REFERENCES posts(id)`, `NULL` for top-level posts).

```sql
-- schema addition
parent_id INTEGER REFERENCES posts(id)
```

The `reply` command looks up the target post ID, creates/reuses the author, and
inserts a child post:

```bash
python bbs_db.py post alice "Hello everyone"     # post id 1
python bbs_db.py reply 1 bob "Hey Alice!"        # reply to post 1
python bbs_db.py reply 1 carol "Welcome, Alice!" # another reply to post 1
python bbs_db.py read
# [2026-04-19 10:00] alice: Hello everyone
#   [2026-04-19 10:01] bob: Hey Alice!
#   [2026-04-19 10:02] carol: Welcome, Alice!
```

`read` fetches all posts in timestamp order, builds a parent→children map in
Python, and does a depth-first traversal to print each thread tree with two
spaces of indentation per level. Arbitrary nesting depth is supported.

Search operates only on message text and returns flat results (no indentation),
which keeps it consistent with Part A's output format.

## Gold feature: Interactive mode

Running `python bbs_db.py` with no arguments drops you into a live `bbs>`
prompt. You enter your username once at the start of the session and then
run commands without re-typing your name. Commands mirror the one-shot CLI:
`post`, `reply`, `read`, `users`, `search`, plus a `help` menu and `quit`/`exit`.

The REPL loop dispatches to the same underlying functions as the CLI, so both
modes share the database layer and query logic.