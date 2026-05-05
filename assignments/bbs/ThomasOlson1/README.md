# BBS — Thomas Olson

## Setup

Python 3.9+ required. Install the one dependency:

```bash
pip install -r requirements.txt
```

`requirements.txt` contains `sqlalchemy`. No other third-party packages are used.

## Running the programs

Run all commands from inside `assignments/bbs/ThomasOlson1/`.

### JSON version (`bbs.py`)

Posts are stored in `bbs_data/boards/<board>.json`, one file per board. User records live in `bbs_data/meta.json`. Vote history (for daily-limit enforcement) is in `bbs_data/votes.json`.

```bash
python bbs.py post <username> [--board <board>] <message>
python bbs.py reply <username> [--board <board>] <message_id> <message>
python bbs.py read [board]
python bbs.py boards
python bbs.py users
python bbs.py search <keyword> [board]
python bbs.py profile show <username>
python bbs.py profile setbio <username> <bio>
python bbs.py upvote <username> <board> <message_id>
python bbs.py downvote <username> <board> <message_id>
python bbs.py trending [board]
```

### SQLite version (`bbs_db.py`)

All data lives in `bbs.db`. Schema: `users`, `boards`, `posts`, `votes`. Tables are created automatically on first run via `db.py:init_db()`.

```bash
python bbs_db.py post <username> [--board <board>] <message>
python bbs_db.py reply <username> [--board <board>] <message_id> <message>
python bbs_db.py read [board]
python bbs_db.py boards
python bbs_db.py users
python bbs_db.py search <keyword> [board]
python bbs_db.py profile show <username>
python bbs_db.py profile setbio <username> <bio>
python bbs_db.py upvote <username> <board> <message_id>
python bbs_db.py downvote <username> <board> <message_id>
python bbs_db.py trending [board]
```

If your shell treats `!` specially (e.g. zsh history expansion), wrap the message in single quotes or omit it and enter it interactively when prompted.

### Migration

```bash
python migrate.py           # reads bbs_data/, writes bbs.db
python migrate.py --force   # wipes bbs.db first, then migrates
```

## Tier

Gold

## Search: JSON vs SQL

JSON

`bbs.py` stores posts in separate per-board files under `bbs_data/boards/`. A board-scoped search `search hello tech` (`hello` is the keyword and `tech` is the board) opens only `tech.json`. This is obviously good because if it was not the case we would be opening all posts in order to find messages we just want to find in tech. This also allows for more efficicent writes as you can write just to text. It scales linearly with the length of the board, I was debating adding pages for gold but did not. You can also do a global search (`search hello`) opens each board file in turn and scans them sequentially. This obviously is just linear with the length of all messages. Not as usable as SQL for 1 million posts but better than a flat json. 


SQL

`bbs_db.py` runs a single parameterized query. For a board-scoped search, SQLite resolves the board name to a `board_id` integer and only scans posts belonging to that board. SQLite handles the scan internally without deserializing anything into Python, and the optional board filter is pushed into the query as an additional `AND` clause. At a million posts spread across many boards the speed of the data structure would still be fast. It has this better time because the only thing it needs to check for comparison and unpack would be what i needs to search wihtin each posts. While the JSON has to unpack all the other irrelevant data that goes with each post.

## Migration behavior

`migrate.py` reads the per-board JSON files from `bbs_data/boards/` and inserts all posts into the normalized SQLite schema — resolving board-local parent IDs to SQLite global foreign keys, preserving original timestamps, and carrying vote history from `bbs_data/votes.json` into the `votes` table so daily-limit and duplicate-vote enforcement stays consistent after migration.

If `bbs.db` already exists, the script exits with an error rather than silently overwriting or merging. A merge would risk duplicate posts with no clean way to detect them; a silent overwrite would destroy any posts added directly through `bbs_db.py` after the last migration. Erroring out forces a deliberate choice. Pass `--force` to explicitly wipe and recreate `bbs.db` from the current JSON state.

## Silver features

**Named boards** — posts belong to a named board (default: `general`). The `boards` command lists all boards with post counts. `read <board>` shows only that board's threads.

**Threaded replies** — `reply` attaches a post under a parent by its board-local ID. `read` displays threads with nested indentation, sorted by timestamp at each level.

**User profiles** — each user has a join date (set on first post), running post count, and a settable bio. `profile show` and `profile setbio` expose this.

In `bbs.py` the per-board file structure means a post or vote operation only writes the affected board's file — not a full rewrite of all data. In `bbs_db.py` a `boards` table normalizes board names; `board_post_id` is a board-scoped sequential ID so message IDs stay small and board-relative.

## Gold features

**Upvotes and downvotes** — `upvote <username> <board> <message_id>` and `downvote` increment the respective counters on a post. Votes require a username for accountability. Two constraints are enforced: a user can only vote on any given post once, and each user is limited to 5 votes per day across all boards. In `bbs.py` this is tracked in `bbs_data/votes.json`. In `bbs_db.py` a `votes` table with a `UNIQUE(user_id, post_id)` constraint enforces the duplicate check at the database level, and a `(user_id, date)` index makes the daily count query fast.

**Trending** — `trending [board]` scores all root posts from the last 7 days using `upvotes - downvotes + (reply_count × 5)` and shows the top 5% by score. The reply multiplier rewards active threads, not just highly upvoted ones. Scores are computed fresh on every call — there is no cache — so the ranking always reflects the current vote state. In `bbs_db.py` the date filter is pushed into SQL (`WHERE p.timestamp >= :cutoff`) so only the relevant window of posts is loaded into Python.
