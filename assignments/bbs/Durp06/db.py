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
