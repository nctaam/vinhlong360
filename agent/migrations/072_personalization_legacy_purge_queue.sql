-- Migration 072: durable post-commit legacy personalization purge work.
-- No foreign key: the owning user row is deleted before this outbox job runs.

CREATE TABLE IF NOT EXISTS personalization_legacy_purge_queue (
    user_id         UUID PRIMARY KEY,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    attempt_count   INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_error      TEXT
);

CREATE INDEX IF NOT EXISTS idx_personalization_legacy_purge_queue_due
    ON personalization_legacy_purge_queue(next_attempt_at, created_at);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 72, '072_personalization_legacy_purge_queue.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
