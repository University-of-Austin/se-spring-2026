# BBS — Bulletin Board System

**Software Engineering · UATX · Spring 2026**

> Terminal-native. Text-first. Two storage engines.  
> A faithful spiritual successor to the 1980s BBS.

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. That's it.  Both programs create their storage files on first run.
```

**Requirements:** Python 3.10+, `sqlalchemy>=2.0`, `rich>=13.0`

> **Windows note:** Interactive mode uses `readline` for command history (arrow keys, history).
> `readline` is built into Python on Linux/macOS but is not available on Windows by default.
> The app handles this gracefully — interactive mode works on Windows, just without history recall.

---

## Part A — JSON Version (`bbs.py`)

```bash
python bbs.py post <username> <message>   # Post a message
python bbs.py read                         # Read all messages
python bbs.py users                        # List all users
python bbs.py search <keyword>            # Search posts
```

Posts are stored in `bbs.json` as a flat JSON array — you can
inspect the full state at any time with `cat bbs.json`.

---

## Part B — SQLite Version (`bbs_db.py`)

### Backwards-compatible one-shot commands

```bash
python bbs_db.py post   <username> <message>
python bbs_db.py read   [board]
python bbs_db.py users
python bbs_db.py search <keyword>
```

### Gold-tier one-shot commands

```bash
python bbs_db.py boards                           # List all boards
python bbs_db.py thread    <post_id>              # View a threaded conversation
python bbs_db.py reply     <post_id> <username> <message>   # Reply to a post
python bbs_db.py profile   <username>             # View user profile
python bbs_db.py bio       <username> <text>      # Set bio
python bbs_db.py react     <post_id> <emoji> <username>
python bbs_db.py unreact   <post_id> <emoji> <username>
python bbs_db.py msg       <sender> <recipient> <message>
python bbs_db.py inbox     <username>
python bbs_db.py leaderboard
python bbs_db.py trending
python bbs_db.py export               # Dump DB → bbs_export.json
python bbs_db.py export  <path>       # Dump to custom path
python bbs_db.py promote <requester> <username>
python bbs_db.py delete  <post_id>  <username>   # username is not verified server-side
```

> **Note on one-shot delete:** the one-shot form requires passing your username as an argument, which is not authenticated — it is provided purely for CLI convenience. In interactive mode, deletion is tied to the logged-in session user.

### Interactive mode (Gold)

```bash
python bbs_db.py          # no arguments → login prompt
python bbs_db.py -i       # explicit interactive flag
python bbs_db.py -i alice # skip the login prompt
```

Once logged in, you get a persistent session prompt:

```
bbs [alice] [general]> 
```

**Interactive commands:**

| Category | Command | Description |
|---|---|---|
| Session | `help` | Show all commands |
| Session | `logout` / `exit` | Leave the BBS |
| Session | `clear` | Clear the screen |
| Navigation | `boards` | List all boards |
| Navigation | `use <board>` | Switch active board |
| Posting | `post <message>` | Post to current board |
| Posting | `post <board> <message>` | Post to specific board |
| Posting | `reply <post_id> <message>` | Reply to a post (creates thread) |
| Posting | `edit <post_id> <new message>` | Edit your own post (records `edited_at`) |
| Posting | `delete <post_id>` | Delete your own post |
| Reading | `read [board] [--limit N] [--page N]` | Read posts with pagination |
| Reading | `thread <post_id>` | View full threaded conversation |
| Reading | `search <keyword>` | Search all posts |
| Social | `react <post_id> <emoji>` | React to a post |
| Social | `unreact <post_id> <emoji>` | Remove a reaction |
| Social | `msg <username> <message>` | Send a private message |
| Social | `inbox` | Read your inbox |
| Profile | `profile [username]` | View profile |
| Profile | `bio <text>` | Set your bio |
| Moderation | `pin <post_id>` | Pin a post to the top (admin/mod only) |
| Moderation | `unpin <post_id>` | Unpin a post (admin/mod only) |
| Moderation | `promote <username>` | Grant mod privileges (admin/mod only) |
| Moderation | `makeadmin <username>` | Grant admin rights (first user or existing admin) |
| Subscriptions | `subscribe <board>` | Subscribe to a board |
| Subscriptions | `unsubscribe <board>` | Unsubscribe from a board |
| Subscriptions | `subscriptions` | List your subscriptions and watermarks |
| Subscriptions | `digest` | New posts since last visit across subscribed boards |
| Stats | `leaderboard` | Most active users |
| Stats | `trending` | Hot posts (last 7 days) |

---

## Part C — Migration (`migrate.py`)

```bash
python migrate.py                        # Migrate bbs.json → bbs.db
python migrate.py --json path --db path  # Custom paths
```

After running, `bbs_db.py read` will show the same posts as `bbs.py read`.

> **Verified:** migrated a 2-user, 2-post `bbs.json` and confirmed both commands produce identical usernames, messages, and timestamps.

---

## Tier

**Gold.**

### Gold features implemented

| Feature | Description |
|---|---|
| **Rich terminal UI** | Full colour output, styled tables, bordered panels, and an ASCII art welcome banner using the `rich` library with a custom colour theme |
| **Interactive shell** | Persistent `bbs [user] [board]>` prompt with readline history; keeps you "logged in" across commands; shows unread PM count on login |
| **Boards / Topics** | Posts belong to named boards; `use <board>` switches context; new boards auto-created on first post |
| **Threaded replies** | `reply <post_id>` attaches to a parent; `thread <post_id>` renders the whole tree indented with `└─` connectors |
| **User profiles** | Join date, post count, recent posts, and an editable `bio` field |
| **Post reactions** | Emoji reactions per post (👍 ❤️ 🔥 😂 …) with per-user uniqueness; displayed inline in `read` output |
| **Private messages** | Direct messages between users; `inbox` marks messages as read; "NEW" badge shown |
| **Leaderboard** | Top-N users ranked by post count + reactions received; 🥇🥈🥉 medals |
| **Trending algorithm** | Score = reactions × 3 + replies × 2 + 1, filtered to the last 7 days; surfaces both popular and lively posts |
| **Post editing/deletion** | `edit <post_id>` and `delete <post_id>` — owner-only; edited posts show an `(edited)` timestamp inline |
| **@mentions** | `@username` in any post notifies the mentioned user with a banner on their next login |
| **Post pinning** | Admins/mods can `pin`/`unpin` posts; pinned posts float to the top of `read` output with a 📌 indicator |
| **Pagination** | `read --page N` shows one screenful at a time; page header shows current page, total pages, and navigation hints |
| **Export to JSON** | `python bbs_db.py export [file]` dumps the full DB back to JSON (inverse of `migrate.py`) |
| **Moderator system** | `promote <username>` grants mod privileges; mods can delete/pin any post |
| **Board subscriptions** | `subscribe <board>` follows a board; `digest` shows all posts since the user's last visit, per board, with a per-board watermark |
| **BBS EconSim** | Full in-BBS economy: fish for fish, sell at daily-varying market prices, buy to speculate, gamble at the slots (jackpot ×5 to catastrophic loss), transfer money with `give`, track history and lifetime stats, leaderboard sorted by balance/earned/net |

### Schema changes for Gold features

```sql
users            id, username, bio, created_at, is_admin, is_mod,
                 balance, total_earned, total_lost, peak_balance
boards           id, name, description, created_at
posts            id, user_id, board_id, parent_id, message, timestamp,
                 edited_at, pinned
reactions        id, post_id, user_id, reaction, created_at  [UNIQUE per triple]
private_messages id, sender_id, recipient_id, message, timestamp, read_at
mentions         id, post_id, mentioned_user_id, notified  [UNIQUE per pair]
subscriptions    id, user_id, board_id, created_at, last_digest_at  [UNIQUE per pair]
inventory        id, user_id, fish_type, quantity  [UNIQUE per pair]
econ_log         id, user_id, action, detail, amount, balance_after, timestamp
```

The `parent_id` self-referential FK on `posts` is the key to threading —
a post with `parent_id IS NULL` is a top-level post; otherwise it is a reply.

---

## Search: JSON vs SQL

In `bbs.py`, search means **loading the entire `bbs.json` file into memory**
and iterating over every post in Python.  This is O(n) in both time and memory:
to find one match in 1 000 000 posts, we deserialise all 1 000 000 objects,
allocate them as Python dicts, and walk the whole list.  At scale this would be
catastrophically slow — a 1M-post board might easily consume hundreds of
megabytes just to answer a single search query.

In `bbs_db.py`, search is a single parameterised SQL `LIKE` query:

```sql
SELECT p.id, u.username, b.name, p.message, p.timestamp
FROM posts p
JOIN users u ON p.user_id = u.id
LEFT JOIN boards b ON p.board_id = b.id
WHERE p.message LIKE :kw ESCAPE '!'
   OR u.username LIKE :kw ESCAPE '!'
ORDER BY p.timestamp DESC
LIMIT 50
```

SQLite executes this inside the database process.  Even without a full-text
index, SQLite's LIKE scan is faster than Python-level iteration because it
avoids Python object allocation overhead and keeps data in native C structures.
Adding a full-text search index (`CREATE VIRTUAL TABLE ... USING fts5`) would
reduce this to O(log n) or even O(k) where k is the number of results — a
transformation that would be nearly impossible to achieve with a flat JSON file
without maintaining a separate index structure by hand.

At one million posts the JSON version would effectively be unusable for search;
the SQL version would remain fast.

---

## Migration behaviour when `bbs.db` already has data

`migrate.py` is **safe to re-run**:

1. Users are inserted with `INSERT OR IGNORE` — existing users are untouched
   and their existing posts, reactions, and PMs are preserved.
2. Before inserting each post, a `SELECT` checks whether an identical row
   (same `user_id` + `message` + `timestamp`) already exists.  If it does,
   the post is skipped and counted in the "skipped" summary.
3. The "general" board is created by `init_db()` with `INSERT OR IGNORE` —
   it will not be duplicated.

**Chosen behaviour: skip duplicates, never wipe.**  The alternative (truncating
the DB before migration) would destroy any data added through `bbs_db.py` after
the JSON-era posts.  The duplicate-check approach means you can safely run the
migration at any time without data loss, and the summary output makes it easy to
verify exactly what was imported.

---

## Repository layout

```
assignments/bbs/<your-github-username>/
├── bbs.py           Part A — JSON storage
├── db.py            SQLAlchemy engine + schema
├── bbs_db.py        Part B + Gold — SQLite BBS
├── migrate.py       Part C — JSON → SQLite migration
├── requirements.txt sqlalchemy, rich
└── README.md        This file
```

> **Before submitting:** rename the directory from `<your-github-username>`
> to your actual GitHub username, then open a PR titled **"BBS — Your Name"**.
