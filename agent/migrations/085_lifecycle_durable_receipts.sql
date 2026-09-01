-- Durable lifecycle proofs for retries across workers and restarts.
CREATE TABLE IF NOT EXISTS media_delete_receipts (
    subject_id TEXT NOT NULL,
    object_key TEXT NOT NULL,
    generation TEXT NOT NULL,
    status TEXT NOT NULL,
    object_status TEXT NOT NULL,
    cdn_status TEXT NOT NULL,
    error TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (subject_id, object_key, generation)
);

CREATE TABLE IF NOT EXISTS browser_clear_instructions (
    issuance_id TEXT PRIMARY KEY,
    subject_hash TEXT NOT NULL,
    instruction_json JSONB NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_browser_clear_instructions_subject
    ON browser_clear_instructions(subject_hash, issued_at DESC);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 85, '085_lifecycle_durable_receipts.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version
                     THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
