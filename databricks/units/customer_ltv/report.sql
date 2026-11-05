-- Preserve CHAR(4) padding and Redshift's scale-2, truncated NUMERIC AVG.
SELECT region,
       COUNT(*)         AS customers,
       SUM(order_count) AS orders,
       SUM(ltv)         AS total_ltv,
       CAST((SUM(ltv) * 100 DIV NULLIF(COUNT(ltv), 0)) / 100
            AS DECIMAL(38,2)) AS avg_ltv
FROM   gold.customer_ltv
GROUP  BY region
ORDER  BY region;
