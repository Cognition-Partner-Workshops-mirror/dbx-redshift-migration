-- promo_lift: order-value distribution per channel (MEDIAN + PERCENTILE_CONT).
-- Redshift MEDIAN / PERCENTILE_CONT over NUMERIC(38,2) interpolate exactly and
-- truncate the result to the input scale; Databricks percentile_cont returns
-- DOUBLE and would round. Interpolate on DECIMAL and truncate to 2 places.
CREATE OR REPLACE TABLE gold.promo_lift AS
WITH order_totals AS (
    SELECT o.order_id,
           o.sales_channel,
           SUM(oi.quantity * (oi.unit_price - oi.discount)) AS order_total
    FROM   silver.orders o
    JOIN   silver.order_items oi ON oi.order_id = o.order_id
    GROUP  BY o.order_id, o.sales_channel
),
ranked AS (
    SELECT sales_channel,
           order_total,
           ROW_NUMBER() OVER (PARTITION BY sales_channel ORDER BY order_total) AS rn,
           COUNT(*)     OVER (PARTITION BY sales_channel)                      AS n
    FROM   order_totals
),
positions AS (
    SELECT sales_channel, order_total, rn, n,
           1 + (n - 1) * 0.5 AS pos_50,
           1 + (n - 1) * 0.9 AS pos_90
    FROM   ranked
),
bounds AS (
    SELECT sales_channel,
           MAX(n)                                                         AS order_count,
           MAX(CASE WHEN rn = FLOOR(pos_50)   THEN order_total END)       AS lo_50,
           MAX(CASE WHEN rn = CEIL(pos_50)    THEN order_total END)       AS hi_50,
           MAX(pos_50 - FLOOR(pos_50))                                    AS frac_50,
           MAX(CASE WHEN rn = FLOOR(pos_90)   THEN order_total END)       AS lo_90,
           MAX(CASE WHEN rn = CEIL(pos_90)    THEN order_total END)       AS hi_90,
           MAX(pos_90 - FLOOR(pos_90))                                    AS frac_90
    FROM   positions
    GROUP  BY sales_channel
),
interpolated AS (
    SELECT sales_channel,
           order_count,
           lo_50 + frac_50 * (hi_50 - lo_50) AS median_exact,
           lo_90 + frac_90 * (hi_90 - lo_90) AS p90_exact
    FROM   bounds
)
SELECT sales_channel,
       CAST(order_count AS BIGINT)                                                    AS order_count,
       CAST(CASE WHEN median_exact >= 0 THEN FLOOR(median_exact, 2)
                 ELSE CEIL(median_exact, 2) END AS DECIMAL(38,2))                    AS median_order_value,
       CAST(CASE WHEN p90_exact >= 0 THEN FLOOR(p90_exact, 2)
                 ELSE CEIL(p90_exact, 2) END AS DECIMAL(38,2))                       AS p90_order_value
FROM   interpolated
ORDER  BY sales_channel;
