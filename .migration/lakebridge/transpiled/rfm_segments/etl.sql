-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'CREATE': extra input 'CREATE'. SQLSTATE: 42601 (line 4, pos 0)

== SQL ==
EXPLAIN -- rfm_segments: NTILE(5) over recency/frequency/monetary as of '2025-12-31',
-- including customers with NULL metrics (NULL ordering matters).
DROP TABLE IF EXISTS mart.rfm_segments;
CREATE OR REPLACE TABLE mart.rfm_segments
^^^

ZORDER BY(customer_id)
AS
WITH metrics AS (
    SELECT c.customer_id,
           DATEDIFF(DAY, MAX(o.order_ts)::CURRENT_DATE, CURRENT_DATE '2025-12-31')        AS recency_days,
           COUNT(DISTINCT o.order_id)                                    AS frequency,
           COALESCE(SUM(oi.quantity * (oi.unit_price - oi.discount)), 0) AS monetary
    FROM   core.customers c
    LEFT JOIN core.orders      o  ON o.customer_id = c.customer_id
    LEFT JOIN core.order_items oi ON oi.order_id   = o.order_id
    GROUP  BY c.customer_id
),
tiles AS (
    SELECT customer_id,
           recency_days,
           frequency,
           monetary,
           NTILE(5) OVER (ORDER BY recency_days ASC, customer_id)             AS r_tile,
           NTILE(5) OVER (ORDER BY frequency   DESC,            customer_id)  AS f_tile,
           NTILE(5) OVER (ORDER BY monetary    DESC,            customer_id)  AS m_tile
    FROM   metrics
)
SELECT customer_id,
       recency_days,
       frequency,
       monetary,
       r_tile,
       f_tile,
       m_tile,
       (r_tile::STRING || f_tile::STRING || m_tile::STRING):: STRING AS rfm_segment
FROM   tiles
ORDER  BY customer_id;

*/

 ---------------Exception End --------------------
