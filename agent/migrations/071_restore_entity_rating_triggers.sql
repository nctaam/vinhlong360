-- Restore rating trigger wiring. Migration 070 owns the corrected function body.
DROP TRIGGER IF EXISTS trg_entity_ratings ON posts;
CREATE TRIGGER trg_entity_ratings
    AFTER INSERT OR UPDATE ON posts
    FOR EACH ROW
    WHEN (NEW.post_type = 'review')
    EXECUTE FUNCTION update_entity_ratings();

DROP TRIGGER IF EXISTS trg_entity_ratings_del ON posts;
CREATE TRIGGER trg_entity_ratings_del
    AFTER DELETE ON posts
    FOR EACH ROW
    WHEN (OLD.post_type = 'review')
    EXECUTE FUNCTION update_entity_ratings();

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 71, '071_restore_entity_rating_triggers.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE
        WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration
        ELSE schema_version.migration
    END,
    updated_at = NOW();
