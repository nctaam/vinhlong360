-- Migration 059: Repair the migration chain (audit 2026-07-02, top-risk #3).
--
-- (a) entity_claims: migration 037 was silently shadowed by 029 (both CREATE TABLE
--     IF NOT EXISTS entity_claims; 029 ran first without reviewer_note/UNIQUE, so
--     037 became a no-op on replay). Live code reads/writes reviewer_note. Heal
--     the end-state additively.
-- (b) entity_changes: written by admin.py on every entity edit, but DDL existed
--     only in database.py's SQLite branch — no PG migration. Create it (PG dialect
--     of database.py's SQLite DDL).
-- (c) site_settings_history: created lazily at runtime by site_settings.py only —
--     invisible to migrations/replay. Own it here (same DDL + indexes).

-- (a) entity_claims heal
ALTER TABLE entity_claims ADD COLUMN IF NOT EXISTS reviewer_note TEXT;
-- UNIQUE(entity_id, claimant_id) từ 037 — dạng unique index để IF NOT EXISTS được.
-- Nếu prod có dữ liệu trùng, migration sẽ fail to (đúng ý: phải xử lý tay, không nuốt lỗi).
CREATE UNIQUE INDEX IF NOT EXISTS idx_entity_claims_entity_claimant
    ON entity_claims(entity_id, claimant_id);

-- (b) entity_changes (PG dialect of database.py SQLite DDL)
CREATE TABLE IF NOT EXISTS entity_changes (
    id         BIGSERIAL PRIMARY KEY,
    entity_id  TEXT NOT NULL,
    field      TEXT NOT NULL,
    old_value  TEXT,
    new_value  TEXT,
    actor      TEXT DEFAULT 'admin',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_entity_changes_entity
    ON entity_changes(entity_id, created_at DESC);
ALTER TABLE entity_changes OWNER TO vl360;

-- (c) site_settings_history (DDL từ agent/site_settings.py runtime-create)
CREATE TABLE IF NOT EXISTS site_settings_history (
    id             TEXT PRIMARY KEY,
    setting_key    TEXT NOT NULL,
    category       TEXT NOT NULL,
    previous_value JSONB,
    next_value     JSONB,
    action         TEXT NOT NULL,
    actor          TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_site_settings_history_key
    ON site_settings_history(setting_key, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_site_settings_history_cat
    ON site_settings_history(category, created_at DESC);
ALTER TABLE site_settings_history OWNER TO vl360;

INSERT INTO schema_version(component, version, migration, updated_at)
VALUES ('agent', 59, '059_repair_migration_chain.sql', NOW())
ON CONFLICT (component) DO UPDATE
SET version = GREATEST(schema_version.version, EXCLUDED.version),
    migration = CASE WHEN EXCLUDED.version >= schema_version.version THEN EXCLUDED.migration ELSE schema_version.migration END,
    updated_at = NOW();
