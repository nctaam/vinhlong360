-- Migration 027: Curated collections of entities (admin-managed).
-- Used for themed entity groups (e.g. "Top 10 món ăn Vĩnh Long").

CREATE TABLE IF NOT EXISTS collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    cover_image TEXT,
    entity_ids JSONB DEFAULT '[]',
    sort_order INTEGER DEFAULT 0,
    is_published BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_collections_published ON collections(sort_order) WHERE is_published = TRUE;
CREATE INDEX IF NOT EXISTS idx_collections_slug ON collections(slug);
