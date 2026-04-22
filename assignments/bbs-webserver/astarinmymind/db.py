from datetime import datetime

from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///bbs.db")


def init_db():
    """Create tables if they don't exist."""
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
        conn.commit()


def create_user(conn, username: str) -> dict | None:
    """Insert a new user. Returns user dict, or None if username already exists."""
    # Look up the database to see if this username is already taken
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    ).fetchone()
    # If we found a match, username is taken. Return None instead of raising
    # an error. Claude recommended this because it keeps db.py simple and
    # unaware of HTTP concerns. The API layer decides the status code (409).
    if row:
        return None

    # Username is available, generate timestamp and insert the new user
    created_at = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        text("INSERT INTO users (username, created_at) VALUES (:username, :created_at)"),
        {"username": username, "created_at": created_at},
    )
    conn.commit()
    # Return the user dict matching the API response shape
    return {"username": username, "created_at": created_at}


def get_user_by_username(conn, username: str) -> dict | None:
    """Look up one user by username. Returns dict or None if not found."""
    row = conn.execute(
        text("SELECT username, created_at FROM users WHERE username = :username"),
        {"username": username},
    ).fetchone()
    # No match found - API layer will return 404
    if not row:
        return None
    return {"username": row[0], "created_at": row[1]}
