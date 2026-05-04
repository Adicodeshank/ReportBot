-- =============================================================================
-- daily_summary.sql
-- =============================================================================
-- SCHEMA:
--   users  (id, email, signup_date)
--   orders (id, user_id, amount, status)
--
-- PURPOSE:
--   For a given day, answer:
--     1. How many new users signed up?
--     2. How many orders were placed (by new users that day)?
--     3. What was the total revenue from completed orders?
--     4. What was the average and max order value?
--     5. How many orders are pending / cancelled?
--
-- PARAMETERS (injected by Python at runtime):
--   :start_date  → the report date   e.g. 2026-04-15
--   :end_date    → the next day      e.g. 2026-04-16
-- =============================================================================

WITH

-- ── CTE 1: New users who signed up yesterday ──────────────────────────────────
-- Aggregated separately so the JOIN below doesn't distort the count.
new_users AS (
    SELECT
        COUNT(*)    AS new_user_count
    FROM
        users
    WHERE
        signup_date >= :start_date
        AND signup_date <  :end_date
),

-- ── CTE 2: Orders linked to yesterday's activity ───────────────────────────
-- JOIN orders → users so we can filter by signup_date.
-- When your orders table later gets its own created_at column,
-- simply swap the WHERE to: o.created_at >= :start_date AND o.created_at < :end_date
daily_orders AS (
    SELECT
        o.id,
        o.user_id,
        o.amount,
        o.status
    FROM
        orders  o
        JOIN users u ON o.user_id = u.id
    WHERE
        u.signup_date >= :start_date
        AND u.signup_date <  :end_date
)

-- ── Final SELECT: one summary row for the report ──────────────────────────────
SELECT

    CAST(:start_date AS DATE)                                       AS report_date,

    -- New signups (pulled from separate CTE to avoid JOIN inflation)
    (SELECT new_user_count FROM new_users)                          AS new_users,

    -- Total orders placed
    COUNT(*)                                                        AS total_orders,

    -- Revenue: only completed orders count as earned money
    ROUND(
        COALESCE(SUM(amount) FILTER (WHERE status = 'completed'), 0)::NUMERIC
    , 2)                                                            AS total_revenue,

    -- Average order value across all orders
    ROUND(
        COALESCE(AVG(amount), 0)::NUMERIC
    , 2)                                                            AS avg_order_value,

    -- Biggest single order of the day
    ROUND(
        COALESCE(MAX(amount), 0)::NUMERIC
    , 2)                                                            AS max_order_value,

    -- Status breakdown — useful for operations team
    COUNT(*) FILTER (WHERE status = 'completed')                    AS completed_orders,
    COUNT(*) FILTER (WHERE status = 'pending')                      AS pending_orders,
    COUNT(*) FILTER (WHERE status = 'cancelled')                    AS cancelled_orders

FROM
    daily_orders;