# BBS - Bulletin Board System

**Tier: Gold**

## Setup

```bash
pip install sqlalchemy
pip install windows-curses   # only needed on Windows, for the TUI
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
python bbs_db.py interactive          # <-- best way to use it
python bbs_db.py tui                  # <-- full-screen curses interface
```

Or one-shot commands:

```bash
python bbs_db.py post <user> <board> <msg>
python bbs_db.py read [board] [hot|new|top]
python bbs_db.py upvote <user> <post_id>
python bbs_db.py downvote <user> <post_id>
python bbs_db.py pin <user> <post_id>
python bbs_db.py react <user> <post_id> [emoji]
python bbs_db.py trending
python bbs_db.py dm <from> <to> <msg>
python bbs_db.py inbox <user>
python bbs_db.py games <user>
python bbs_db.py leaderboard
python bbs_db.py badges <user>
python bbs_db.py export [file.json]
python bbs_db.py import <file.json>
```

### Part C: Migration

```bash
python migrate.py
```

### Tests

```bash
python test_bbs.py    # 73 automated tests covering all features
```

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
correctly mapped foreign keys.

## Silver Features

### 1. Topics/Boards

Every post belongs to a named board. Replies inherit the parent's board.

**Schema:** `boards` table (`id`, `name` UNIQUE) plus `board_id` FK on `posts`.

### 2. Threads

Reply to any post by ID. Replies display indented under their parent with
`+-` tree connectors. Nesting is recursive -- replies can go arbitrarily deep.

**Schema:** nullable `reply_to` column on `posts` referencing `posts(id)`.

### 3. User Profiles

Auto-created on first post. Includes join date, post count, settable bio, and
earned achievement badges.

**Schema:** `bio` (TEXT) and `joined` (TEXT) columns on `users`.

### 4. Colored Terminal Output

ANSI-colored output with per-user color coding, dimmed metadata, yellow board
tags, and tree connectors for threads. Respects `NO_COLOR` / `FORCE_COLOR`.

## Gold Features

### 5. Interactive Mode

`python bbs_db.py interactive` drops you into a live `username@bbs>` session.
You log in once and run commands without re-typing your name. On login it
checks for unread DMs and notifies you, and checks for new achievements.

### 6. Full-Screen Curses TUI

`python bbs_db.py tui` launches a full-screen terminal interface built with
the `curses` library. Features:

- Arrow-key menu navigation with highlighted selection
- Scrollable post/message views (Page Up/Down, arrow keys)
- Color-coded header bar with unread DM count
- Status bar with contextual key hints
- Inline commands (upvote/downvote/reply from the posts view)
- Seamless transition to door games (temporarily exits curses, plays the
  game in normal terminal mode, then returns)

**No schema changes** -- the TUI is a presentation layer over the same database.
Requires `windows-curses` on Windows.

### 7. Private Messages

DMs between users with read-tracking. Inbox shows `[NEW]` markers on unread
messages, marks them read when viewed.

**Schema:** `messages` table with `sender_id`, `recipient_id` (both FK->users),
`body`, `timestamp`, `is_read`.

### 8. Post Reactions & Trending

Custom emoji reactions (one per user per post). Reactions display inline next
to posts. `trending` ranks posts by combined vote + reaction score.

**Schema:** `reactions` table with `UNIQUE(post_id, user_id)`.

### 9. Upvote / Downvote System

Separate from emoji reactions. Each user can upvote (+1) or downvote (-1) any
post. Voting the same direction again **toggles it off** (removes the vote).
Vote scores display inline as colored `[+N]` / `[-N]` tags.

Three sort modes for `read`:
- **default** -- chronological with pinned posts first
- **hot** -- votes + recency bonus (posts from last 24h get +5)
- **new** -- reverse chronological
- **top** -- pure vote count descending

**Schema:** `votes` table with `post_id`, `user_id`, `value` (+1/-1),
`UNIQUE(post_id, user_id)`.

### 10. Post Pinning

Any user can pin a post. Pinned posts display at the top with a `[PINNED]`
tag. Pinning again toggles it off.

**Schema:** `is_pinned` column (INTEGER, default 0) on `posts`.

### 11. Achievements / Badges

9 badges awarded automatically when milestones are reached:

| Badge | Requirement |
|---|---|
| First Post | Make your first post |
| Chatterbox | Post 10 messages |
| Reply King | Reply to 5 posts |
| Board Explorer | Post in 3 different boards |
| Social Butterfly | Send 5 DMs |
| Popular | Get 5 upvotes on a single post |
| Democracy! | Vote on 10 posts |
| Gamer | Play a door game |
| High Roller | Score 80+ in a door game |

Badges show on profiles and via the `badges` command. New achievements trigger
a `** Achievement Unlocked **` notification inline.

**Schema:** `achievements` table with `user_id`, `badge`, `description`,
`awarded`, `UNIQUE(user_id, badge)`.

### 12. Door Games

Three classic BBS-style mini-games accessible via `games`:

- **Trivia Challenge** -- 10 random CS/tech questions, multiple choice,
  10 pts each. Questions are shuffled each play.
- **Hangman** -- Random word from a tech word list, classic ASCII art
  gallows, score based on remaining lives.
- **Number Guesser** -- Guess 1-100, score = 100 - (attempts-1)*10.

All scores are saved to a leaderboard with per-user, per-game tracking.

**Schema:** `high_scores` table with `user_id`, `game`, `score`, `timestamp`.

### 13. Import / Export

Full round-trip serialization covering posts, users, DMs, reactions, and votes.
Import skips duplicate posts and merges new data.

```bash
python bbs_db.py export backup.json
python bbs_db.py import backup.json
```
