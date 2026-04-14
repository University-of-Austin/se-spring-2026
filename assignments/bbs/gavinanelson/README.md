# BBS

This project targets the `gold` tier for Assignment 1. It includes the required JSON CLI, the SQLite upgrade with Silver-level feature extensions, a migration script, and a Textual TUI layered on top of both storage backends.

Everything in this submission is Python. The SQLite version uses SQLAlchemy with raw SQL via `text()`, not the ORM, to stay aligned with the assignment requirements.

## Setup

From this project directory:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

If you want to verify the environment after install:

```bash
python -m unittest -v
```

## Storage

The app now stores its runtime data in a real app-data directory instead of assuming you launch it from the repo:

- Default: `~/.local/share/bbs/`
- Override: set `BBS_DATA_DIR=/path/to/custom-dir`

Important files:

- SQLite database: `bbs.db`
- JSON file: `bbs.json`
- Backups: `backups/`
- JSON exports: `exports/`
- Uploaded images: `uploads/`

To print the active paths:

```bash
bbs-db paths
```

The app starts empty by default. On a fresh run, it creates the storage files it needs and waits for real posts. If you want a populated board immediately for demos or grading, you can use the fake-data seeder described below.

## How To Run

The assignment-required entry points work directly with Python:

JSON version:

```bash
python bbs.py post alice "Hello, is anyone out there?"
python bbs.py read
python bbs.py users
python bbs.py search hello
```

SQLite version:

```bash
python bbs_db.py post alice "Hello from SQLite"
python bbs_db.py post bob general "Thread starter"
python bbs_db.py reply alice 2 "Replying in-thread"
python bbs_db.py read
python bbs_db.py read-board general
python bbs_db.py users
python bbs_db.py search hello
python bbs_db.py boards
python bbs_db.py create-board announcements
python bbs_db.py profile alice
python bbs_db.py set-bio alice "First caller on the board"
```

Migration:

```bash
python migrate.py
```

After installation with `pip install -e .`, the same functionality is also available through the convenience commands `bbs`, `bbs-db`, `bbs-migrate`, `bbs-seed`, and `bbs-tui`.

Gold-tier extras:

```bash
bbs-tui
bbs-tui --backend json
bbs-tui --backend sqlite

bbs-seed --users 20 --posts 80 --boards 4 --replies 12
```

## Demo Data

If the grader wants to see the app with a lot of content right away, they can seed the SQLite database with realistic fake users, boards, posts, bios, and replies:

```bash
bbs-seed --users 20 --posts 80 --boards 4 --replies 12
```

For a larger dataset:

```bash
bbs-seed --users 100 --posts 5000 --boards 20 --replies 800
```

If the database already has data, the seeder refuses to overwrite it unless `--reset` is passed:

```bash
bbs-seed --users 50 --posts 500 --boards 12 --replies 100 --reset
```

I added this so the grader can start from an empty database for the core assignment behavior, but can also instantly populate the board to evaluate the TUI, search, profiles, threads, and overall scale.

## SSH Usage

The intended "real" stopping point for this project is a normal terminal workflow over SSH.

One simple way to use it on a remote machine:

```bash
ssh user@host
git clone <repo-url>
cd bbs
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
tmux new -s bbs
bbs-tui
```

If you want the data somewhere other than `~/.local/share/bbs`, set:

```bash
export BBS_DATA_DIR="$HOME/my-bbs-data"
```

Then launch the same commands. That is useful for testing, backups, or keeping multiple isolated BBS environments.

## Search Comparison

In the JSON version, `search` loads the entire `bbs.json` file into memory and loops through every message in Python. That is straightforward and transparent because the data is just a list of posts on disk, but it means the program has to scan everything every time you search. With a million posts, search still works, but it gets slower because the Python process must read and inspect the whole file for every query.

In the SQLite version, `search` is handled by SQL. The CLI sends one parameterized query to SQLite, and the database engine performs the filtering. The code path is shorter at the application layer because the database does the matching work instead of the Python program manually scanning every row. With a much larger dataset, that separation matters: the SQLite approach scales better and keeps the storage/query logic in the database rather than forcing the CLI to re-process the entire dataset on every search.

## Migration Behavior

`bbs-migrate` reads `bbs.json`, creates normalized `users`, `boards`, and `posts` rows in `bbs.db`, and preserves the original JSON timestamps exactly. Every migrated JSON post lands on the `general` board, because the JSON format does not store boards, replies, or profiles.

If `bbs.db` already contains actual content, the migration stops with an error instead of merging, skipping duplicates, or wiping the database. Concretely, it refuses to run if there are any existing users, any existing posts, or any boards other than the harmless auto-seeded `general` board. I chose that behavior because it is the safest default for assignment code: it prevents silent duplication, accidental data loss, and hard-to-explain partial merges.

## Backup And Export

For SSH/local-machine use, the SQLite CLI now includes minimal operational commands:

```bash
bbs-db backup
bbs-db backup /tmp/my-bbs.db
bbs-db export-json
bbs-db export-json /tmp/my-bbs-export.json
```

`backup` copies the live SQLite database to a file. `export-json` writes a Bronze-shaped JSON message export in timestamp order.

## Silver Additions

The SQLite version includes all three example Silver extensions:

- Boards/topics via `create-board`, board-aware `post`, `boards`, and `read <board>`
- Threads via `reply <username> <post_id> <message>` with indented display under the parent post
- User profiles via `profile <username>` and `set-bio <username> <bio>`

Those features required extending the Bronze schema with:

- a `boards` table
- `joined_at` and `bio` columns on `users`
- a `parent_post_id` column on `posts`

## Gold Addition

The Gold addition is `bbs_tui.py`, a full-screen Textual interface with:

- a split-pane terminal layout
- clickable sidebar navigation
- keyboard shortcuts for the main sections
- board browsing, compose, search, user listing, and profile lookup
- reply flow for SQLite threads
- image attachment support in the SQLite-backed TUI
- backend switching between JSON and SQLite

The TUI sits on top of the command/storage logic rather than replacing the required CLI programs. The JSON backend remains Bronze-shaped, so the TUI degrades gracefully there: boards, replies, and profiles are only fully available when running against SQLite.

### Image Attachments

One of the extra Gold features is image support for SQLite-backed posts in the TUI:

- You can attach an image by entering a file path in the compose panel.
- On Wayland systems, `Ctrl+V` can paste an image from the clipboard directly into the compose form.
- Attached images are stored in the app data directory under `uploads/`.
- The inspector panel can preview an attached image, and the lightbox can open the full image.

Supported formats are `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, and `.bmp`, with a 10 MB size limit per image.

## Account Security

SQLite-backed profiles now store PINs as salted PBKDF2-SHA256 hashes rather than raw text. Existing accounts created implicitly through posting are marked as needing PIN setup; when that user first opens the profile flow, the app tells them to create a PIN before logging in. Legacy rows that still have a plaintext PIN are upgraded to hashed storage automatically after a successful login.

Terminal commands for the PIN lifecycle:

```bash
python bbs_db.py init-pin alice 1234
python bbs_db.py change-pin alice 1234 5678
```
