"""Database engine and schema initialization for the BBS.

Exports:
    engine  – SQLAlchemy engine connected to bbs.db
    init_db – creates all tables idempotently
"""

from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///bbs.db")


def init_db():
    """Create all tables if they don't already exist."""
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                bio TEXT DEFAULT '',
                joined TEXT NOT NULL,
                avatar_ascii TEXT DEFAULT '',
                role TEXT DEFAULT 'user',
                is_banned INTEGER DEFAULT 0
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                board_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                reply_to INTEGER,
                is_pinned INTEGER DEFAULT 0,
                is_locked INTEGER DEFAULT 0,
                scheduled_at TEXT,
                has_attachment INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (board_id) REFERENCES boards(id),
                FOREIGN KEY (reply_to) REFERENCES posts(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                body TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (recipient_id) REFERENCES users(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                UNIQUE(post_id, user_id, emoji),
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                value INTEGER NOT NULL,
                UNIQUE(post_id, user_id),
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                badge TEXT NOT NULL,
                description TEXT NOT NULL,
                awarded TEXT NOT NULL,
                UNIQUE(user_id, badge),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS high_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game TEXT NOT NULL,
                score INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS attachments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                content_type TEXT DEFAULT '',
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS mod_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mod_id INTEGER NOT NULL,
                target_user_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                reason TEXT DEFAULT '',
                timestamp TEXT NOT NULL,
                FOREIGN KEY (mod_id) REFERENCES users(id),
                FOREIGN KEY (target_user_id) REFERENCES users(id)
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
