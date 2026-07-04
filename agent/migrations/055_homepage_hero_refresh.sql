-- Refresh homepage hero defaults when production still has the previous seed values.
-- Apply after backup: psql "$DATABASE_URL" -f agent/migrations/055_homepage_hero_refresh.sql

WITH desired(key, value, category, label, description, input_type) AS (
    VALUES
    (
        'homepage.hero_subtitle',
        to_jsonb('Tìm điểm đến, món ngon, lễ hội và lịch trình phù hợp cho chuyến đi Vĩnh Long hôm nay.'::text),
        'homepage',
        'Hero subtitle',
        'Dòng mô tả dưới thanh tìm kiếm trang chủ',
        'textarea'
    ),
    (
        'homepage.search_placeholder',
        to_jsonb('Tìm điểm đến, món ngon, lịch trình…'::text),
        'homepage',
        'Placeholder tìm kiếm',
        'Placeholder cho ô tìm kiếm trang chủ',
        'text'
    ),
    (
        'homepage.hero_pills',
        '[
            {"emoji": "📍", "label": "Gần tôi", "to": "/ban-do?near=1"},
            {"emoji": "🍲", "label": "Ăn gì hôm nay", "to": "/kham-pha/am-thuc"},
            {"emoji": "🗓️", "label": "Đi 2N1Đ", "to": "/lich-trinh"},
            {"emoji": "🌿", "label": "Miệt vườn", "to": "/du-lich"},
            {"emoji": "🗺️", "label": "Bản đồ", "to": "/ban-do"},
            {"emoji": "🎁", "label": "Đặc sản làm quà", "to": "/ocop"}
        ]'::jsonb,
        'homepage',
        'Quick pills',
        'Các nút nhanh dưới hero (mảng JSON gồm emoji, label, to)',
        'json'
    )
),
previous(key, value) AS (
    VALUES
    (
        'homepage.hero_subtitle',
        to_jsonb('Trải nghiệm miệt vườn sông nước, đặc sản theo mùa, OCOP, làng nghề, và lịch trình gợi ý — tất cả ở một nơi.'::text)
    ),
    (
        'homepage.search_placeholder',
        to_jsonb('Tìm: chôm chôm, kẹo dừa, homestay Cái Bè…'::text)
    ),
    (
        'homepage.search_placeholder',
        to_jsonb('Tìm: chôm chôm, kẹo dừa, homestay Bến Tre…'::text)
    ),
    (
        'homepage.hero_pills',
        '[
            {"emoji": "🍊", "label": "Trái cây", "to": "/kham-pha/trai-cay"},
            {"emoji": "🏡", "label": "Homestay", "to": "/kham-pha/homestay"},
            {"emoji": "🛶", "label": "Sông nước", "to": "/kham-pha/song-nuoc"},
            {"emoji": "🧁", "label": "Đặc sản", "to": "/san-pham"},
            {"emoji": "🎭", "label": "Lễ hội", "to": "/le-hoi"},
            {"emoji": "🗺️", "label": "Bản đồ", "to": "/ban-do"}
        ]'::jsonb
    )
)
INSERT INTO site_settings (key, value, category, label, description, input_type, updated_at)
SELECT key, value, category, label, description, input_type, NOW()
FROM desired
ON CONFLICT (key) DO UPDATE
SET value = EXCLUDED.value,
    label = EXCLUDED.label,
    description = EXCLUDED.description,
    input_type = EXCLUDED.input_type,
    updated_at = NOW()
WHERE EXISTS (
    SELECT 1
    FROM previous
    WHERE previous.key = EXCLUDED.key
      AND previous.value = site_settings.value
);

CREATE TABLE IF NOT EXISTS schema_version (
    component  TEXT PRIMARY KEY,
    version    INTEGER NOT NULL,
    migration  TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 55, '055_homepage_hero_refresh.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = EXCLUDED.version,
    migration = EXCLUDED.migration,
    updated_at = NOW();
