-- Migration 042: Share tracking on posts.

ALTER TABLE posts ADD COLUMN IF NOT EXISTS share_count INTEGER DEFAULT 0;
