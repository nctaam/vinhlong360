-- Migration 024: Composite indexes for profile & feed performance
-- Speeds up COUNT queries in get_user_profile and user post listings

CREATE INDEX IF NOT EXISTS idx_posts_user_status_created
    ON posts(user_id, moderation_status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_users_active
    ON users(is_active) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_users_username_lower
    ON users(lower(username)) WHERE username IS NOT NULL;
