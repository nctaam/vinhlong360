-- Migration 061: GĐ-B entity split — 9 bảng CTI mở rộng theo NHÓM (kind).
-- Spec: docs/superpowers/specs/2026-07-02-entity-split-per-kind-design.md
--
-- Kiến trúc: entities GIỮ NGUYÊN làm xương sống (graph relationships trỏ
-- entities.id). Mỗi bảng dưới đây 1-1 với entities (PK = FK, CASCADE), chứa
-- các trường typed của nhóm — cột sinh từ registry agent/entity_schemas.py.
-- Additive: bảng rỗng vô hại; backfill là script riêng; nguồn sự thật CHƯA
-- đổi (vẫn attributes JSONB) cho tới GĐ-C flip sau feature flag.
--
-- Ánh xạ khóa registry -> cột (2 ngoại lệ, backfill phải dùng đúng map này):
--   food.view                -> view_note  (VIEW là keyword SQLite, tránh quoting)
--   place.architectural_style (history) -> architecture_style (chuẩn hoá drift 2 tên)

-- 🛕 attraction / nature / history
CREATE TABLE IF NOT EXISTS entity_place_details (
    entity_id          TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
    admission          TEXT,
    architecture_style TEXT,
    founding_year      INTEGER,
    religion           TEXT,
    dress_code         TEXT,
    heritage_type      TEXT,
    heritage_level     TEXT,
    historical_period  TEXT,
    waterway_type      TEXT,
    scenic_rating      INTEGER,
    best_view_point    TEXT
);
ALTER TABLE entity_place_details OWNER TO vl360;

-- 🍲 dish / drink / restaurant / cafe
CREATE TABLE IF NOT EXISTS entity_food_details (
    entity_id       TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
    origin          TEXT,
    ingredients     JSONB,
    specialty       TEXT,
    where_to_eat    TEXT,
    cooking_method  TEXT,
    main_ingredient TEXT,
    signature_dish  TEXT,
    rating          NUMERIC(3,1),
    review_count    INTEGER,
    parking         BOOLEAN,
    wifi            BOOLEAN,
    view_note       TEXT
);
ALTER TABLE entity_food_details OWNER TO vl360;

-- 🍊 product / craft_village
CREATE TABLE IF NOT EXISTS entity_product_details (
    entity_id        TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
    ocop_star        INTEGER,
    ocop_certified   BOOLEAN,
    gi_certification TEXT,
    producer         TEXT,
    variety          TEXT,
    shelf_life       TEXT,
    specialty        TEXT,
    households       INTEGER,
    raw_material     TEXT,
    recognition_date TEXT,
    cooperative      TEXT
);
ALTER TABLE entity_product_details OWNER TO vl360;

-- 🏡 accommodation
CREATE TABLE IF NOT EXISTS entity_lodging_details (
    entity_id          TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
    accommodation_type TEXT,
    star_rating        INTEGER,
    rooms              INTEGER,
    check_in           TEXT,
    check_out          TEXT,
    amenities          JSONB,
    booking_note       TEXT
);
ALTER TABLE entity_lodging_details OWNER TO vl360;

-- 🎉 event
CREATE TABLE IF NOT EXISTS entity_event_details (
    entity_id       TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
    date_start      TEXT,
    date_end        TEXT,
    lunar_date      TEXT,
    month           INTEGER,
    duration_days   INTEGER,
    organizer       TEXT,
    venue           TEXT,
    target_audience TEXT
);
ALTER TABLE entity_event_details OWNER TO vl360;

-- 🌾 experience
CREATE TABLE IF NOT EXISTS entity_experience_details (
    entity_id TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
    duration  TEXT,
    operator  TEXT
);
ALTER TABLE entity_experience_details OWNER TO vl360;

-- 🏛️ facility
CREATE TABLE IF NOT EXISTS entity_facility_details (
    entity_id         TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
    office_kind       TEXT,
    emergency_phone   TEXT,
    note_for_tourists TEXT,
    category_tag      TEXT,
    transport_type    TEXT
);
ALTER TABLE entity_facility_details OWNER TO vl360;

-- 👤 person
CREATE TABLE IF NOT EXISTS entity_person_details (
    entity_id  TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
    role       TEXT,
    birth_year INTEGER,
    death_year INTEGER,
    hometown   TEXT
);
ALTER TABLE entity_person_details OWNER TO vl360;

-- 📍 place (hành chính xã/phường)
CREATE TABLE IF NOT EXISTS entity_adminplace_details (
    entity_id        TEXT PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
    former_district  TEXT,
    merged_from      JSONB,
    population       INTEGER,
    effective_date   TEXT,
    governance_model TEXT
);
ALTER TABLE entity_adminplace_details OWNER TO vl360;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 61, '061_entity_detail_tables.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
