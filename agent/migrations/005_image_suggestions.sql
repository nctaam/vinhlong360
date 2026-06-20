-- Migration 005: image_suggestions — human-in-the-loop review queue (P2, review-gated)
--
-- Why: ingest scripts (Wikimedia/Commons) fuzzy-match entity names and are wrong
-- ~50% of the time. NOTHING goes live without explicit admin approval (B6).
-- This table queues image candidates with full attribution; admin approves/rejects
-- on /admin/duyet-anh. On approve, the backend re-encodes + uploads to R2 and stores
-- license + author + source on the entity (attributes.image_credits) per B6.
--
-- Postgres-only in prod (UGC/admin data, dev/prod parity per architecture decision).
-- SQLite dev uses the equivalent DDL created lazily by agent/image_suggestions.py.
-- Safe to re-run.

CREATE TABLE IF NOT EXISTS image_suggestions (
    id               TEXT PRIMARY KEY,                        -- uuid hex
    entity_id        TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    candidate_url    TEXT NOT NULL,                           -- Commons/licensed source URL
    wp_title         TEXT DEFAULT '',                         -- Wikipedia article title (review context)
    license          TEXT DEFAULT '',                         -- license short name (CC-BY-SA, CC0, ...)
    author           TEXT DEFAULT '',                         -- artist/author (B6 attribution)
    source           TEXT DEFAULT 'wikipedia-vi',             -- source type
    match_confidence REAL DEFAULT 0.7,                        -- fuzzy match score 0.0-1.0 (advisory)
    status           TEXT NOT NULL DEFAULT 'pending',         -- pending | approved | rejected
    rejection_reason TEXT DEFAULT '',
    approved_by      TEXT DEFAULT '',
    approved_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_image_suggestions_status ON image_suggestions(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_image_suggestions_entity ON image_suggestions(entity_id);

-- Match table ownership to the app role (other tables created by init.sql are owned
-- by vl360). Run AFTER the CREATE TABLE so prod inserts/updates have privileges.
ALTER TABLE image_suggestions OWNER TO vl360;
