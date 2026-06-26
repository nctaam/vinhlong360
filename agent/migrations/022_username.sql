-- 022: Add username field for human-readable profile URLs
ALTER TABLE users ADD COLUMN IF NOT EXISTS username TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique
  ON users (lower(username)) WHERE username IS NOT NULL;
