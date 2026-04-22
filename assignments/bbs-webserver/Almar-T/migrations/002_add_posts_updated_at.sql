-- 002_add_posts_updated_at.sql
-- Silver: adds updated_at to posts so PATCH /posts/{id} can record edits.
-- Nullable — existing rows get NULL, meaning "never edited".

ALTER TABLE posts ADD COLUMN updated_at TEXT;
