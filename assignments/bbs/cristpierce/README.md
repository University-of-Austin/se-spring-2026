# BBS Bustin' — Assignment 1

**Tier: Gold+**
**Author:** cristpierce

A full-featured Bulletin Board System with CLI and web interfaces. Built with Python, SQLAlchemy (raw SQL), and FastAPI.

---

## Setup

```bash
pip install -r requirements.txt
```

Requires Python 3.9+.

## Part A: JSON CLI (`bbs.py`)

```bash
python bbs.py post <username> <board> <message>
python bbs.py read [board]
python bbs.py reply <post_id> <username> <message>
python bbs.py users
python bbs.py boards
python bbs.py search <keyword>
python bbs.py profile <username>
python bbs.py bio <username> <text>
```

Data is stored in `bbs.json` and `bbs_users.json`.

## Part B: SQLite CLI (`bbs_db.py`)

Same commands as Part A, plus all Silver and Gold features:

```bash
# Core commands
python bbs_db.py post <username> <board> <message>
python bbs_db.py read [board] [--sort=hot|new|top]
python bbs_db.py reply <post_id> <username> <message>
python bbs_db.py users
python bbs_db.py boards
python bbs_db.py search <keyword>

# Silver: profiles
python bbs_db.py profile <username>
python bbs_db.py bio <username> <text>

# Gold: social
python bbs_db.py dm <from> <to> <message>
python bbs_db.py inbox <username>
python bbs_db.py react <username> <post_id> <emoji>
python bbs_db.py upvote <username> <post_id>
python bbs_db.py downvote <username> <post_id>
python bbs_db.py trending
python bbs_db.py pin <post_id>
python bbs_db.py badges <username>

# Gold: data
python bbs_db.py export [filename]
python bbs_db.py import <filename>
python bbs_db.py leaderboard [game]

# Gold: interactive mode
python bbs_db.py interactive
```

Data is stored in `bbs.db` (SQLite).

## Part C: Migration (`migrate.py`)

```bash
python migrate.py          # Reads bbs.json, writes to bbs.db
python migrate.py other.json  # Custom source file
```

### Migration behavior when `bbs.db` already exists

The migration uses a **clean-slate approach**: it wipes all existing data in the database before importing. This was chosen because:

1. **Simplicity and correctness**: Duplicate detection across JSON and SQL is error-prone (timestamps may differ by microseconds, IDs don't map 1:1). A clean slate guarantees no duplicates.
2. **Idempotency**: Running the migration twice produces the same result. No surprises.
3. **The assignment context**: Migration is a one-time operation moving from Part A to Part B. If you've already been using `bbs_db.py` independently, you should export that data first with `python bbs_db.py export backup.json`.

## Web Frontend (Beyond Gold)

```bash
cd assignments/bbs/cristpierce
uvicorn web.app:app --reload --port 8000
```

Then open [http://localhost:8000](http://localhost:8000).

The web UI is a **retro-modern hybrid** — dark CRT-inspired aesthetic with phosphor green and amber accents, monospace typography, scanline overlay effects, and a clean card-based layout. Features:

- **Boards and threaded posts** with voting, reactions, and pinning
- **User profiles** with ASCII art avatars, bio, and achievement badges
- **Private messaging** with unread indicators
- **Real-time WebSocket notifications** for new DMs and reactions
- **File/image attachments** on posts (5MB limit)
- **Markdown support** with syntax-highlighted code blocks
- **Dark/light theme toggle** (persists via localStorage)
- **Admin panel** with user management, moderation log, and analytics
- **Post scheduling** with datetime picker
- **Game leaderboard** (scores from CLI door games)

Login requires only a username — no password, just like the real BBSes.

## Search: JSON vs SQL

In the JSON version (`bbs.py`), search loads the entire `bbs.json` file into memory, deserializes every post, and iterates through them in Python checking `keyword.lower() in post["message"].lower()`. This is O(n) for every search, and the entire dataset must fit in memory.

In the SQL version (`bbs_db.py`), search executes `WHERE p.message LIKE :keyword` — the database engine handles the filtering internally, reading only the relevant pages from disk. For a million posts, the JSON approach would mean parsing hundreds of megabytes of JSON on every query, while SQLite processes the query with minimal memory overhead and can leverage indexes for even faster lookups.

## Silver Features

### 1. Boards/Topics
Posts belong to named boards. Use `python bbs_db.py post alice general "Hello"` to post to the `general` board, and `python bbs_db.py read general` to view only that board.

**Schema change:** Added `boards` table (`id`, `name UNIQUE`) and `board_id` foreign key on `posts`.

### 2. Threaded Replies
Reply to any post by ID: `python bbs_db.py reply 1 bob "Great post!"`. Replies display indented under their parent in both CLI and web.

**Schema change:** Added `reply_to` self-referential foreign key on `posts`.

### 3. User Profiles
View profiles with `python bbs_db.py profile alice`. Set a bio with `python bbs_db.py bio alice "I love BBSes"`. Profiles show join date, post count, bio, and earned badges.

**Schema change:** Added `bio`, `joined`, `avatar_ascii`, `role`, `is_banned` columns to `users`.

## Gold Features

### 4. Interactive Mode
`python bbs_db.py interactive` drops you into a live `username@bbs>` session. Shows unread DM count on login, badge unlock notifications, and supports all commands without re-entering your username.

### 5. ASCII Art & Colors
ANSI-colored terminal output with per-user color coding, a retro ASCII art welcome banner, and formatted display for posts, profiles, badges, and leaderboards. Respects `NO_COLOR` environment variable.

### 6. Private Messages
Send DMs: `dm alice bob "Hey!"`. View inbox: `inbox bob`. Unread messages show `[NEW]` tags. Messages are marked read when you view your inbox.

**Schema change:** Added `messages` table with `sender_id`, `recipient_id`, `body`, `timestamp`, `is_read`.

### 7. Reactions & Voting
React to posts: `react bob 1 fire`. Vote: `upvote bob 1` / `downvote bob 1`. Votes toggle on repeat. Sort by `--sort=hot|new|top`.

**Schema change:** Added `reactions` table (`UNIQUE(post_id, user_id, emoji)`) and `votes` table (`UNIQUE(post_id, user_id)`).

### 8. Post Pinning
`pin <post_id>` toggles pin status. Pinned posts always appear first in listings with a `[PINNED]` tag.

**Schema change:** Added `is_pinned` column to `posts`.

### 9. Door Games
Three playable mini-games via `python bbs_db.py interactive` → `games`:
- **Trivia Challenge**: 10 random CS/tech questions, 10 points each
- **Hangman**: Guess tech words, ASCII gallows art, scored by remaining guesses
- **Number Guesser**: Guess 1-100, scored by attempts

High scores saved to the database, viewable on the leaderboard.

**Schema change:** Added `high_scores` table with `user_id`, `game`, `score`, `timestamp`.

### 10. Achievement System
9 badges auto-awarded: First Post, Chatterbox (10+ posts), Reply King (5+ replies), Board Explorer (3+ boards), Social Butterfly (5+ DMs), Popular (10+ reactions received), Democracy! (10+ votes cast), Gamer (played a game), High Roller (top-3 score).

**Schema change:** Added `achievements` table with `UNIQUE(user_id, badge)`.

### 11. Import/Export
`export [file]` dumps the entire database to JSON. `import <file>` loads JSON into the database (clean-slate).

## Beyond Gold Features

### 12. FastAPI Web Frontend
Full web interface at `localhost:8000` with 8 page templates, retro-modern CSS with CRT scanline effects, and responsive design.

### 13. Real-Time WebSocket Notifications
New DMs and reactions trigger instant toast notifications in the browser — no page refresh needed.

### 14. Admin Panel & Moderation
Admin users can ban/unban users, lock/unlock threads, delete posts, change user roles, and view a moderation action log with analytics dashboard.

**Schema change:** Added `mod_actions` table and `sessions` table for web authentication.

### 15. File/Image Attachments
Upload images or files to posts via the web interface. Images display inline, other files as download links. 5MB size limit.

**Schema change:** Added `attachments` table with `post_id`, `filename`, `filepath`, `content_type`.

### 16. Markdown & Syntax Highlighting
Posts support Markdown formatting with fenced code blocks rendered with Pygments syntax highlighting.

### 17. Dark/Light Theme Toggle
Toggle between dark (CRT green-on-black) and light (warm paper) themes. Persists across sessions via localStorage.

### 18. ASCII Art Avatars
Users can set custom ASCII art avatars (10 lines x 40 chars) via their profile page.

### 19. Post Scheduling
Schedule posts for future publication via the web interface. Scheduled posts remain hidden until their scheduled time.

**Schema change:** Added `scheduled_at` column to `posts`.

## Database Schema

11 tables total: `users`, `boards`, `posts`, `messages`, `reactions`, `votes`, `achievements`, `high_scores`, `attachments`, `mod_actions`, `sessions`.

All SQL uses `text()` with parameterized `:param` syntax — no string interpolation anywhere.

## Tests

```bash
python test_bbs.py
```

77 automated tests covering Parts A, B, C, and all Gold features.

## Architecture

```
bbs.py (JSON, standalone) ──── bbs.json

bbs_db.py (CLI) ──┐
                   ├── services.py (business logic) ──── db.py ──── bbs.db
web/app.py (Web) ──┘
```

The key architectural decision is the **shared services layer**: `services.py` contains all business logic and SQL, called by both `bbs_db.py` (CLI) and `web/app.py` (FastAPI). This avoids duplicating SQL across entry points and ensures CLI and web always produce consistent results from the same database.
