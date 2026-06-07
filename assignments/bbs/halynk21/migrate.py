#!/usr/bin/env python3
"""
migrate.py — One-shot migration from bbs.json → bbs.db

BEHAVIOUR
─────────
• Reads every post from bbs.json.
• For each unique username found, inserts a row into `users`
  (INSERT OR IGNORE — existing users are left untouched).
• For each post, inserts a row into `posts` using the correct
  user_id foreign key and the original ISO timestamp.
• All posts land in the 'general' board (the default board created
  by init_db), since the JSON format has no board concept.

EDGE CASES
──────────
1. bbs.json does not exist → prints a clear error, exits non-zero.
2. A username already exists in bbs.db → INSERT OR IGNORE skips it;
   the existing user row is reused for any new posts.
3. The exact same post (same username + message + timestamp) already
   exists in bbs.db → we detect it with a SELECT before inserting
   and skip it.  This makes migrate.py safely re-runnable.
4. bbs.json is empty → migration succeeds with 0 posts imported.

Usage:
    python migrate.py [--json path/to/bbs.json] [--db path/to/bbs.db]
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, text
import db as _db_module


def migrate(json_path: str = "bbs.json", db_path: str = "bbs.db") -> None:
    # ── Validate source ──────────────────────────────────────────────────────
    src = Path(json_path)
    if not src.exists():
        print(f"Error: '{json_path}' not found.  Run bbs.py first to create it.")
        sys.exit(1)

    with open(src, "r", encoding="utf-8") as fh:
        posts: list[dict] = json.load(fh)

    if not posts:
        print("bbs.json is empty — nothing to migrate.")
        return

    # ── Connect ──────────────────────────────────────────────────────────────
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    # Temporarily point db module at the migration target so init_db/init_econ
    # create the full schema (all tables + ALTER TABLE additions) there.
    _db_module.engine = engine
    _db_module.init_db()
    _db_module.init_econ()

    # ── Extract distinct users (preserving first-seen order) ─────────────────
    seen: dict[str, str] = {}   # username → first-seen timestamp
    for p in posts:
        u = p["username"]
        if u not in seen:
            seen[u] = p.get("timestamp", datetime.now().isoformat(timespec="seconds"))

    # ── Run migration in a single transaction ────────────────────────────────
    inserted_users = 0
    inserted_posts = 0
    skipped_posts  = 0

    with engine.connect() as conn:

        # 1. Upsert users
        for username, first_ts in seen.items():
            result = conn.execute(
                text("INSERT OR IGNORE INTO users (username, bio, created_at) VALUES (:u, '', :ts)"),
                {"u": username, "ts": first_ts},
            )
            if result.rowcount:
                inserted_users += 1

        # 2. Fetch user_id map (covers both newly inserted and pre-existing)
        rows = conn.execute(text("SELECT username, id FROM users")).fetchall()
        uid_map: dict[str, int] = {uname: uid for uname, uid in rows}

        # 3. Get the 'general' board id (created by init_db)
        board_row = conn.execute(
            text("SELECT id FROM boards WHERE name = 'general'")
        ).fetchone()
        board_id: int = board_row[0]

        # 4. Insert posts (skip exact duplicates)
        for p in posts:
            username  = p["username"]
            message   = p["message"]
            raw_ts    = p.get("timestamp", datetime.now().isoformat(timespec="seconds"))
            # Normalise to seconds precision so ORDER BY timestamp is consistent
            try:
                timestamp = datetime.fromisoformat(raw_ts).isoformat(timespec="seconds")
            except ValueError:
                timestamp = raw_ts

            user_id = uid_map[username]

            # Duplicate check: same user + message + timestamp → already migrated
            existing = conn.execute(
                text("""
                    SELECT id FROM posts
                    WHERE user_id = :uid
                      AND message = :msg
                      AND timestamp = :ts
                """),
                {"uid": user_id, "msg": message, "ts": timestamp},
            ).fetchone()

            if existing:
                skipped_posts += 1
                continue

            conn.execute(
                text("""
                    INSERT INTO posts (user_id, board_id, parent_id, message, timestamp)
                    VALUES (:uid, :bid, NULL, :msg, :ts)
                """),
                {
                    "uid": user_id,
                    "bid": board_id,
                    "msg": message,
                    "ts":  timestamp,
                },
            )
            inserted_posts += 1

        conn.commit()

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"Migration complete.")
    print(f"  Users  inserted : {inserted_users}")
    print(f"  Posts  inserted : {inserted_posts}")
    print(f"  Posts  skipped  : {skipped_posts}  (already in DB)")
    print(f"  Source          : {json_path}")
    print(f"  Destination     : {db_path}")


# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate bbs.json → bbs.db",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--json", default="bbs.json", metavar="PATH",
                        help="Path to the JSON file  (default: bbs.json)")
    parser.add_argument("--db",   default="bbs.db",   metavar="PATH",
                        help="Path to the SQLite DB  (default: bbs.db)")
    args = parser.parse_args()

    migrate(args.json, args.db)


if __name__ == "__main__":
    main()
