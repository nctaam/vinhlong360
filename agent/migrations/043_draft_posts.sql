-- Migration 043: Draft posts support.
-- Allows users to save posts as drafts before publishing.

ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_draft BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_posts_user_drafts
    ON posts(user_id, updated_at DESC)
    WHERE is_draft = TRUE;
