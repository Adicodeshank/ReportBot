-- =============================================================================
-- seed.sql
-- =============================================================================
-- Run this once in psql or DBeaver to set up your test database.
--
--   psql -U myuser -d mydb -f sql/seed.sql
--
-- =============================================================================

-- ── Create tables ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    email       TEXT        NOT NULL UNIQUE,
    signup_date TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS orders (
    id      SERIAL PRIMARY KEY,
    user_id INTEGER     NOT NULL REFERENCES users(id),
    amount  NUMERIC(10,2) NOT NULL,
    status  TEXT        NOT NULL CHECK (status IN ('completed', 'pending', 'cancelled'))
);

-- ── Seed data ─────────────────────────────────────────────────────────────────
-- Using NOW() - INTERVAL so data is always "yesterday" relative to today.
-- This means your query will always return rows when you test it.

-- Yesterday's users (these will appear in the report)
INSERT INTO users (email, signup_date) VALUES
    ('sarah@example.com', NOW() - INTERVAL '1 day'), -- interval 1 day means 24hr
    ('mike@example.com',  NOW() - INTERVAL '1 day'),
    ('priya@example.com', NOW() - INTERVAL '1 day');

-- Older user (will NOT appear in new_users count, but their orders could)
INSERT INTO users (email, signup_date) VALUES
    ('raj@example.com',   NOW() - INTERVAL '5 days');

-- Yesterday's orders (linked to yesterday's users)
INSERT INTO orders (user_id, amount, status)
SELECT u.id, 55.00, 'completed' FROM users u WHERE u.email = 'sarah@example.com';

INSERT INTO orders (user_id, amount, status)
SELECT u.id, 120.50, 'completed' FROM users u WHERE u.email = 'mike@example.com';

INSERT INTO orders (user_id, amount, status)
SELECT u.id, 40.00, 'pending' FROM users u WHERE u.email = 'priya@example.com';

INSERT INTO orders (user_id, amount, status)
SELECT u.id, 200.00, 'cancelled' FROM users u WHERE u.email = 'priya@example.com';

-- Older order (will NOT appear in the report — it belongs to an older user)
INSERT INTO orders (user_id, amount, status)
SELECT u.id, 300.00, 'completed' FROM users u WHERE u.email = 'raj@example.com';

