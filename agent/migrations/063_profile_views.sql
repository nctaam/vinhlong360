-- Migration 063: theo dõi lượt xem hồ sơ — Wave 2 "Activity Timeline + Profile
-- Depth", Task 1. Dedup theo (viewer, viewed, ngày) qua UNIQUE constraint +
-- ON CONFLICT DO NOTHING (xem _log_profile_view trong social.py) — 1 người
-- xem lại nhiều lần/ngày không bị đếm trùng. Chỉ chủ hồ sơ thấy view_count_7d
-- của chính mình (không lộ cho người khác).
-- Apply sau backup: psql "$DATABASE_URL" -f agent/migrations/063_profile_views.sql

CREATE TABLE IF NOT EXISTS profile_views (
    id           BIGSERIAL PRIMARY KEY,
    viewer_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    viewed_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    viewed_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(viewer_id, viewed_id, viewed_date)
);
ALTER TABLE profile_views OWNER TO vl360;

CREATE INDEX IF NOT EXISTS idx_profile_views_viewed_id_date
    ON profile_views(viewed_id, viewed_date);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 63, '063_profile_views.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
