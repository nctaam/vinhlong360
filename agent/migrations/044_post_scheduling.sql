-- Migration 044: Post scheduling support.
-- Posts can be saved with a scheduled_at timestamp for future publication.

ALTER TABLE posts ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_posts_scheduled
    ON posts(scheduled_at)
    WHERE scheduled_at IS NOT NULL AND is_draft = FALSE AND moderation_status = 'pending';
