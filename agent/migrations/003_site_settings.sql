-- Migration 003: site_settings table for CMS admin
-- Stores all configurable website elements (nav, footer, SEO, theme, etc.)
-- Postgres-only (UGC/config data per architecture decision)

CREATE TABLE IF NOT EXISTS site_settings (
    key         TEXT PRIMARY KEY,
    value       JSONB NOT NULL,
    category    TEXT NOT NULL,
    label       TEXT NOT NULL DEFAULT '',
    description TEXT DEFAULT '',
    input_type  TEXT DEFAULT 'text',
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_site_settings_cat ON site_settings(category);
