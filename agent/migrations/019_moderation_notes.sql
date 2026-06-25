-- B3d: Internal admin notes on posts (not visible to poster)
ALTER TABLE posts ADD COLUMN IF NOT EXISTS moderation_notes JSONB DEFAULT '[]'::jsonb;
