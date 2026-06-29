-- Migration 046: Post edit history.
-- Saves a snapshot of previous content before each edit for transparency.

CREATE TABLE IF NOT EXISTS post_edit_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    editor_id UUID NOT NULL REFERENCES users(id),
    old_content TEXT NOT NULL,
    old_rating SMALLINT,
    edit_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_post_edit_history_post ON post_edit_history(post_id, created_at DESC);
