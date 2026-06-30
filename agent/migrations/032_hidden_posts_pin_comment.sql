-- Migration 032: Hidden posts (mute) + pinned comments.

-- Users can hide individual posts from their feed
CREATE TABLE IF NOT EXISTS user_hidden_posts (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, post_id)
);

CREATE INDEX IF NOT EXISTS idx_hidden_posts_user
    ON user_hidden_posts(user_id);

-- Post authors can pin one comment per post
ALTER TABLE posts ADD COLUMN IF NOT EXISTS pinned_comment_id UUID REFERENCES comments(id);
