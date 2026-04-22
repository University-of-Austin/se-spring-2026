-- 004_add_posts_board.sql
-- Gold: every post belongs to a board. Uses the board name (not FK id)
-- for API ergonomics. Existing posts get 'general' via the DEFAULT.

ALTER TABLE posts ADD COLUMN board TEXT NOT NULL DEFAULT 'general';
