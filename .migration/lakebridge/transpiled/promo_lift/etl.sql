-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'CREATE': extra input 'CREATE'. SQLSTATE: 42601 (line 3, pos 0)

== SQL ==
EXPLAIN -- promo_lift: order-value distribution per channel (MEDIAN + PERCENTILE_CONT).
DROP TABLE IF EXISTS mart.promo_lift;
CREATE OR REPLACE TABLE mart.promo_lift AS
^^^
WITH order_totals AS (
    SELECT o.order_id,
           o.sales_channel,
           SUM(oi.quantity * (oi.unit_price - oi.discount)) AS order_total
    FROM   core.orders o
    JOIN   core.order_items oi ON oi.order_id = o.order_id
    GROUP  BY o.order_id, o.sales_channel
)
SELECT sales_channel,
       COUNT(*)                                                       AS order_count,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY order_total)                                            AS median_order_value,
       PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY order_total)       AS p90_order_value
FROM   order_totals
GROUP  BY sales_channel
ORDER  BY sales_channel;

*/

 ---------------Exception End --------------------
