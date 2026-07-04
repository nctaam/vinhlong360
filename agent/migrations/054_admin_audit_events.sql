-- Append-only admin audit store and release schema marker.
-- Apply after backup: psql "$DATABASE_URL" -f agent/migrations/054_admin_audit_events.sql

CREATE TABLE IF NOT EXISTS admin_audit_events (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor        TEXT NOT NULL,
    actor_role   TEXT,
    actor_scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
    method       TEXT NOT NULL,
    path         TEXT NOT NULL,
    request_id   TEXT,
    ip           TEXT,
    reason       TEXT,
    before_json  JSONB,
    after_json   JSONB,
    meta         JSONB DEFAULT '{}'::JSONB
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_events_created_at
    ON admin_audit_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_events_actor
    ON admin_audit_events(actor, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_admin_audit_events_path
    ON admin_audit_events(path, created_at DESC);

CREATE TABLE IF NOT EXISTS schema_version (
    component  TEXT PRIMARY KEY,
    version    INTEGER NOT NULL,
    migration  TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 54, '054_admin_audit_events.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = EXCLUDED.version,
    migration = EXCLUDED.migration,
    updated_at = NOW();
