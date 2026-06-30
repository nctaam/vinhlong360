-- Migration 051: Soft delete for posts.
-- Posts are marked deleted_at instead of hard DELETE.
-- Allows recovery and audit trail.

ALTER TABLE posts ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_posts_deleted_at ON posts(deleted_at) WHERE deleted_at IS NOT NULL;
