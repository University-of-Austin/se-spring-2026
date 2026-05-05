import json
import sys
from pathlib import Path
from sqlalchemy import text
from db import engine, init_db

JSON_FILE = Path(__file__).parent / "bbs.json"


def migrate():
    if not JSON_FILE.exists():
        print("bbs.json not found — nothing to migrate.", file=sys.stderr)
        sys.exit(1)

    with open(JSON_FILE) as f:
        posts = json.load(f)

    init_db()

    inserted = 0
    skipped = 0

    with engine.begin() as conn:
        for post in posts:
            username = post["username"]
            message = post["text"]
            timestamp = post["when"]

            conn.execute(text("INSERT OR IGNORE INTO users (username) VALUES (:u)"), {"u": username})

            uid = conn.execute(
                text("SELECT id FROM users WHERE username = :u"), {"u": username}
            ).fetchone()[0]

            existing = conn.execute(text(
                "SELECT id FROM posts WHERE user_id = :uid AND message = :msg AND timestamp = :ts"
            ), {"uid": uid, "msg": message, "ts": timestamp}).fetchone()

            if existing:
                skipped += 1
                continue

            conn.execute(text(
                "INSERT INTO posts (user_id, message, timestamp, parent_id) VALUES (:uid, :msg, :ts, NULL)"
            ), {"uid": uid, "msg": message, "ts": timestamp})
            inserted += 1

    print(f"Done: {inserted} posts inserted, {skipped} skipped (already present).")


if __name__ == "__main__":
    migrate()
