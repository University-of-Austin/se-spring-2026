from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///bbs.db", future=True)


def init_db():
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys = ON"))
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    join_date TEXT NOT NULL,
                    post_count INTEGER NOT NULL DEFAULT 0,
                    bio TEXT NOT NULL DEFAULT ''
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS boards (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    board_id INTEGER NOT NULL,
                    board_post_id INTEGER NOT NULL,
                    parent_id INTEGER,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    upvotes INTEGER NOT NULL DEFAULT 0,
                    downvotes INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(board_id) REFERENCES boards(id),
                    FOREIGN KEY(parent_id) REFERENCES posts(id)
                )
                """
            )
        )

        users_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(users)")).all()]
        if "join_date" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN join_date TEXT NOT NULL DEFAULT ''"))
        if "post_count" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN post_count INTEGER NOT NULL DEFAULT 0"))
        if "bio" not in users_columns:
            conn.execute(text("ALTER TABLE users ADD COLUMN bio TEXT NOT NULL DEFAULT ''"))

        posts_columns = [row[1] for row in conn.execute(text("PRAGMA table_info(posts)")).all()]
        if "board_id" not in posts_columns:
            conn.execute(text("ALTER TABLE posts ADD COLUMN board_id INTEGER"))
            conn.execute(text("INSERT OR IGNORE INTO boards (name) VALUES ('general')"))
            board_id = conn.execute(
                text("SELECT id FROM boards WHERE name = 'general'"),
            ).scalar_one()
            conn.execute(text("UPDATE posts SET board_id = :board_id"), {"board_id": board_id})
            posts_columns.append("board_id")
        if "board_post_id" not in posts_columns:
            conn.execute(text("ALTER TABLE posts ADD COLUMN board_post_id INTEGER NOT NULL DEFAULT 0"))
            post_rows = conn.execute(text("SELECT id, board_id FROM posts ORDER BY board_id, id")).all()
            current = {}
            for row in post_rows:
                row_id, board_id = row
                current.setdefault(board_id, 0)
                current[board_id] += 1
                conn.execute(
                    text("UPDATE posts SET board_post_id = :board_post_id WHERE id = :id"),
                    {"board_post_id": current[board_id], "id": row_id},
                )
            posts_columns.append("board_post_id")
        if "parent_id" not in posts_columns:
            conn.execute(text("ALTER TABLE posts ADD COLUMN parent_id INTEGER"))
        if "upvotes" not in posts_columns:
            conn.execute(text("ALTER TABLE posts ADD COLUMN upvotes INTEGER NOT NULL DEFAULT 0"))
        if "downvotes" not in posts_columns:
            conn.execute(text("ALTER TABLE posts ADD COLUMN downvotes INTEGER NOT NULL DEFAULT 0"))
        if "board_post_id" in posts_columns:
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_board_post_id ON posts (board_id, board_post_id)"
                )
            )

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS votes (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    post_id INTEGER NOT NULL,
                    vote_type TEXT NOT NULL CHECK(vote_type IN ('up', 'down')),
                    date TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id),
                    FOREIGN KEY(post_id) REFERENCES posts(id),
                    UNIQUE(user_id, post_id)
                )
                """
            )
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_votes_user_date ON votes (user_id, date)")
        )
