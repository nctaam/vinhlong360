-- Migration 031: Feed performance indexes.
-- Composite indexes for the most common social feed queries.

-- Main feed: filter by moderation + type, sort by created_at
CREATE INDEX IF NOT EXISTS idx_posts_feed_approved
    ON posts(created_at DESC) WHERE moderation_status = 'approved';

-- Duplicate check on post creation (user_id + content hash check)
CREATE INDEX IF NOT EXISTS idx_posts_user_recent
    ON posts(user_id, created_at DESC) WHERE moderation_status != 'rejected';

-- Notification dedup: find recent notifications by (user_id, type, actor_id)
CREATE INDEX IF NOT EXISTS idx_notifications_dedup
    ON notifications(user_id, type, created_at DESC);
