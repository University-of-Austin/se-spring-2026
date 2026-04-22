from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///bbs.db")


def init_db():
    """Create the users and posts tables if they don't already exist."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                bio TEXT DEFAULT '',
                joined TEXT DEFAULT ''
            )
        """))
        # Add columns for databases created before the profile feature.
        for col, defn in [("bio", "TEXT DEFAULT ''"), ("joined", "TEXT DEFAULT ''")]:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {defn}"))
            except Exception:
                pass
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """))
