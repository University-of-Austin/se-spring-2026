# BBS — Kyle Choy

**Tier: Gold**

## Setup

Requires Python 3.10+ and SQLAlchemy.

```bash
pip install sqlalchemy
```

No other dependencies. The JSON version (`bbs.py`) uses only the standard library.

## File structure

| File | Purpose |
|------|---------|
| `bbs.py` | Part A — JSON-backed BBS (stdlib only) |
| `db.py` | SQLAlchemy engine, FK enforcement, `init_db()` for table creation |
| `bbs_db.py` | Part B + Silver + Gold — SQLite-backed BBS with all extensions |
| `migrate.py` | Part C — one-shot JSON-to-SQLite migration |
| `README.md` | This file |

## Running

All scripts resolve data files relative to their own directory, so they work from any working directory.

### Part A — JSON storage

```bash
python3 bbs.py post <username> <message>
python3 bbs.py read
python3 bbs.py users
python3 bbs.py search <keyword>
```

Data is stored in `bbs.json`, a flat list of post objects.

### Part B — SQLite storage

```bash
python3 bbs_db.py post <username> <message>
python3 bbs_db.py read
python3 bbs_db.py users
python3 bbs_db.py search <keyword>
```

Tables are created automatically on first run. Data is stored in `bbs.db`.

### Part C — Migration

```bash
python3 migrate.py
```

Reads `bbs.json` and populates `bbs.db`. After migration, `bbs_db.py read` produces identical output to `bbs.py read`.

### Interactive mode

```bash
python3 bbs_db.py login <username>
```

Drops into a live BBS session with a `bbs>` prompt. No need to repeat your username or the script name on every command. Type `help` for available commands, `quit` to exit.

## Search: JSON vs SQL

In the JSON version, every search loads the entire file into memory, deserializes it, and iterates through every post to check for a substring match. The dataset has to fit in RAM, and every query pays the full cost of reading the file regardless of how many results there are.

The SQL version pushes the filter to the database engine:

```sql
SELECT u.username, p.message, p.timestamp
FROM posts p JOIN users u ON p.user_id = u.id
WHERE p.message LIKE :pattern
```

One query. The database handles the scan internally and only returns matching rows across the boundary.

At a million posts, the difference matters. The JSON file would be roughly 100MB+ of raw text that Python has to parse into dicts on every single read operation. Even a search that returns zero results pays the full deserialization cost. The SQL version never loads the full dataset into application memory — SQLite streams through the file on disk using its page cache. Both approaches are O(n) for a LIKE scan without indexing, but the constant factor is dramatically different: Python dict construction vs. SQLite's optimized C-level string comparison. If search performance became critical, you could add an FTS (full-text search) index to the SQLite version and bring it down to O(log n). There's no equivalent optimization path for the JSON version — you'd have to build your own index, at which point you've reinvented a database.

## Migration behavior

If `bbs.db` already contains data (any rows in the `users` table), `migrate.py` aborts with:

```
bbs.db already contains data. Delete bbs.db and retry.
```

Detection is simple: if `SELECT COUNT(*) FROM users` returns anything greater than zero, the migration refuses to proceed. This is intentional. A merge strategy (skipping duplicates, reconciling conflicts) adds complexity without clear benefit for a one-time migration. The safe behavior is to refuse and let the user decide — delete the database and re-migrate, or keep what's there. No silent data destruction.

The migration runs as a single transaction with three steps:

1. **Extract users.** Iterate through the flat JSON list and collect distinct usernames in first-seen order, recording each user's earliest post timestamp as their `created_at` value. This preserves the actual join date rather than using the migration runtime.
2. **Insert users.** Batch-insert into the `users` table. Usernames are normalized to lowercase to match the application's case-insensitive handling.
3. **Insert posts.** Build a `username → id` mapping from the newly created rows, then batch-insert posts with the correct `user_id` foreign keys.

If anything fails mid-migration, the transaction rolls back and `bbs.db` is left untouched.

## Database schema

```
users
├── id          INTEGER PRIMARY KEY
├── username    TEXT UNIQUE NOT NULL
├── bio         TEXT
└── created_at  TEXT NOT NULL

posts
├── id          INTEGER PRIMARY KEY
├── user_id     INTEGER NOT NULL → users(id)
├── message     TEXT NOT NULL
└── timestamp   TEXT NOT NULL

messages
├── id             INTEGER PRIMARY KEY
├── sender_id      INTEGER NOT NULL → users(id)
├── recipient_id   INTEGER NOT NULL → users(id)
├── message        TEXT NOT NULL
├── timestamp      TEXT NOT NULL
└── is_read        INTEGER NOT NULL DEFAULT 0
```

`users` is the single source of identity. `posts` and `messages` both reference it via foreign key. The `messages` table has two foreign keys into `users` — one for each side of the conversation.

## Silver: User profiles

**Commands:**

```bash
python3 bbs_db.py profile <username>    # View a profile
python3 bbs_db.py set-bio <username> <bio>  # Set bio text
```

In interactive mode: `profile` (defaults to your own), `profile <user>`, `bio <text>`.

**Schema change:** Added `bio TEXT` and `created_at TEXT NOT NULL` to the `users` table.

**Why profiles:** A BBS without identity is just a log file. Profiles give users a reason to come back — you can see when someone joined, how active they are, and what they've posted recently. The `created_at` field also enabled the migration to preserve real join dates, which turned out to be a meaningful data integrity decision.

The profile query uses correlated subqueries to fetch the post count and DM count in a single round trip:

```sql
SELECT u.username, u.created_at, u.bio,
       (SELECT COUNT(*) FROM posts WHERE user_id = u.id) AS post_count,
       (SELECT COUNT(*) FROM messages WHERE sender_id = u.id) AS dms_sent
FROM users u WHERE u.username = :username
```

## Gold: Private messages and interactive mode

### Private messages

**Commands:**

```bash
python3 bbs_db.py dm <from> <to> <message>   # Send a DM
python3 bbs_db.py inbox <username>            # View received messages
python3 bbs_db.py sent <username>             # View sent messages
```

In interactive mode: `dm <user> <message>`, `inbox`, `sent`.

**Schema change:** New `messages` table with `sender_id`, `recipient_id`, `message`, `timestamp`, and `is_read` (integer boolean, 0/1).

Both sender and recipient must be existing users. The inbox displays all messages chronologically, with `(new)` markers on unread ones and a count of new messages at the top. After viewing, unread messages are marked as read atomically within the same transaction. The second time you check your inbox, the markers are gone.

Profile pages show a user's DM sent count alongside their post count.

### Interactive mode

```bash
python3 bbs_db.py login <username>
```

Real BBSes were interactive sessions, not one-shot commands. You dialed in, logged on, and stayed connected. The `login` command recreates that: you get a persistent session with a `bbs>` prompt where your identity carries through every command. `post` doesn't need a username. `dm` doesn't need a sender. `profile` with no argument shows your own.

The session uses Python's `cmd.Cmd` module for the REPL loop, with ANSI escape codes for colored terminal output (navy blue UI chrome, gold usernames and highlights, gray timestamps). Color is only active in interactive mode — CLI output stays plain so it can be piped and diffed safely.

New users get a welcome message on first post pointing them to `login`, and a profile setup prompt when they first log in.

### Design decisions

**Usernames are case-insensitive.** All usernames are normalized to lowercase on input. `Alice`, `ALICE`, and `alice` are the same user. This prevents accidental duplicate accounts.

**DM recipients must already exist.** Posting creates your account, but you can't DM someone who hasn't posted yet. Auto-creating a recipient on DM would produce ghost accounts with no posts and no activity. If you want to reach someone, they need to exist on the board first.

**LIKE metacharacters are escaped in search.** If you search for a literal `%` or `_`, the query treats them as literal characters rather than SQL wildcards. Minor edge case, but correct.

**Foreign key enforcement is explicitly enabled.** SQLite disables foreign key constraints by default. `db.py` uses a SQLAlchemy connection event listener to run `PRAGMA foreign_keys = ON` on every connection, ensuring referential integrity is actually enforced at the database level.

**All data files resolve relative to the script, not the working directory.** `bbs.json`, `bbs.db`, and all imports work correctly regardless of where you invoke the scripts from. This was a deliberate choice after catching that `create_engine("sqlite:///bbs.db")` creates the database in the caller's CWD.

## Edge cases

- **Missing `bbs.json`** — `bbs.py read`/`users`/`search` treat it as empty (no output, no crash). `migrate.py` prints a clear error.
- **Empty `bbs.json` (`[]`)** — migration prints "No posts to migrate." and exits cleanly.
- **Corrupt or non-list JSON** — `bbs.py` and `migrate.py` catch `JSONDecodeError` and type mismatches with a clean error message.
- **Same username, many posts** — handled naturally. JSON version deduplicates with `dict.fromkeys`. Migration extracts distinct users before inserting.
- **Duplicate usernames with different casing** — normalized to lowercase on input across all entry points, including migration.
- **Database already has data on migration** — aborts rather than silently overwriting or producing duplicates.
- **Nonexistent user in `profile`/`set-bio`/`dm`/`inbox`/`sent`** — returns a clear error message with guidance.
- **LIKE wildcards in search terms** — `%` and `_` are escaped so they match literally.
- **Posts with identical timestamps** — secondary sort on `id ASC` ensures stable chronological ordering.
- **`die()` inside interactive mode** — `SystemExit` is caught by the session so errors print but don't kill the REPL.
