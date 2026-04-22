-- 005_indexes.sql
-- Indexes for the foreign-key columns this API filters and joins on.
-- At 10 rows, no difference. At 10k rows, these turn table scans into
-- O(log n) lookups. Non-breaking — A1's CLI queries benefit too.

CREATE INDEX IF NOT EXISTS idx_posts_user_id     ON posts(user_id);
CREATE INDEX IF NOT EXISTS idx_posts_board       ON posts(board);
CREATE INDEX IF NOT EXISTS idx_reactions_post_id ON reactions(post_id);
CREATE INDEX IF NOT EXISTS idx_reactions_user_id ON reactions(user_id);
