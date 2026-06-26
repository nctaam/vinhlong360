-- 021: Notification preferences per user
-- Each boolean controls whether the user wants to receive that notification type.
-- Defaults to TRUE (opt-out model).
CREATE TABLE IF NOT EXISTS notification_preferences (
    user_id      UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    pref_like    BOOLEAN NOT NULL DEFAULT TRUE,
    pref_comment BOOLEAN NOT NULL DEFAULT TRUE,
    pref_mention BOOLEAN NOT NULL DEFAULT TRUE,
    pref_follow  BOOLEAN NOT NULL DEFAULT TRUE,
    pref_system  BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
