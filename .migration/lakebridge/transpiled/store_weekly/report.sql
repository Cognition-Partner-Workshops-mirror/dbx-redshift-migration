-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near '('. SQLSTATE: 42601 (line 4, pos 27)

== SQL ==
EXPLAIN -- BI report: store weekly totals and span.
SELECT s.store_id,
       s.region,
       FLOOR(FLOOR(DATEDIFF($3, MIN(w.week_start)) / 7) / 7) + 1 AS active_weeks,
---------------------------^^^
       SUM(w.order_count)                                        AS order_count,
       SUM(w.revenue)                                            AS revenue
FROM   mart.store_weekly w
JOIN   core.stores s ON s.store_id = w.store_id
GROUP  BY s.store_id, s.region
ORDER  BY s.store_id;

*/

 ---------------Exception End --------------------
