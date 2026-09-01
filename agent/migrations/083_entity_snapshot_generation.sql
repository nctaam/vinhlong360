-- Entity snapshot generations shared by every cache consumer.
CREATE TABLE IF NOT EXISTS entity_snapshot_generation (
    entity_id TEXT PRIMARY KEY,
    generation BIGINT NOT NULL DEFAULT 0,
    issued_at TIMESTAMPTZ NOT NULL
);

ALTER TABLE entity_snapshot_generation OWNER TO vl360;

INSERT INTO schema_version (component, version, migration, updated_at)
VALUES ('agent', 83, '083_entity_snapshot_generation', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version
                     THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
