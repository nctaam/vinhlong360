-- Migration 033: Performance indexes for round 2 upgrade endpoints.

-- Entity stats: review aggregation by entity
CREATE INDEX IF NOT EXISTS idx_posts_entity_review_stats
    ON posts(entity_id) WHERE post_type = 'review'
      AND moderation_status = 'approved' AND rating IS NOT NULL;

-- Trending posts: engagement-weighted sort within time window
CREATE INDEX IF NOT EXISTS idx_posts_trending
    ON posts(created_at DESC, like_count, comment_count)
    WHERE moderation_status = 'approved';

-- User activity: user's recent posts/comments/likes
CREATE INDEX IF NOT EXISTS idx_comments_user_recent
    ON comments(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_likes_user_recent
    ON likes(user_id, created_at DESC);

-- User counts: unread notification count
CREATE INDEX IF NOT EXISTS idx_notifications_unread
    ON notifications(user_id) WHERE is_read = FALSE;

-- Saved entities count per entity (for entity stats)
CREATE INDEX IF NOT EXISTS idx_saved_entities_entity
    ON saved_entities(entity_id);

-- Follows count per entity (for entity stats)
CREATE INDEX IF NOT EXISTS idx_follows_entity_target
    ON follows(target_id) WHERE target_type = 'entity';
