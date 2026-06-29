-- Migration 047: Featured/admin-pinned posts on entity pages.
-- Admin can feature a post to appear at top of entity feed.

ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS featured_by UUID REFERENCES users(id);
ALTER TABLE posts ADD COLUMN IF NOT EXISTS featured_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_posts_featured
    ON posts(entity_id, featured_at DESC) WHERE is_featured = TRUE;
