-- Additive schema contract cleanup for saved items and admin roles.
-- Apply after backup: psql "$DATABASE_URL" -f agent/migrations/053_saved_kind_superadmin.sql

ALTER TABLE saved_entities ADD COLUMN IF NOT EXISTS id UUID DEFAULT uuid_generate_v4();
ALTER TABLE saved_entities ADD COLUMN IF NOT EXISTS kind TEXT DEFAULT 'entity';

UPDATE saved_entities
SET kind = 'itinerary'
WHERE entity_id LIKE 'itinerary-%' AND COALESCE(kind, 'entity') = 'entity';

UPDATE saved_entities
SET snapshot = COALESCE(snapshot, '{}'::jsonb) || jsonb_build_object('kind', kind)
WHERE kind IS NOT NULL;

ALTER TABLE saved_entities DROP CONSTRAINT IF EXISTS saved_entities_kind_check;
ALTER TABLE saved_entities
  ADD CONSTRAINT saved_entities_kind_check CHECK (kind IN ('entity', 'itinerary'));

DO $$
DECLARE
  constraint_name text;
BEGIN
  SELECT con.conname INTO constraint_name
  FROM pg_constraint con
  JOIN pg_class rel ON rel.oid = con.conrelid
  JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
  WHERE nsp.nspname = 'public'
    AND rel.relname = 'users'
    AND con.contype = 'c'
    AND pg_get_constraintdef(con.oid) LIKE '%role%'
  LIMIT 1;

  IF constraint_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE users DROP CONSTRAINT %I', constraint_name);
  END IF;
END $$;

ALTER TABLE users
  ADD CONSTRAINT users_role_check CHECK (role IN ('user', 'moderator', 'admin', 'superadmin'));
