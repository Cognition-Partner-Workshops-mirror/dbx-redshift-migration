-- BI report: store weekly totals and span.
SELECT s.store_id,
       s.region,
       CAST(DATEDIFF(DATE_TRUNC('WEEK', MAX(w.week_start)),
                     DATE_TRUNC('WEEK', MIN(w.week_start))) DIV 7 AS BIGINT) + 1 AS active_weeks,
       SUM(w.order_count)                                        AS order_count,
       SUM(w.revenue)                                            AS revenue
FROM   gold.store_weekly w
JOIN   silver.stores s ON s.store_id = w.store_id
GROUP  BY s.store_id, s.region
ORDER  BY s.store_id;
