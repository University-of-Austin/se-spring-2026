# BBS - Bulletin Board System

**Tier: Silver**

## Setup

```bash
pip install sqlalchemy
```

No other dependencies are needed. Python 3.9+ is required.

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

Data is stored in `bbs.json` (posts) and `bbs_users.json` (profiles).

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

Data is stored in `bbs.db`. Tables are created automatically on first run.

### Part C: Migration

```bash
python migrate.py
```

Reads `bbs.json` (and `bbs_users.json` if present) and populates `bbs.db`.

## Search: JSON vs SQL

In the JSON version, search loads the entire `bbs.json` file into memory, deserializes it, and loops through every single post to check if the keyword appears in the message. This is O(n) on the number of posts, and the entire dataset must be held in memory.

In the SQL version, the database engine handles the search with a `LIKE` query. The database reads only the relevant rows and can use internal optimizations. With a million posts, the JSON version would need to load and parse a massive file on every search (potentially hundreds of megabytes), while the SQL version would run a single indexed query without loading the entire dataset into application memory. Adding an index on the message column could further speed up SQL searches.

## Migration Behavior

When `migrate.py` runs, it **wipes existing data** in `bbs.db` (deletes all rows from `posts`, `boards`, and `users`) before inserting the migrated data. This ensures a clean, idempotent migration: running it multiple times always produces the same result. I chose this approach because the migration is meant to be a one-time conversion from JSON to SQLite, and wiping prevents duplicate entries if you accidentally run it twice. Thread reply relationships, board assignments, and user profiles from the JSON files are preserved with correctly mapped foreign keys.

## Silver Features

### 1. Topics/Boards

Posts belong to named boards. When posting, you specify a board:

```bash
python bbs_db.py post alice general "Hello everyone!"
python bbs_db.py post bob tech "Anyone using SQLite?"
python bbs_db.py boards          # List all boards with post counts
python bbs_db.py read tech        # Read only posts in the "tech" board
python bbs_db.py read             # Read all posts across all boards
```

Replies automatically inherit the board of their parent post.

**Schema change:** A new `boards` table (`id`, `name` UNIQUE) and a `board_id` foreign key on the `posts` table.

### 2. Threads

Users can reply to any existing post by its ID:

```bash
python bbs_db.py post alice general "Hello, is anyone out there?"
python bbs_db.py reply 1 bob "Hey Alice! Welcome to the board."
python bbs_db.py reply 2 alice "Thanks Bob!"
```

When reading posts, replies are displayed indented under their parent:

```
[2026-04-12 14:01] [general] (#1) alice: Hello, is anyone out there?
  [2026-04-12 14:02] [general] (#2) bob: Hey Alice! Welcome to the board.
    [2026-04-12 14:03] [general] (#3) alice: Thanks Bob!
```

**Schema change:** A nullable `reply_to` column on `posts` that references `posts(id)`.

### 3. User Profiles

Users have profiles with a join date (auto-set on first post), post count, and a settable bio:

```bash
python bbs_db.py profile alice    # View a user's profile
python bbs_db.py bio alice "Retro computing enthusiast"
python bbs_db.py profile alice    # Now shows the bio
```

Output:

```
User: alice
Joined: 2026-04-12 14:01
Posts: 3
Bio: Retro computing enthusiast
```

**Schema change:** Added `bio` (TEXT, default empty) and `joined` (TEXT, timestamp) columns to the `users` table.

### 4. ASCII Art Welcome Screen & Colored Output

All terminal output uses ANSI escape codes for color. A gradient ASCII art BBS banner displays on `read` and when running with no arguments. Features:

- **Color-coded usernames** - each user gets a unique persistent color for easy scanning
- **Dimmed timestamps and IDs** - metadata stays visible but doesn't compete with content
- **Yellow board tags** - boards stand out in post listings
- **Green confirmations** / **red errors** - clear feedback on actions
- **Styled profiles** - boxed profile display with labeled fields
- **Thread connectors** - `+-` prefixes on replies for visual threading
- **NO_COLOR / FORCE_COLOR support** - respects the `NO_COLOR` environment variable to disable colors, or `FORCE_COLOR` to enable them in non-TTY contexts

All color logic lives in `display.py`, shared by both `bbs.py` and `bbs_db.py`.
