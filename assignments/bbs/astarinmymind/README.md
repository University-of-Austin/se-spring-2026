# Angela's BBS

## Setup

```bash
uv sync
```

## Usage

### Part A (JSON)
```bash
uv run python bbs.py post <username> <message>
uv run python bbs.py read
uv run python bbs.py users
uv run python bbs.py search <keyword>
```

### Part B (SQLite)
```bash
uv run python bbs_db.py post <username> <message>
uv run python bbs_db.py read
uv run python bbs_db.py users
uv run python bbs_db.py search <keyword>
```

### Part C (Migration)
```bash
uv run python migrate.py          # Migrate JSON to SQLite
uv run python migrate.py --force  # Overwrite existing database
```

### Tests
```bash
uv run pytest
```

## Tier

Targeting **gold**.

## Gold Feature: Thermal Printer Integration

Posts automatically print on a thermal receipt printer via Bluetooth. Classmates can post through a web interface.

<p align="center">
  <img src="printer.jpg" alt="MXW01 thermal printer with BBS posts" width="400">
</p>
<p align="center"><em>The MXW01 printer with QR code, posts with emoji flair, and that classic BBS feel.</em></p>

### Setup
1. Turn on the MXW01 thermal printer
2. Make sure it's paired with your laptop via Bluetooth

### Running the Web Interface
```bash
uv run python web.py
```
This starts a local web server. Classmates on the same WiFi can visit the URL shown to post messages. Each post saves to the database and prints immediately.

### Printing a QR Code
```bash
uv run python print_qr.py
```
Prints a QR code that classmates can scan to open the web form.

## Silver Feature: User Flair

Users can set an emoji flair that appears next to their name on all posts.

### Command Line
```bash
uv run python bbs_db.py flair <username> <emoji>
```

Example:
```
$ python bbs_db.py flair angela ⭐
Flair set to ⭐ for angela.

$ python bbs_db.py read
[2026-04-13 11:30] angela ⭐: Hello everyone!
```

### Web Interface
The web form includes an emoji picker. Users can select a flair when posting, and it gets saved to their profile.

### Schema Change
Added a `flair` column to the `users` table:
```sql
ALTER TABLE users ADD COLUMN flair TEXT
```

## Search Comparison: JSON vs SQL

In the JSON version, search loads the entire `bbs.json` file into memory, then loops through every post checking if the keyword exists in each message. This is O(n) where n is the number of posts, and requires loading all data regardless of how many matches exist.

In the SQL version, the database handles the filtering:
```sql
SELECT ... FROM posts WHERE message LIKE :pattern
```
The database engine does the work and we only receive matching rows. With proper indexing, this could be much faster than O(n).

With a million posts, the JSON version would load 100MB+ into memory on every search and scan every single post. The SQL version would use database optimizations (indexes, query planning) to return results without loading everything.

## Migration Behavior

If `bbs.db` already exists, `migrate.py` **errors out** with:
```
Error: bbs.db already exists. Use --force to overwrite.
```

Use `--force` to delete the existing database and migrate fresh.

**Why this behavior?** It's the safest default. Silently overwriting could destroy data. Skipping duplicates would require complex logic and could leave the database in an inconsistent state. Erroring out forces an explicit decision, and `--force` provides a way to continue after confirming this is what the user wants.
