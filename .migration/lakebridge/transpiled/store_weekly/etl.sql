-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'CREATE': extra input 'CREATE'. SQLSTATE: 42601 (line 3, pos 0)

== SQL ==
EXPLAIN -- store_weekly: weekly revenue per store.
DROP TABLE IF EXISTS mart.store_weekly;
CREATE OR REPLACE TABLE mart.store_weekly
^^^

ZORDER BY(store_id)
AS
SELECT o.store_id,
       DATE_TRUNC('week', o.order_ts)::CURRENT_DATE                        AS week_start,
       DATEADD(day, 6, DATE_TRUNC('week', o.order_ts))::CURRENT_DATE       AS week_end,
       FLOOR(FLOOR(DATEDIFF($3, CURRENT_DATE '2025-01-01') / 7) / 7)             AS week_number,
       COUNT(DISTINCT o.order_id)                                 AS order_count,
       SUM(oi.quantity * (oi.unit_price - oi.discount))            AS revenue
FROM   core.orders o
JOIN   core.order_items oi ON oi.order_id = o.order_id
GROUP  BY o.store_id, DATE_TRUNC('week', o.order_ts)
ORDER  BY o.store_id, week_start;

*/

 ---------------Exception End --------------------
