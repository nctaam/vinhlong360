-- Migration 050: Admin internal notes on user profiles.
-- CRM-like notes for moderation context (warnings, observations, etc.)

CREATE TABLE IF NOT EXISTS admin_user_notes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    admin_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_user_notes_user ON admin_user_notes(user_id, created_at DESC);
