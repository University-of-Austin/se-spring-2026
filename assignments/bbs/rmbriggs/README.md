# BBS — Micah Briggs

## Setup

Python 3.9+ required. Install dependencies:

```bash
pip install sqlalchemy rich
```

No other setup needed. Data files (`bbs.json`, `bbs.db`) are created automatically on first use.

---

## How to Run

### Part A — JSON storage (`bbs.py`)

```bash
python bbs.py post <username> <message>   # Post a message
python bbs.py read                         # Read all messages
python bbs.py users                        # List all users
python bbs.py search <keyword>             # Search posts by keyword
```

### Part B — SQLite storage (`bbs_db.py`)

```bash
python bbs_db.py post <username> <message>          # Post a message
python bbs_db.py read                                # Read all messages (replies indented)
python bbs_db.py users                               # List all users
python bbs_db.py search <keyword>                    # Search posts by keyword
python bbs_db.py reply <post_id> <username> <message> # Reply to a post (Silver)
python bbs_db.py interactive                         # Enter interactive mode (Gold)
```

### Part C — Migration

```bash
python migrate.py   # Reads bbs.json, writes to bbs.db
```

---

## Tier: Gold

### Silver extension: Threads

Posts can be replies to other posts. `bbs_db.py reply <post_id> <username> <message>` creates a post with a `parent_id` foreign key pointing to the original. `read` displays replies indented one level beneath their parent, preserving thread structure visually.

Schema change required: a nullable `parent_id` column on the `posts` table, referencing `posts(id)`.

### Gold addition: Interactive mode + rich terminal UI

Running `python bbs_db.py interactive` drops into a live session. You log in once with a username and get a `bbs>` prompt — no need to retype your username for every post or reply. The session stays active until you type `quit`.

All output in both one-shot and interactive mode uses the `rich` library: timestamps are dimmed, post IDs and usernames are colored, and the interactive mode opens with an ASCII art welcome screen. This makes the board feel like an actual BBS rather than plain CLI output.

---

## Part D: Private Messages, Leaderboard, and Trending

### Private Messages (DMs)

Send a private message from one user to another:

```bash
python bbs_db.py dm <sender> <recipient> <message>
python bbs_db.py inbox <username>
```

Interactive equivalents:

```
dm <recipient> <message>
inbox
```

Messages are stored in a `direct_messages` table and marked unread until `inbox` is run. Unread messages are shown in bold yellow; previously-read messages are dimmed. The sender must already exist as a user — no ghost accounts are created.

Schema change: adds a `direct_messages` table with `sender_id`, `recipient_id`, `message`, `timestamp`, and `read_at` (NULL = unread). The existing `bbs.db` is safe — `init_db()` uses `CREATE TABLE IF NOT EXISTS`.

### Leaderboard

```bash
python bbs_db.py leaderboard
```

Interactive: `leaderboard`

Ranks all users by number of top-level posts authored and total direct replies received. Computed live from the existing `posts` and `users` tables. Output is a formatted table via `rich`.

Only top-level posts (where `parent_id IS NULL`) count toward a user's post total — replies are excluded. The reasoning: a post and a reply are different contributions. The leaderboard ranks original content, not participation. Replies are still counted in the "Replies Received" column for the original post's author.

### Trending

```bash
python bbs_db.py trending
```

Interactive: `trending`

Shows the top 10 top-level posts by a time-decay score:

```
score = reply_count / (hours_since_post + 2) ^ 1.2
```

The `+2` prevents brand-new posts with zero replies from dominating. The exponent `1.2` controls how fast older posts lose ground — a higher exponent means older posts need disproportionately more replies to stay ranked. At 1.2, a post at 72 hours needs roughly 7.4x as many replies as a post at 12 hours to achieve the same score. Age is computed from ISO timestamps stored in SQLite using `julianday()`. Output is a formatted table showing rank, score, age, reply count, and the post itself.

### Threading and recursion

`cmd_read()` displays replies indented under their parent posts using a recursive function. Python's default recursion limit is 1000 levels deep. In practice this means a reply chain would have to be 1000 replies deep (each replying to the previous) to cause a problem — not a realistic scenario for a BBS.

---

## Users: JSON vs. SQL

In `bbs.py`, `cmd_users()` scans every post and collects unique usernames into a `set`. A set automatically rejects duplicates, so no manual checking is needed. The tradeoff is the same as search: the entire `bbs.json` file must be loaded into memory on every call.

In `bbs_db.py`, `cmd_users()` is a single query: `SELECT username FROM users ORDER BY id`. Usernames are stored exactly once in the `users` table (enforced by the `UNIQUE` constraint on the column), so no deduplication logic is needed at all — the database guarantees it at the storage level.

---

## Search: JSON vs. SQL

In `bbs.py`, search works by loading the entire `bbs.json` file into memory and iterating over every post, checking whether the keyword appears in the message string. This is a full linear scan — O(n) in the number of posts. It's simple and works fine at small scale, but it has real limitations: the entire dataset has to fit in memory, and every search reads and parses the whole file from disk regardless of how many results exist.

In `bbs_db.py`, search is a single SQL query:

```sql
SELECT u.username, p.message, p.timestamp
FROM posts p JOIN users u ON p.user_id = u.id
WHERE p.message LIKE :keyword
```

The database engine handles the scan internally and only returns matching rows. At a million posts, the JSON approach would be noticeably slow and memory-hungry — loading and parsing a large file on every search. The SQL version would still do a full table scan for a `LIKE` query (since `%keyword%` patterns can't use a standard index), but the scan happens inside the database process without loading everything into Python memory. Adding a full-text search index (e.g. SQLite FTS5) could make it dramatically faster still — something that has no equivalent in the flat-file approach.

---

## Migration behavior

`migrate.py` reads `bbs.json` and populates `bbs.db`, skipping duplicates rather than wiping or erroring.

- **Users:** inserted with `INSERT OR IGNORE` — if a username already exists in `bbs.db`, it's left untouched.
- **Posts:** before inserting, the script checks whether a post with the same username, message, and timestamp already exists. If it does, it's skipped.

This means `migrate.py` is safe to run multiple times. Running it again after a successful migration produces: `Migrated 0 users, 0 posts (N skipped as duplicates)` and leaves the database unchanged.

I chose this behavior over wiping because a destructive migration (drop and recreate) would destroy any posts or replies added directly through `bbs_db.py` after the initial migration. Skipping duplicates is the safer default — it lets you re-run without data loss.

### Timestamp precision

Timestamps were originally stored with second precision (`timespec="seconds"`), e.g. `2026-04-13T17:27:27`. This meant that if the same user posted the same message twice within one second, the duplicate check in `migrate.py` would incorrectly treat the second post as a duplicate and skip it.

Timestamps are now stored with millisecond precision (`timespec="milliseconds"`), e.g. `2026-04-13T17:27:27.143`. This makes same-second duplicates distinguishable in nearly all real cases. The remaining edge case — a user posting the identical message twice within the same millisecond — is not realistically possible through normal use.
