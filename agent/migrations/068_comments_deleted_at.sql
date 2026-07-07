-- agent/migrations/068_comments_deleted_at.sql
-- Migration 068: soft-delete cho comments (SP3 W6.1). Trước đây delete_comment
-- HARD-DELETE comment gốc + cascade xóa vĩnh viễn reply con của NGƯỜI KHÁC
-- (mất UGC, không khôi phục). Thêm deleted_at để soft-delete: reply con giữ
-- lại (recoverable), display lọc deleted_at IS NULL. Lệch với posts (đã soft-
-- delete từ migration 051) nay đồng bộ. Additive.

ALTER TABLE comments ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;
-- Index phần (chỉ hàng chưa xóa) cho truy vấn list/count phổ biến.
CREATE INDEX IF NOT EXISTS idx_comments_post_active
    ON comments(post_id) WHERE deleted_at IS NULL;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 68, '068_comments_deleted_at.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
