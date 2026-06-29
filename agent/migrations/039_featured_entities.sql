-- Migration 039: Featured entities (admin-curated highlights).

CREATE TABLE IF NOT EXISTS featured_entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id TEXT NOT NULL UNIQUE,
    sort_order INTEGER DEFAULT 0,
    added_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_featured_entities_order
    ON featured_entities(sort_order);
