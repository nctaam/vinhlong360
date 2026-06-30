-- Migration 028: Review responses — one official response per review post.
-- Used for business/admin replies to reviews.

CREATE TABLE IF NOT EXISTS review_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    responder_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id)
);

CREATE INDEX IF NOT EXISTS idx_review_responses_post ON review_responses(post_id);
