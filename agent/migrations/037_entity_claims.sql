-- Migration 037: Entity claims (users claim ownership of business listings).

CREATE TABLE IF NOT EXISTS entity_claims (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_id TEXT NOT NULL,
    claimant_id UUID NOT NULL REFERENCES users(id),
    business_name TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    contact_email TEXT,
    evidence TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewer_id UUID REFERENCES users(id),
    reviewer_note TEXT,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(entity_id, claimant_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_claims_status
    ON entity_claims(status) WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_entity_claims_entity
    ON entity_claims(entity_id);
