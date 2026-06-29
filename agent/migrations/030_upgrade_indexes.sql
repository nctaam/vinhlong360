-- Migration 030: Performance indexes for upgrade endpoints.
-- Partial indexes on posts for Q&A and review queries, claims status, collections published.

CREATE INDEX IF NOT EXISTS idx_posts_entity_question
    ON posts(entity_id) WHERE post_type = 'question' AND moderation_status = 'approved';

CREATE INDEX IF NOT EXISTS idx_posts_entity_review
    ON posts(entity_id, created_at DESC) WHERE post_type = 'review' AND moderation_status = 'approved';

CREATE INDEX IF NOT EXISTS idx_entity_claims_pending
    ON entity_claims(created_at DESC) WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_collections_sort_published
    ON collections(sort_order) WHERE is_published = TRUE;

CREATE INDEX IF NOT EXISTS idx_user_visits_review_prompt
    ON user_visits(user_id, entity_id) WHERE status = 'visited';
