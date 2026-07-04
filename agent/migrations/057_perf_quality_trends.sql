-- Performance and observability hardening for public discovery endpoints.
-- Apply after backup: psql "$DATABASE_URL" -f agent/migrations/057_perf_quality_trends.sql

ALTER TABLE entities ADD COLUMN IF NOT EXISTS status TEXT;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS verified INTEGER DEFAULT 1;

CREATE INDEX IF NOT EXISTS idx_entities_public_type_area_updated
    ON entities(type, area, "updatedAt" DESC, id)
    WHERE type <> 'place'
      AND (status IS NULL OR status <> 'provisional')
      AND (verified IS NULL OR verified <> 0);

CREATE INDEX IF NOT EXISTS idx_entities_public_area_updated
    ON entities(area, "updatedAt" DESC, id)
    WHERE type <> 'place'
      AND (status IS NULL OR status <> 'provisional')
      AND (verified IS NULL OR verified <> 0);

CREATE INDEX IF NOT EXISTS idx_entities_public_place_updated
    ON entities("placeId", "updatedAt" DESC, id)
    WHERE type <> 'place'
      AND "placeId" IS NOT NULL
      AND (status IS NULL OR status <> 'provisional')
      AND (verified IS NULL OR verified <> 0);

CREATE INDEX IF NOT EXISTS idx_entities_public_coordinates
    ON entities(type, area)
    WHERE type <> 'place'
      AND coordinates IS NOT NULL
      AND (status IS NULL OR status <> 'provisional')
      AND (verified IS NULL OR verified <> 0);

CREATE INDEX IF NOT EXISTS idx_entities_public_events_updated
    ON entities("updatedAt" DESC, id)
    WHERE type = 'event'
      AND (status IS NULL OR status <> 'provisional')
      AND (verified IS NULL OR verified <> 0);

CREATE INDEX IF NOT EXISTS idx_entities_season_gin
    ON entities USING gin(season jsonb_path_ops)
    WHERE season IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_posts_review_entity_recent_public
    ON posts(entity_id, created_at DESC)
    WHERE post_type = 'review'
      AND moderation_status = 'approved'
      AND deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS quality_metric_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_key TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    metric_unit TEXT DEFAULT 'count',
    source TEXT DEFAULT 'quality_budget',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quality_metric_snapshots_key_time
    ON quality_metric_snapshots(metric_key, created_at DESC);

CREATE TABLE IF NOT EXISTS schema_version (
    component TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    migration TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 57, '057_perf_quality_trends.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
