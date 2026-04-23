"""
Database layer for the BBS webserver (Assignment 2).

Helpers map to API endpoints as follows:
  init_db              - startup
  create_user          - POST   /users
  list_users           - GET    /users
  get_user_by_username - GET    /users/{username}
  create_post          - POST   /posts
  list_posts           - GET    /posts  AND  GET /users/{username}/posts
                         (via the username filter)
  get_post_by_id       - GET    /posts/{id}
  delete_post          - DELETE /posts/{id}

Helpers return plain dicts / lists / None / bool and know nothing about HTTP.
The FastAPI layer in main.py composes these, picks status codes, and parses
headers (X-Username) and query params (q, limit, offset).
"""
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
                created_at TEXT NOT NULL,
                bio TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT,
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
    return {"username": username, "created_at": created_at, "bio": None, "post_count": 0}


def list_users(conn) -> list[dict]:
    """Return all users as a list of dicts matching the API response shape."""
    rows = conn.execute(
        text("""
            SELECT u.username, u.created_at, u.bio,
                   (SELECT COUNT(*) FROM posts WHERE user_id = u.id) AS post_count
            FROM users u
            ORDER BY u.id
        """),
    ).mappings().all()
    return [
        {
            "username": row["username"],
            "created_at": row["created_at"],
            "bio": row["bio"],
            "post_count": row["post_count"],
        }
        for row in rows
    ]


def get_user_by_username(conn, username: str) -> dict | None:
    """Look up one user by username. Returns dict or None if not found."""
    row = conn.execute(
        text("""
            SELECT u.username, u.created_at, u.bio,
                   (SELECT COUNT(*) FROM posts WHERE user_id = u.id) AS post_count
            FROM users u
            WHERE u.username = :username
        """),
        {"username": username},
    ).mappings().fetchone()
    # No match found - API layer will return 404
    if row is None:
        return None
    return {
        "username": row["username"],
        "created_at": row["created_at"],
        "bio": row["bio"],
        "post_count": row["post_count"],
    }


def update_user_bio(conn, username: str, bio: str) -> dict | None:
    """Update a user's bio. Returns updated user dict, or None if not found."""
    # Check user exists first
    user = get_user_by_username(conn, username)
    if user is None:
        return None
    conn.execute(
        text("UPDATE users SET bio = :bio WHERE username = :username"),
        {"bio": bio, "username": username},
    )
    conn.commit()
    # Return the updated user dict with new bio
    user["bio"] = bio
    return user


def create_post(conn, username: str, message: str) -> dict | None:
    """Insert a new post. Returns post dict, or None if username doesn't exist."""
    # Resolve username to user_id - posts.user_id is the FK into users.
    row = conn.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": username},
    ).mappings().fetchone()
    # No match - API layer will return 404 (A2 does not auto-create users)
    if row is None:
        return None
    user_id = row["id"]

    # Insert the post with the resolved user_id. posts.id is auto-generated.
    created_at = datetime.now().isoformat(timespec="seconds")
    result = conn.execute(
        text("INSERT INTO posts (user_id, message, created_at) VALUES (:user_id, :message, :created_at)"),
        {"user_id": user_id, "message": message, "created_at": created_at},
    )
    conn.commit()

    # Build the API response shape. lastrowid is SQLite's newly assigned post id.
    return {
        "id": result.lastrowid,
        "username": username,
        "message": message,
        "created_at": created_at,
        "updated_at": None,
    }


def list_posts(
    conn,
    q: str | None = None,
    username: str | None = None,
    since: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Return posts (newest first) matching the optional filters.

    Filters:
      q: case-insensitive substring match on message text
      username: exact match on the post's author
      since: ISO timestamp - only return posts created after this time
    """
    # Build WHERE clauses dynamically based on which filters are active.
    # The SELECT/JOIN/ORDER/LIMIT stay the same in every case.
    #
    # SQL injection note: the {where} f-string below only splices hardcoded
    # clause strings into the query. User input (q, username) is never
    # interpolated into SQL - it only reaches the database as bound params
    # via the params dict. The f"%{q}%" below builds a Python LIKE pattern,
    # which is a value, not SQL.
    clauses: list[str] = []
    params: dict = {"limit": limit, "offset": offset}

    if q is not None:
        # Substring search on message, case-insensitive via SQLite's NOCASE collation.
        # Escape % and _ so they're treated as literal characters, not LIKE wildcards.
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("p.message LIKE :q ESCAPE '\\' COLLATE NOCASE")
        params["q"] = f"%{escaped}%"

    if username is not None:
        # Filter by the post's author. Uses u.username (the joined users table)
        # so we do not need a separate user_id lookup.
        clauses.append("u.username = :username")
        params["username"] = username

    if since is not None:
        # Only return posts created at or after this ISO timestamp
        clauses.append("p.created_at >= :since")
        params["since"] = since

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    # JOIN users to surface the username in each post (API response shape
    # needs username, but the posts table only stores user_id).
    sql = f"""
        SELECT p.id, u.username, p.message, p.created_at, p.updated_at
        FROM posts p
        JOIN users u ON p.user_id = u.id
        {where}
        ORDER BY p.id DESC
        LIMIT :limit OFFSET :offset
    """

    rows = conn.execute(text(sql), params).mappings().all()
    return [
        {
            "id": row["id"],
            "username": row["username"],
            "message": row["message"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def get_post_by_id(conn, post_id: int) -> dict | None:
    """Fetch a single post by id. Returns dict or None if not found."""
    # Same JOIN as list_posts - the API response needs username, which lives
    # on users, not posts.
    row = conn.execute(
        text("""
            SELECT p.id, u.username, p.message, p.created_at, p.updated_at
            FROM posts p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = :id
        """),
        {"id": post_id},
    ).mappings().fetchone()
    # No match - API layer will return 404
    if row is None:
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "message": row["message"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def update_post_message(conn, post_id: int, message: str) -> dict | None:
    """Update a post's message. Returns updated post dict, or None if not found."""
    post = get_post_by_id(conn, post_id)
    if post is None:
        return None
    updated_at = datetime.now().isoformat(timespec="seconds")
    conn.execute(
        text("UPDATE posts SET message = :message, updated_at = :updated_at WHERE id = :id"),
        {"message": message, "updated_at": updated_at, "id": post_id},
    )
    conn.commit()
    post["message"] = message
    post["updated_at"] = updated_at
    return post


def delete_post(conn, post_id: int) -> bool:
    """Delete a post by id. Returns True if a row was deleted, False if no such id."""
    result = conn.execute(
        text("DELETE FROM posts WHERE id = :id"),
        {"id": post_id},
    )
    conn.commit()
    # rowcount is the number of rows the DELETE affected. 0 means the id
    # didn't exist, so the API handler should return 404 instead of 204.
    return result.rowcount > 0
