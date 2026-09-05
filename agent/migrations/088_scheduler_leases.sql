-- Durable cross-worker scheduler lease and execution receipt authority.

CREATE TABLE IF NOT EXISTS scheduler_task_slots (
    task_name TEXT NOT NULL,
    slot_key TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    lease_id UUID NOT NULL UNIQUE,
    lease_until TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('leased', 'finished')),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    outcome TEXT,
    receipt_json JSONB,
    PRIMARY KEY (task_name, slot_key)
);

CREATE INDEX IF NOT EXISTS idx_scheduler_task_slots_lease_until
    ON scheduler_task_slots(lease_until);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 88, '088_scheduler_leases.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version
                     THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
