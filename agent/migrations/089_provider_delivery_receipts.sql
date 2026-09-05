-- Durable provider outcome classification for the case notification outbox.

ALTER TABLE case_outbox
    ADD COLUMN IF NOT EXISTS provider_state TEXT,
    ADD COLUMN IF NOT EXISTS provider_reference TEXT,
    ADD COLUMN IF NOT EXISTS provider_receipt JSONB,
    ADD COLUMN IF NOT EXISTS provider_observed_at TIMESTAMPTZ;

ALTER TABLE case_outbox DROP CONSTRAINT IF EXISTS case_outbox_status_check;
ALTER TABLE case_outbox ADD CONSTRAINT case_outbox_status_check
    CHECK (status IN ('pending', 'processing', 'sent', 'failed', 'ambiguous'));

DROP INDEX IF EXISTS idx_case_outbox_retry;
CREATE INDEX IF NOT EXISTS idx_case_outbox_retry
    ON case_outbox(available_at, outbox_id)
    WHERE status IN ('pending', 'failed');

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 89, '089_provider_delivery_receipts.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version
                     THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
