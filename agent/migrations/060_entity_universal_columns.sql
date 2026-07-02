-- Migration 060: GĐ-B entity split — 8 cột phổ quát thăng cấp lên entities.
-- Spec: docs/superpowers/specs/2026-07-02-entity-split-per-kind-design.md
-- Các trường mọi type đều dùng (trước nằm trong attributes JSONB). Additive:
-- cột nullable, KHÔNG đụng dữ liệu JSONB ở bước này (backfill là script riêng,
-- JSONB chỉ được dọn ở GĐ-C sau khi flip + ổn định).

ALTER TABLE entities ADD COLUMN IF NOT EXISTS address      TEXT;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS phone        TEXT;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS website      TEXT;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS hours        TEXT;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS price_range  TEXT;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS sub_category TEXT;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS best_time    TEXT;
ALTER TABLE entities ADD COLUMN IF NOT EXISTS highlight    TEXT;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 60, '060_entity_universal_columns.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
