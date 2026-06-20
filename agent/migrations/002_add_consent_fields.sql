-- Migration 002: Add consent tracking fields to users table
-- Required for NĐ147 compliance
ALTER TABLE users ADD COLUMN IF NOT EXISTS consent_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS consent_version TEXT;
