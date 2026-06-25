-- Migration 017: Add cover photo + login history
-- A1c: Cover photo for user profiles
-- A7b: Login activity log for security

ALTER TABLE users ADD COLUMN IF NOT EXISTS cover_url TEXT;

CREATE TABLE IF NOT EXISTS login_history (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    phone      TEXT NOT NULL,
    method     TEXT NOT NULL DEFAULT 'otp',
    success    BOOLEAN NOT NULL DEFAULT TRUE,
    ip         TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_login_history_user ON login_history(user_id);
CREATE INDEX IF NOT EXISTS idx_login_history_phone ON login_history(phone);
