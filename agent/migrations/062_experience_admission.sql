-- Migration 062: bổ sung cột thiếu — registry experience có field `admission`
-- (vé/phí vào cửa) nhưng 061 tạo entity_experience_details thiếu nó. Backfill
-- prod phát hiện khi INSERT (UndefinedColumn, transaction rollback toàn bộ —
-- không mất dữ liệu). Test coverage đã được siết per-table để bịt lỗ hổng
-- (containment toàn file che mất vì admission có ở bảng place).

ALTER TABLE entity_experience_details ADD COLUMN IF NOT EXISTS admission TEXT;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 62, '062_experience_admission.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
