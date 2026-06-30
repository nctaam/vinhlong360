-- Migration 038: Add is_pinned column to posts for profile pinning.
-- Users can pin up to 3 posts to the top of their profile.

ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_pinned BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_posts_pinned
    ON posts(user_id, is_pinned) WHERE is_pinned = TRUE;
