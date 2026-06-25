-- 020: Feed performance indexes
-- Composite index for feed queries (WHERE moderation_status='approved' ORDER BY created_at DESC)
CREATE INDEX IF NOT EXISTS idx_posts_status_created ON posts(moderation_status, created_at DESC);
-- Composite index for user-specific feed queries
CREATE INDEX IF NOT EXISTS idx_posts_user_status_created ON posts(user_id, moderation_status, created_at DESC);
-- GIN index for hashtag filtering (?tag= queries)
CREATE INDEX IF NOT EXISTS idx_posts_hashtags_gin ON posts USING GIN(hashtags);
-- Likes lookup by user (for enriching feed with user_liked status)
CREATE INDEX IF NOT EXISTS idx_likes_user_id ON likes(user_id);
-- Bookmarks lookup by user
CREATE INDEX IF NOT EXISTS idx_bookmarks_user_id ON bookmarks(user_id);
