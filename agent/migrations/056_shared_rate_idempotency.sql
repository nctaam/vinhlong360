-- Shared rate-limit and idempotency stores for multi-worker/VPS-safe writes.
-- Apply after backup: psql "$DATABASE_URL" -f agent/migrations/056_shared_rate_idempotency.sql

CREATE TABLE IF NOT EXISTS shared_rate_limits (
    key        TEXT PRIMARY KEY,
    hits       DOUBLE PRECISION[] NOT NULL DEFAULT ARRAY[]::DOUBLE PRECISION[],
    expires_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shared_rate_limits_expires_at
    ON shared_rate_limits(expires_at);

CREATE TABLE IF NOT EXISTS request_idempotency_keys (
    key           TEXT PRIMARY KEY,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at    TIMESTAMPTZ NOT NULL,
    meta          JSONB NOT NULL DEFAULT '{}'::JSONB
);

CREATE INDEX IF NOT EXISTS idx_request_idempotency_keys_expires_at
    ON request_idempotency_keys(expires_at);

CREATE TABLE IF NOT EXISTS schema_version (
    component  TEXT PRIMARY KEY,
    version    INTEGER NOT NULL,
    migration  TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 56, '056_shared_rate_idempotency.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = EXCLUDED.version,
    migration = EXCLUDED.migration,
    updated_at = NOW();
