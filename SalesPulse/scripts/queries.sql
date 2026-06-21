-- ============================================================================
-- SalesPulse :: Core Analysis Queries
-- Run against sales_data.db (SQLite). Each query maps directly to a business
-- question the dashboard and weekly/monthly reports are built to answer.
-- ============================================================================

-- 1. MONTHLY REVENUE TREND -----------------------------------------------
-- Used for the dashboard's trend line and the monthly report's headline KPI.
SELECT
    order_month,
    COUNT(*)                       AS num_transactions,
    ROUND(SUM(revenue), 0)         AS total_revenue,
    ROUND(AVG(revenue), 0)         AS avg_order_value
FROM sales
GROUP BY order_month
ORDER BY order_month;


-- 2. REVENUE BY REGION ------------------------------------------------------
-- "Regional performance" -- which regions drive revenue, and at what
-- average order value (helps separate "more orders" from "bigger orders").
SELECT
    region,
    COUNT(*)                                    AS num_transactions,
    ROUND(SUM(revenue), 0)                      AS total_revenue,
    ROUND(AVG(revenue), 0)                      AS avg_order_value,
    ROUND(100.0 * SUM(revenue) / (SELECT SUM(revenue) FROM sales), 1) AS pct_of_total_revenue
FROM sales
GROUP BY region
ORDER BY total_revenue DESC;


-- 3. TOP PRODUCTS BY REVENUE -------------------------------------------------
SELECT
    product_category,
    product_name,
    SUM(quantity)             AS units_sold,
    ROUND(SUM(revenue), 0)    AS total_revenue
FROM sales
GROUP BY product_category, product_name
ORDER BY total_revenue DESC
LIMIT 10;


-- 4. CATEGORY PERFORMANCE ----------------------------------------------------
SELECT
    product_category,
    COUNT(*)                  AS num_transactions,
    SUM(quantity)              AS units_sold,
    ROUND(SUM(revenue), 0)     AS total_revenue,
    ROUND(AVG(unit_price), 0)  AS avg_unit_price
FROM sales
GROUP BY product_category
ORDER BY total_revenue DESC;


-- 5. SALES CHANNEL COMPARISON (Online vs. Store) -----------------------------
SELECT
    source AS channel,
    COUNT(*)                   AS num_transactions,
    ROUND(SUM(revenue), 0)     AS total_revenue,
    ROUND(AVG(revenue), 0)     AS avg_order_value
FROM sales
GROUP BY source;


-- 6. CUSTOMER TRENDS: REPEAT VS ONE-TIME BUYERS ------------------------------
-- "Customer trends" -- segments customers by purchase frequency, a standard
-- lever for retention-focused business decisions.
WITH customer_orders AS (
    SELECT customer_id, COUNT(*) AS order_count, SUM(revenue) AS total_spent
    FROM sales
    WHERE source = 'Online'        -- customer_id is reliable for online orders
    GROUP BY customer_id
)
SELECT
    CASE WHEN order_count = 1 THEN 'One-Time' ELSE 'Repeat' END AS customer_type,
    COUNT(*)                         AS num_customers,
    ROUND(AVG(total_spent), 0)       AS avg_lifetime_spend,
    ROUND(SUM(total_spent), 0)       AS total_revenue_from_segment
FROM customer_orders
GROUP BY customer_type;


-- 7. REVENUE BY CUSTOMER SEGMENT (joins fact table to customer dimension) ----
SELECT
    c.segment,
    COUNT(DISTINCT s.customer_id)   AS num_customers,
    COUNT(*)                        AS num_transactions,
    ROUND(SUM(s.revenue), 0)        AS total_revenue,
    ROUND(AVG(s.revenue), 0)        AS avg_order_value
FROM sales s
JOIN customers c ON s.customer_id = c.customer_id
WHERE s.source = 'Online'
GROUP BY c.segment
ORDER BY total_revenue DESC;


-- 8. WEEK-OVER-WEEK TREND (last 8 weeks) -------------------------------------
-- Powers the "weekly summary report" automation.
SELECT
    order_week,
    COUNT(*)                  AS num_transactions,
    ROUND(SUM(revenue), 0)    AS total_revenue
FROM sales
GROUP BY order_week
ORDER BY order_week DESC
LIMIT 8;


-- 9. PAYMENT METHOD MIX (Online only) ----------------------------------------
SELECT
    payment_method,
    COUNT(*)                  AS num_transactions,
    ROUND(SUM(revenue), 0)    AS total_revenue
FROM sales
WHERE source = 'Online'
GROUP BY payment_method
ORDER BY total_revenue DESC;


-- 10. RETURNS IMPACT BY REGION ------------------------------------------------
-- Returns are loaded into their own table (see scripts/2_load_to_sql.py) so
-- they remain auditable rather than being silently dropped during cleaning.
SELECT
    region,
    COUNT(*)                          AS return_count,
    ROUND(SUM(quantity * unit_price), 0) AS revenue_value_returned
FROM returns
GROUP BY region
ORDER BY return_count DESC;
