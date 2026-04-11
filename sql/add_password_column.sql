-- ============================================================
-- Migration: Add password column to users table
-- Run this ONCE against your egypt_transport database:
--   psql -U postgres -d egypt_transport -f sql/add_password_column.sql
-- ============================================================

-- Add 'password' column to users table (nullable so existing rows are unaffected)
ALTER TABLE users ADD COLUMN IF NOT EXISTS password TEXT;

-- Existing users (Omar, Sara, Ahmed, ...) have NULL passwords.
-- They will need to register via /api/users/register to set a password.
-- Until they do, they cannot log in through the API.
-- If you want to give existing users a temporary default password, run:
--   UPDATE users SET password = 'changeme' WHERE password IS NULL;

-- Verify
SELECT user_id, name,
       CASE WHEN password IS NULL THEN 'NO PASSWORD (needs registration)'
            ELSE 'HAS PASSWORD'
       END AS password_status
FROM users
ORDER BY user_id
LIMIT 10;
