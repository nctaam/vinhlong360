-- Additive uniqueness guard for concurrent pending image candidates.

CREATE UNIQUE INDEX IF NOT EXISTS uq_image_suggestions_pending_candidate
    ON image_suggestions(entity_id, candidate_url)
    WHERE status = 'pending';

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 90, '090_image_suggestion_pending_unique.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version
                     THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
