-- Repair itinerary schema drift: runtime requires itineraries.areas for multi-area plans.
-- Apply after backup via scripts/apply_migrations.py.

ALTER TABLE itineraries
    ADD COLUMN IF NOT EXISTS areas JSONB DEFAULT '[]'::jsonb;

UPDATE itineraries
SET areas = CASE
    WHEN area IS NULL OR btrim(area) = '' THEN '[]'::jsonb
    ELSE to_jsonb(ARRAY[area])
END
WHERE areas IS NULL OR areas = '[]'::jsonb;

CREATE TABLE IF NOT EXISTS schema_version (
    component TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    migration TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 58, '058_itinerary_areas_schema.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
