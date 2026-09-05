-- Canonical report authority. Additive migration for the existing reports table.

ALTER TABLE reports ALTER COLUMN reporter_id DROP NOT NULL;

ALTER TABLE reports ADD COLUMN IF NOT EXISTS actor_scope TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS reporter_hash TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS detail TEXT NOT NULL DEFAULT '';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS contact_ciphertext TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS field TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE reports ADD COLUMN IF NOT EXISTS resolved_by TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS correlation_id TEXT;
ALTER TABLE reports ADD COLUMN IF NOT EXISTS source_channel TEXT NOT NULL DEFAULT 'legacy';
ALTER TABLE reports ADD COLUMN IF NOT EXISTS legacy_locator TEXT;

ALTER TABLE reports DROP CONSTRAINT IF EXISTS reports_target_type_check;
ALTER TABLE reports ADD CONSTRAINT reports_target_type_check
    CHECK (target_type IN ('post', 'comment', 'user', 'entity', 'facility', 'stale_field'));

ALTER TABLE reports DROP CONSTRAINT IF EXISTS reports_status_check;
ALTER TABLE reports ADD CONSTRAINT reports_status_check
    CHECK (status IN ('pending', 'reviewed', 'dismissed', 'resolved'));

CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_actor_idempotency
    ON reports(actor_scope, idempotency_key);
CREATE UNIQUE INDEX IF NOT EXISTS uq_reports_legacy_locator
    ON reports(legacy_locator);
CREATE INDEX IF NOT EXISTS idx_reports_target_status
    ON reports(target_type, target_id, status);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 87, '087_report_authority.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version
                     THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
