# BBS — Bulletin Board System

A retro-inspired terminal bulletin board with JSON and SQLite backends, threaded conversations, private messaging, emoji reactions, user profiles, trending posts, and a full interactive terminal mode with colored output.

**Tier: Gold**

## Setup

```bash
# Install dependencies
pip install sqlalchemy rich

# That's it — everything else is Python standard library + SQLite
```

## How to Run

### Part A — JSON Storage

```bash
python bbs.py post <username> <message>     # Post a message
python bbs.py read                          # Read all messages
python bbs.py users                         # List all users
python bbs.py search <keyword>              # Search posts by keyword
```

### Part B — SQLite Storage (with Gold features)

```bash
# Core commands (same as Part A)
python bbs_db.py post <username> <message>
python bbs_db.py read
python bbs_db.py users
python bbs_db.py search <keyword>

# Threads
python bbs_db.py reply <post_id> <username> <message>

# Emoji reactions
python bbs_db.py react <post_id> <username> <emoji>

# User profiles
python bbs_db.py profile <username>
python bbs_db.py bio <username> <text>

# Private messages
python bbs_db.py dm <from> <to> <message>
python bbs_db.py inbox <username>

# Trending
python bbs_db.py trending

# Interactive mode (the full experience)
python bbs_db.py interactive
```

### Part C — Migration

```bash
python migrate.py    # Reads bbs.json → writes to bbs.db
```

## Search: JSON vs SQL

In the JSON version, every command starts by loading the entire `bbs.json` file into memory with `json.load()`. Search means iterating over every single post in Python and checking whether the keyword appears in the message string. For 100 posts this is instant. For a million posts, you're loading potentially hundreds of megabytes into RAM, then doing a linear scan through all of them — every single time someone searches.

The SQL version handles search with a single query: `SELECT ... FROM posts JOIN users ... WHERE message LIKE :pattern`. The database engine does the scanning internally, and it only returns the rows that match — not the entire dataset. For a million posts, the database can use optimizations like page-level I/O (it doesn't have to load the whole file to find a match) and could benefit from full-text search indexes if needed. The Python process never has to hold all million posts in memory. Beyond search, the normalized schema (separate `users` and `posts` tables linked by foreign keys) also means that updating a username only requires changing one row in the `users` table, rather than finding and editing every post in a JSON array.

## Migration Behavior

When `migrate.py` runs, it **wipes all existing data** in `bbs.db` (posts, users, reactions, and messages) and rebuilds from `bbs.json`. This is a destructive, full-replace migration.

I chose this approach because it's the simplest and most predictable: after migration, the database is guaranteed to be an exact mirror of the JSON source. There's no ambiguity about duplicate detection, merge conflicts, or partial state. The tradeoff is that any data created directly in the SQLite version (reactions, DMs, threads) will be lost — but since the migration's purpose is to bridge the JSON version into the database, this felt like the right default. If you need to preserve existing database data, back up `bbs.db` before running the migration.

## Gold Features

### Threads (schema change: `parent_id` on `posts`)
Posts can be replies to other posts. The `posts` table has a nullable `parent_id` column that references another post's `id` — a self-referential foreign key. When reading the board, replies are displayed indented under their parent with `└─` connectors. This required no new tables, just one additional column, which keeps the schema clean.

### Emoji Reactions (new table: `reactions`)
Users can react to any post with one of 15 emojis (heart, fire, thumbsup, etc.). A `reactions` table stores `(post_id, user_id, emoji)` with a unique constraint so the same user can't add the same emoji twice. Reacting again toggles it off. Reactions are displayed inline next to posts, and the `trending` command ranks posts by total reaction count.

Available emojis: `thumbsup`, `thumbsdown`, `heart`, `laugh`, `fire`, `wow`, `sad`, `clap`, `think`, `100`, `star`, `rocket`, `eyes`, `wave`, `skull`

### Private Messages (new table: `messages`)
Users can send direct messages to each other. The `messages` table has `sender_id`, `recipient_id`, a `read` boolean flag, and the message content. The `inbox` command shows both received and sent messages, with `[NEW]` tags on unread ones. Opening your inbox marks all received messages as read.

### User Profiles (schema change: `bio` and `created_at` on `users`)
Each user has a profile showing their join date, total post count, reactions received across all their posts, and an optional bio. This required adding `bio` and `created_at` columns to the `users` table.

### Interactive Mode
Running `python bbs_db.py interactive` launches a live session. You enter a username to "log in," then interact through a persistent `bbs>` prompt — no need to re-type `python bbs_db.py` for every command. On login, you're notified of unread DMs. The interface features an ASCII art welcome banner and colored output via the `rich` library (with graceful fallback to plain text if `rich` isn't installed).

### Trending
The `trending` command shows the top 10 most-reacted posts, ranked by total reaction count, with all their emoji reactions displayed. It's a single SQL query with `JOIN`, `GROUP BY`, and `ORDER BY` — the database does the heavy lifting.
