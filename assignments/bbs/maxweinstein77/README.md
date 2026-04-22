# Llamagram BBS

LlamaGram BBS is a terminal-based bulletin board system coded in Python. Users are able to post messages, read threads, and search for specific queries through the CLI. I had a little fun with it and added some ASCII llama art to make the user experience more enjoyable. 

**Tier Goal: Gold**

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install sqlalchemy rich
```

## Usage

### Part A: JSON File Storage

```bash
python3 bbs.py post <username> <message>
python3 bbs.py read
python3 bbs.py users
python3 bbs.py search <keyword>
```

### Part B: SQLite Upgrade

```bash
python3 bbs_db.py post <username> <message>
python3 bbs_db.py read
python3 bbs_db.py users
python3 bbs_db.py search <keyword>
python3 bbs_db.py reply <username> <post_id> <message>
```

### Part C: Migration

```bash
python3 migrate.py
```

## Search: JSON File Storage vs SQLite Upgrade

Using JSON file storage, every search loads the entire `bbs.json` file into memory, looping through every single post until it identifies the match that it's looking for. 

On the other hand, the SQLite version, as opposed to searching through every single post, just sends one query to the database and that query alone is sufficient for the database to filter and identify the matching rows.

When working with really large datasets, SQLite stands out relative to JSON file storage, namely because the JSON method of having to search through every single post can become computationally expensive very quickly. SQL avoids this limitation because it only needs to send one query and that query is able to identify matches without having to check through every single row. 

So sure, at small scales, it might seem irrelevant why one ought to prioritize one over the other. But as soon you as start making significant leaps in the size of the data you're working with, say a million or more posts, that JSON file storage system is going to be parsing hundreds of mb per search query, a much more computationally expensive task relative to the single query search afforded on behalf of SQLite. 

## Migration Behavior + Justification 

If `bbs.db` already contains data when you run `migrate.py`, the program exits and error will populate the screen. The idea is for the migration to only move the data form the JSON file into the database in a single instance. If we didn't enforce this constraint, we'd run the risk of duplicating or perhaps even overwriting posts that were added via `bbs_db.py` after our inital migration. So you can still re-migrate but this constraint forces the user to delete 'bbs.db' and run it all over again. 

## Silver: Threads

Added a `reply` command that lets users reply to a specific post by its ID. Replies are displayed indented underneath their parent post in the `read` output for ease of readability. 

In order to achieve the addition of threads, I added a new column to the posts table called `parent_id`. Regular high-level posts are indicated by an empty (NULL) `parent_id`. In the case that it's a reply, parent_id stores the ID of the post it's responding to. When you run the read command, you'll see the replies indented under the parent posts. 

## Gold: Llamagram UI

Implemented ASCII art llama speech bubbles and colored terminal output via the `rich` library. Every command displays a llama banner with the llama art in magenta. The read command color-codes usernames in yellow, timestamps in grey, post IDs in blue, and uses a threading indicator to show replies indented under their parent posts.

## Files

- `bbs.py` — Part A, JSON-based BBS
- `bbs_db.py` — Part B, SQLite-based BBS with threads and rich UI
- `db.py` — Shared database engine and table initialization
- `migrate.py` — Part C, JSON to SQLite migration script