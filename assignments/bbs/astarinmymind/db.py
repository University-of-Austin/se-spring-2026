"""
Database module for BBS.

Exports the SQLAlchemy engine and init_db() function.
Uses raw SQL with text() - no ORM.
"""

from sqlalchemy import create_engine, text

# SQLite database file
engine = create_engine("sqlite:///bbs.db")


def init_db():
    """
    Create the users and posts tables if they don't exist.
    Called on first run to set up the database.
    """
    with engine.connect() as conn:
        # Users table: stores unique usernames
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL
            )
        """))

        # Posts table: stores messages with foreign key to users
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        # Add flair column if it doesn't exist (for silver feature)
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN flair TEXT"))
        except Exception:
            pass  # Column already exists

        conn.commit()
