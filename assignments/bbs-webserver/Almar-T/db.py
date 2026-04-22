"""
db.py - engine + init_db() for the A2 webserver.

The DB file is shared with A1's CLI. By default we point at A1's bbs.db
so running `python bbs_db.py read` in the A1 directory and hitting
GET /posts here both see the same posts. Override with BBS_DB_PATH.

init_db() runs pending migrations from ./migrations/ against a
schema_migrations tracking table. Safe on a fresh DB and safe on a
pre-existing A1 DB (migration 001 uses IF NOT EXISTS).
"""

import os

from sqlalchemy import create_engine, text

_HERE = os.path.dirname(os.path.abspath(__file__))

# Default: share the A1 CLI's bbs.db so the two interfaces talk to the
# same database (per the A2 spec: "two ways to talk to the same database").
DEFAULT_DB_PATH = os.path.abspath(os.path.join(_HERE, "..", "..", "bbs", "Almar-T", "bbs.db"))
DB_PATH = os.environ.get("BBS_DB_PATH", DEFAULT_DB_PATH)

engine = create_engine(f"sqlite:///{DB_PATH}")

MIGRATIONS_DIR = os.path.join(_HERE, "migrations")


def _applied_versions(conn):
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
        )
    """))
    rows = conn.execute(text("SELECT version FROM schema_migrations")).fetchall()
    return {r[0] for r in rows}


def _split_statements(sql):
    """Split a .sql file into individual statements.

    Strips `-- ...` comments first so a `;` inside a comment doesn't
    fake a statement boundary.
    """
    no_comments = "\n".join(
        ln.split("--", 1)[0] for ln in sql.splitlines()
    )
    return [s.strip() for s in no_comments.split(";") if s.strip()]


def init_db():
    """Apply any pending migrations in order. Idempotent."""
    with engine.begin() as conn:
        applied = _applied_versions(conn)

    for filename in sorted(os.listdir(MIGRATIONS_DIR)):
        if not filename.endswith(".sql"):
            continue
        version = filename.split("_", 1)[0]
        if version in applied:
            continue

        with open(os.path.join(MIGRATIONS_DIR, filename)) as f:
            statements = _split_statements(f.read())

        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
            conn.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:v)"),
                {"v": version},
            )
        print(f"[db] applied migration {filename}")


if __name__ == "__main__":
    init_db()
    print(f"[db] schema is up to date at {DB_PATH}")
