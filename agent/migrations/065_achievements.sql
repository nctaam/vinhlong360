-- agent/migrations/065_achievements.sql
-- Migration 065: hệ thống thành tích — Wave 3 W3.1. `achievements` = định nghĩa
-- (seed 15 dòng), `user_achievements` = trạng thái mở khóa/tiến độ mỗi user.
-- Additive; seed qua ON CONFLICT DO NOTHING nên chạy lại an toàn.

CREATE TABLE IF NOT EXISTS achievements (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    description       TEXT,
    icon              TEXT,
    category          TEXT,          -- content | explorer | social | veteran | special
    requirement_value INT NOT NULL DEFAULT 1,
    sort_order        INT NOT NULL DEFAULT 0
);
ALTER TABLE achievements OWNER TO vl360;

CREATE TABLE IF NOT EXISTS user_achievements (
    user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_id TEXT NOT NULL REFERENCES achievements(id),
    unlocked_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, achievement_id)
);
ALTER TABLE user_achievements OWNER TO vl360;

CREATE INDEX IF NOT EXISTS idx_user_achievements_user ON user_achievements(user_id);

INSERT INTO achievements (id, name, description, icon, category, requirement_value, sort_order) VALUES
    ('first_post',    'Bài viết đầu tiên',  'Đăng bài viết đầu tiên',              '📝', 'content',  1,  1),
    ('writer_10',     'Nhà văn',            'Đăng 10 bài viết',                    '✒️', 'content',  10, 2),
    ('reviewer_5',    'Nhà phê bình',       'Viết 5 đánh giá',                     '📋', 'content',  5,  3),
    ('review_master', 'Bậc thầy đánh giá',  'Viết 25 đánh giá',                    '⭐', 'content',  25, 4),
    ('photographer',  'Nhiếp ảnh gia',      'Đăng 10 bài có ảnh',                  '📸', 'content',  10, 5),
    ('explorer_5',    'Nhà thám hiểm',      'Ghé thăm 5 địa điểm',                 '🧭', 'explorer', 5,  6),
    ('explorer_20',   'Lữ khách',           'Ghé thăm 20 địa điểm',                '🎒', 'explorer', 20, 7),
    ('local_3',       'Người địa phương',   'Khám phá 3 khu vực',                  '🏡', 'explorer', 3,  8),
    ('social_10',     'Kết nối',            'Có 10 người theo dõi',                '🤝', 'social',   10, 9),
    ('social_50',     'Ảnh hưởng',          'Có 50 người theo dõi',                '💫', 'social',   50, 10),
    ('helpful_5',     'Hữu ích',            'Có 5 câu trả lời hay nhất',           '💡', 'social',   5,  11),
    ('streak_7',      'Chăm chỉ',           'Đăng nhập 7 ngày liên tiếp',          '🔥', 'veteran',  7,  12),
    ('streak_30',     'Kiên trì',           'Đăng nhập 30 ngày liên tiếp',         '🏅', 'veteran',  30, 13),
    ('veteran_6m',    'Lão làng',           'Thành viên 6 tháng',                  '🎖️', 'veteran',  180,14),
    ('allrounder',    'Đa tài',             'Mở khóa mỗi nhóm ít nhất 1 thành tích','🌟', 'special',  4,  15)
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name, description = EXCLUDED.description, icon = EXCLUDED.icon,
    category = EXCLUDED.category, requirement_value = EXCLUDED.requirement_value,
    sort_order = EXCLUDED.sort_order;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 65, '065_achievements.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
