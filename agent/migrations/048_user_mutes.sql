-- Migration 048: User muting (soft block).
-- Muted users' posts/comments are hidden from the muter's feed,
-- but muted users can still see the muter's content.

CREATE TABLE IF NOT EXISTS user_mutes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    muted_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, muted_id)
);

CREATE INDEX IF NOT EXISTS idx_user_mutes_user ON user_mutes(user_id);
