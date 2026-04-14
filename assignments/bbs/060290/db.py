from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///bbs.db")


def init_db():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                bio TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """))
        # Add bio column to existing databases that were created before it was introduced
        columns = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        column_names = [c[1] for c in columns]
        if "bio" not in column_names:
            conn.execute(text("ALTER TABLE users ADD COLUMN bio TEXT"))
        # Visit counter for welcome screen frames
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS visit_counter (
                current_frame INTEGER
            )
        """))
        row = conn.execute(text("SELECT COUNT(*) FROM visit_counter")).fetchone()
        if row[0] == 0:
            conn.execute(text("INSERT INTO visit_counter (current_frame) VALUES (:frame)"),
                         {"frame": 1})


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
