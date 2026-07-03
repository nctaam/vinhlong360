-- Migration 064: theo dõi chuỗi đăng nhập liên tiếp — Wave 3 "Achievement
-- System + Engagement", W3.3. login_streak tăng khi đăng nhập vào ngày kế
-- tiếp last_login_date; reset về 1 nếu cách >1 ngày; giữ nguyên nếu cùng ngày.
-- Nuôi 2 achievement streak_7/streak_30 (xem achievements.py). Additive.
-- Apply sau backup: psql "$DATABASE_URL" -f agent/migrations/064_login_streak.sql

ALTER TABLE users ADD COLUMN IF NOT EXISTS login_streak INT NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_date DATE;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 64, '064_login_streak.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
