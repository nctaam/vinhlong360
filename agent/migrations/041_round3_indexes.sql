-- Migration 041: Indexes for round-3 features (announcements, trending, engagement).

-- Announcements: active + time-windowed queries
CREATE INDEX IF NOT EXISTS idx_announcements_active_time
    ON announcements(starts_at, expires_at)
    WHERE is_active = TRUE;

-- Rating breakdown: per-entity approved reviews with rating
CREATE INDEX IF NOT EXISTS idx_posts_entity_rating
    ON posts(entity_id, rating)
    WHERE post_type = 'review' AND moderation_status = 'approved' AND rating IS NOT NULL;

-- Trending: recent posts grouped by entity
CREATE INDEX IF NOT EXISTS idx_posts_entity_recent
    ON posts(entity_id, created_at DESC)
    WHERE entity_id IS NOT NULL AND moderation_status = 'approved';

-- Content search: ILIKE on content (trigram would be better but requires pg_trgm)
CREATE INDEX IF NOT EXISTS idx_posts_created_status
    ON posts(created_at DESC, moderation_status);

-- Admin user detail: report counts per reporter
CREATE INDEX IF NOT EXISTS idx_reports_reporter
    ON reports(reporter_id);

-- Admin post detail: reports by target
CREATE INDEX IF NOT EXISTS idx_reports_target
    ON reports(target_type, target_id);
