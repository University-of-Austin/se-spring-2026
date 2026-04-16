# BBS — Bulletin Board System

A terminal-based bulletin board system built in Python, inspired by the dial-up BBSes of the 1980s–90s.

---

## Setup

**Requirements:** Python 3.8+

Install dependencies:
```bash
pip install sqlalchemy rich
```

No other setup needed. Both `bbs.py` (JSON) and `bbs_db.py` (SQLite) create their storage files automatically on first use.

---

## Part A: JSON Version (`bbs.py`)

```bash
python bbs.py post <username> <message>   # Post a message
python bbs.py read                         # Read all messages
python bbs.py users                        # List users
python bbs.py search <keyword>             # Search messages
```

Data is stored in `bbs.json` in the current directory.

---

## Part B: SQLite Version (`bbs_db.py`)

Same four core commands, plus Gold-tier extensions:

```bash
python bbs_db.py post <username> <message>            # Post a message
python bbs_db.py read                                  # Read all messages (with threads)
python bbs_db.py users                                 # List users with post counts
python bbs_db.py search <keyword>                      # Search (highlights matches)
python bbs_db.py reply <post_id> <username> <message>  # Reply to a post
python bbs_db.py profile <username>                    # View user profile
python bbs_db.py setbio <username> <bio>               # Set user bio
python bbs_db.py                                       # Interactive mode (bbs> prompt)
```

Data is stored in `bbs.db` (SQLite) in the current directory.

---

## Part C: Migration

```bash
python migrate.py   # Reads bbs.json, populates bbs.db
```

See the [Migration Behavior](#migration-behavior) section below.

---

## Tier: Gold

This submission targets the **Gold** tier.

---

## Search: JSON vs. SQL

**JSON version (`bbs.py`):** Search loads the entire `bbs.json` file into memory, then iterates over every post object to check whether the keyword appears in the message string. This is an O(n) linear scan — every single post is examined regardless of what you're looking for. For a small BBS this is fine, but at a million posts the file could be hundreds of megabytes. Loading it on every search call would be slow and memory-hungry, and there's no way to make it faster short of building your own in-memory index.

**SQL version (`bbs_db.py`):** Search uses a single parameterized query with `LIKE :keyword`. The database engine executes this server-side and only returns matching rows. At a million posts SQLite would still do a full table scan for a `LIKE '%word%'` pattern (since leading wildcards prevent B-tree index use), but it does so inside a native C engine rather than Python, and it never loads all data into the Python process. For a production BBS you'd switch to SQLite's FTS5 full-text search extension, which builds an inverted index and turns keyword searches into O(log n) lookups instead of O(n) scans.

The fundamental difference: the JSON version moves all the data to the code; the SQL version moves the query to the data. That distinction only matters at scale, but at scale it matters enormously.

---

## Migration Behavior

`migrate.py` is **idempotent**: you can run it multiple times against the same `bbs.db` without duplicating data.

**Users:** Uses `INSERT OR IGNORE` on the `username` column (which has a `UNIQUE` constraint). If the user already exists, the insert is silently skipped.

**Posts:** Before inserting each post, the script checks whether a row with the same `(user_id, message, timestamp)` triple already exists. If so, it skips the post. This means that if you add new posts to `bbs.json` and re-run the migration, only the new posts are inserted.

**Timestamps:** The original `timestamp` values from `bbs.json` are preserved exactly — the database does not overwrite them with the current time.

Why idempotent? Re-running a migration is a common operational pattern (e.g., if the first run partially failed, or if the JSON file was updated). An idempotent migration can be retried safely without corrupting data.

---

## Gold Features

### Threads (Reply to Posts)
Posts have an optional `parent_id` foreign key referencing another post in the same table. This is a self-referential relationship that lets any post become the root of a thread. The `read` command displays replies indented under their parent with a `↳` prefix.

**Schema change:** Added `parent_id INTEGER REFERENCES posts(id)` to the `posts` table (defaults to `NULL` for top-level posts).

### User Profiles
Each user has a `bio` field and a `created_at` timestamp. The `profile` command displays their join date, post count, reply count, and bio. The `setbio` command lets them update their bio.

**Schema change:** Added `bio TEXT NOT NULL DEFAULT ''` and `created_at TEXT NOT NULL` to the `users` table.

### Rich Terminal Output
Uses the `rich` library for colored output, an ASCII art banner, formatted tables, and keyword highlighting in search results. The visual style is intentional — the retro green-on-black color scheme is a nod to the original CRT terminals that BBS users actually sat in front of.

### Interactive Mode
Running `python bbs_db.py` with no arguments drops into a persistent `bbs>` prompt. Uses Python's `shlex.split` to correctly handle quoted arguments (so `post alice "Hello world"` works as expected). Type `help` for commands, `quit` to exit.

---

## Database Schema

```sql
CREATE TABLE users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT    UNIQUE NOT NULL,
    bio        TEXT    NOT NULL DEFAULT '',
    created_at TEXT    NOT NULL
);

CREATE TABLE posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    message    TEXT    NOT NULL,
    timestamp  TEXT    NOT NULL,
    parent_id  INTEGER REFERENCES posts(id)   -- NULL for top-level posts
);
```
