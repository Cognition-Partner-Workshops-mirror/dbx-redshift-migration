-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'CREATE': extra input 'CREATE'. SQLSTATE: 42601 (line 3, pos 0)

== SQL ==
EXPLAIN -- daily_revenue: revenue and order count per day x channel.
DROP TABLE IF EXISTS mart.daily_revenue;
CREATE OR REPLACE TABLE mart.daily_revenue
^^^

ZORDER BY(order_date)
AS
SELECT TRUNC('DD', o.order_ts)::CURRENT_DATE                       AS order_date,
       o.sales_channel                               AS sales_channel,
       COUNT(DISTINCT o.order_id)                    AS order_count,
       SUM(oi.quantity * (oi.unit_price - oi.discount)) AS revenue
FROM   core.orders o
JOIN   core.order_items oi ON oi.order_id = o.order_id
GROUP  BY 1, 2
ORDER  BY 1, 2;

*/

 ---------------Exception End --------------------
