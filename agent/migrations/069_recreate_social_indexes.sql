-- agent/migrations/069_recreate_social_indexes.sql
-- Migration 069: tái tạo 3 index social bị xoá NHẦM ở commit 5c09a00 (khi dời các
-- CREATE INDEX inline từ database.py sang migrations, 3 cái này không được tái tạo).
-- Phát hiện qua job CI test-pg (TestPhase14PgIndexes). Additive, IF NOT EXISTS (an toàn chạy lại).
--   - idx_follows_follower: follows(follower_id) — "ai theo dõi X" / feed. (PK leftmost đã là
--     follower_id nhưng index tường minh cho rõ ý định + parity Phase-14.)
--   - idx_follows_target: follows(target_type, target_id) — reverse "ai theo dõi entity/user này".
--   - idx_entity_ratings: entity_ratings(entity_id) — entity_id là PK (index ngầm); tên tường minh.

CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows(follower_id);
CREATE INDEX IF NOT EXISTS idx_follows_target ON follows(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_entity_ratings ON entity_ratings(entity_id);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 69, '069_recreate_social_indexes.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
