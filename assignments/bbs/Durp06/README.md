# BBS - Bulletin Board System

**Tier: Silver**

## Setup

```bash
pip install sqlalchemy
```

Python 3.9+ required.

## How to Run

### Part A: JSON Version

```bash
python bbs.py post <username> <board> <message>
python bbs.py reply <post_id> <username> <message>
python bbs.py read [board]
python bbs.py users
python bbs.py boards
python bbs.py search <keyword>
python bbs.py profile <username>
python bbs.py bio <username> <bio_text>
```

Data lives in `bbs.json` (posts) and `bbs_users.json` (profiles).

### Part B: SQLite Version

```bash
python bbs_db.py post <username> <board> <message>
python bbs_db.py reply <post_id> <username> <message>
python bbs_db.py read [board]
python bbs_db.py users
python bbs_db.py boards
python bbs_db.py search <keyword>
python bbs_db.py profile <username>
python bbs_db.py bio <username> <bio_text>
```

Data stored in `bbs.db`. Tables are auto-created on first run.

### Part C: Migration

```bash
python migrate.py
```

Reads `bbs.json` (and `bbs_users.json` if present) and populates `bbs.db`.

## Search: JSON vs SQL

The JSON version loads every post into memory and scans them one by one — O(n)
on the total number of posts, and the whole dataset has to be parsed each time.

The SQL version pushes the search into SQLite with a `LIKE` query. The database
only touches the rows it needs and can leverage internal page-level caching.
For a million posts the JSON path would be parsing hundreds of megabytes per
query, while SQL stays fast and memory-light. Adding a full-text index
(`FTS5`) would make it faster still.

## Migration Behavior

`migrate.py` **wipes the database** before inserting, making it idempotent:
running it twice gives the same result. This is intentional — the migration
is a one-time conversion, and wiping prevents duplicates if you run it again
by accident. Reply relationships and board assignments are preserved with
correctly mapped foreign keys.

## Silver Features

### 1. Topics/Boards

Every post belongs to a named board. Replies inherit the parent's board.

```bash
python bbs_db.py post alice general "Hello everyone!"
python bbs_db.py boards      # list boards with post counts
python bbs_db.py read tech   # filter to one board
```

**Schema:** `boards` table (`id`, `name` UNIQUE) plus `board_id` FK on `posts`.

### 2. Threads

Reply to any post by ID. Replies display indented under their parent:

```
[2026-04-13 10:00] [general] #1 alice: Hello!
+-[2026-04-13 10:01] [general] #2 bob: Hi Alice!
  +-[2026-04-13 10:02] [general] #3 alice: How's it going?
```

**Schema:** nullable `reply_to` column on `posts` referencing `posts(id)`.

### 3. User Profiles

Auto-created on first post. Includes join date, post count, and settable bio.

```bash
python bbs_db.py profile alice
python bbs_db.py bio alice "Retro computing fan"
```

**Schema:** `bio` (TEXT) and `joined` (TEXT) columns on `users`.

### 4. Colored Terminal Output

ANSI-colored output with per-user color coding, dimmed metadata, yellow board
tags, and tree connectors for threads. Respects `NO_COLOR` / `FORCE_COLOR`
environment variables. All display logic is in `display.py`.
