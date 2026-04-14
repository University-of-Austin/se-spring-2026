"""SQLite database setup via SQLAlchemy."""

from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///bbs.db")


def init_db() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    UNIQUE NOT NULL,
                bio      TEXT    DEFAULT '',
                joined   TEXT    NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS boards (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT    UNIQUE NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER NOT NULL,
                board_id  INTEGER NOT NULL,
                message   TEXT    NOT NULL,
                timestamp TEXT    NOT NULL,
                reply_to  INTEGER,
                FOREIGN KEY (user_id)  REFERENCES users(id),
                FOREIGN KEY (board_id) REFERENCES boards(id),
                FOREIGN KEY (reply_to) REFERENCES posts(id)
            )
        """))
        # Gold: private messages
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id    INTEGER NOT NULL,
                recipient_id INTEGER NOT NULL,
                body         TEXT    NOT NULL,
                timestamp    TEXT    NOT NULL,
                is_read      INTEGER DEFAULT 0,
                FOREIGN KEY (sender_id)    REFERENCES users(id),
                FOREIGN KEY (recipient_id) REFERENCES users(id)
            )
        """))
        # Gold: post reactions (one per user per post)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS reactions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id   INTEGER NOT NULL,
                user_id   INTEGER NOT NULL,
                emoji     TEXT    NOT NULL DEFAULT '+1',
                timestamp TEXT    NOT NULL,
                FOREIGN KEY (post_id) REFERENCES posts(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(post_id, user_id)
            )
        """))
