-- Migration 018: Privacy settings per user
-- A7a: Let users control profile visibility and activity display

CREATE TABLE IF NOT EXISTS user_privacy (
    user_id            UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    profile_visibility TEXT DEFAULT 'public' CHECK (profile_visibility IN ('public', 'followers', 'private')),
    show_activity      BOOLEAN DEFAULT TRUE,
    show_saved         BOOLEAN DEFAULT TRUE,
    updated_at         TIMESTAMPTZ DEFAULT NOW()
);
