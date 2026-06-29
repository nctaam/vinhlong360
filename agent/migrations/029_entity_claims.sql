-- Migration 029: Entity claims — business owners can claim ownership of an entity.
-- Admin reviews and approves/rejects claims.

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
    reviewed_at TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_entity_claims_status ON entity_claims(status);
CREATE INDEX IF NOT EXISTS idx_entity_claims_entity ON entity_claims(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_claims_claimant ON entity_claims(claimant_id);
