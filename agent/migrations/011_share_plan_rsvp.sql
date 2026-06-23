-- T2 publish itinerary công-khai + T3 RSVP lễ-hội/sự-kiện.
-- Áp prod: psql "$DATABASE_URL" -f agent/migrations/011_share_plan_rsvp.sql  (additive)

ALTER TABLE user_plans ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS event_rsvp (
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_id  TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_event_rsvp_entity ON event_rsvp(entity_id);
