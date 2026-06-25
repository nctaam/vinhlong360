-- 016: Performance indexes for hot queries
-- posts.user_id: user profile, user posts listing
CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
-- comments.post_id: comment listing per post
CREATE INDEX IF NOT EXISTS idx_comments_post_id ON comments(post_id);
-- follows target: follower counts, follower listing
CREATE INDEX IF NOT EXISTS idx_follows_target ON follows(target_type, target_id);
-- notifications.user_id: notification listing
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id, created_at DESC);
