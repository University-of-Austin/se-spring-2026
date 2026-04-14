# BBS - Bulletin Board System

**Tier: Gold**

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
python bbs_db.py post <user> <board> <msg>
python bbs_db.py reply <post_id> <user> <msg>
python bbs_db.py read [board]
python bbs_db.py users
python bbs_db.py boards
python bbs_db.py search <keyword>
python bbs_db.py profile <user>
python bbs_db.py bio <user> <text>
python bbs_db.py dm <from> <to> <msg>
python bbs_db.py inbox <user>
python bbs_db.py sent <user>
python bbs_db.py react <user> <post_id> [emoji]
python bbs_db.py trending
python bbs_db.py export [file.json]
python bbs_db.py import <file.json>
python bbs_db.py interactive
```

Data stored in `bbs.db`. Tables are auto-created on first run.

### Part C: Migration

```bash
python migrate.py
```

Reads `bbs.json` (and `bbs_users.json` if present) and populates `bbs.db`.

## Search: JSON vs SQL

The JSON version loads every post into memory and scans them one by one -- O(n)
on the total number of posts, and the whole dataset has to be parsed each time.
Even a simple keyword search requires deserializing the entire file, iterating
through every message, and doing a case-insensitive string match in Python.

The SQL version pushes the search into SQLite with a `LIKE` query. The database
only touches the rows it needs and can leverage internal page-level caching.
For a million posts the JSON path would be parsing hundreds of megabytes per
query, while SQL stays fast and memory-light. Adding a full-text index (`FTS5`)
would make it faster still. The difference is fundamental: with JSON, the
application does all the work; with SQL, the database engine does the heavy
lifting using optimized C code and disk-level I/O strategies that Python can't
match.

## Migration Behavior

`migrate.py` **wipes the database** before inserting, making it idempotent:
running it twice gives the same result. This is intentional -- the migration
is a one-time conversion, and wiping prevents duplicates if you run it again
by accident. Reply relationships and board assignments are preserved with
correctly mapped foreign keys. User profiles (bio, join date) from
`bbs_users.json` are also carried over.

If `bbs.db` already exists, all rows in `posts`, `boards`, and `users` are
deleted before the import. I chose this over "skip duplicates" because
duplicate detection is fragile (what if the message text is the same but the
user is different?) and over "error out" because that would make the script
annoying to re-run during development. A clean wipe-and-reload is the simplest
correct behavior for a one-time migration.

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

## Gold Features

### 5. Interactive Mode

Instead of one-shot commands, `python bbs_db.py interactive` drops you into a
live BBS session with a `username@bbs>` prompt. You log in once and then run
commands without re-typing your username. The session checks for unread DMs on
login and shows a notification. All commands from the one-shot CLI are available
in shorter form (e.g., `post general "hello"` instead of
`python bbs_db.py post alice general "hello"`).

This required no schema changes -- it's a REPL loop around the existing command
functions, but it changes the feel of the program from a CLI tool to something
that actually feels like dialing into a BBS.

### 6. Private Messages

Users can send direct messages to each other, check their inbox (with unread
markers), and view sent messages.

```bash
python bbs_db.py dm alice bob "Hey, want to collaborate?"
python bbs_db.py inbox bob       # shows [NEW] on unread messages
python bbs_db.py sent alice      # shows messages alice sent
```

In interactive mode: `dm bob "Hey!"`, `inbox`, `sent`.

**Schema:** new `messages` table with `sender_id` (FK->users), `recipient_id`
(FK->users), `body`, `timestamp`, and `is_read` (integer flag). Messages are
marked as read when the recipient views their inbox.

### 7. Post Reactions & Trending

Users can react to any post with a custom emoji tag (defaults to `+1`). Each
user gets one reaction per post (reacting again updates the emoji). Reactions
display inline next to posts when reading.

```bash
python bbs_db.py react alice 1         # reacts [+1] to post #1
python bbs_db.py react bob 1 fire      # reacts [fire] to post #1
python bbs_db.py trending              # shows top posts by reaction count
```

The `trending` command ranks posts by total reaction count, breaking ties by
recency. This is deliberately simple -- a real trending algorithm would
incorporate time-decay, but for a BBS with a small community, raw popularity
is the right signal.

**Schema:** new `reactions` table with `post_id` (FK->posts), `user_id`
(FK->users), `emoji`, `timestamp`, and a `UNIQUE(post_id, user_id)` constraint
to enforce one-reaction-per-user-per-post.

### 8. Import / Export

Full round-trip serialization. `export` dumps the entire database (posts, users,
messages, reactions) to a JSON file. `import` loads a JSON file back in,
skipping duplicate posts and merging new data.

```bash
python bbs_db.py export backup.json    # dump everything
python bbs_db.py import backup.json    # load it back
```

This goes beyond the migration script -- it's a complete backup/restore system
that handles all Gold-tier data (including DMs and reactions), not just the
base posts and users.
