-- 003_create_boards_table.sql
-- Gold: boards/topics resource. Every post lives in a board; the default
-- 'general' board is seeded so posts created before any user-created
-- boards are still valid.

CREATE TABLE IF NOT EXISTS boards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

INSERT OR IGNORE INTO boards (name, description) VALUES ('general', 'Default board');
