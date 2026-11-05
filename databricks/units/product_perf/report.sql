-- BI report: category performance.
SELECT category,
       COUNT(*)        AS products,
       SUM(units_sold) AS units_sold,
       SUM(revenue)    AS revenue
FROM   gold.product_perf
GROUP  BY category
ORDER  BY category;
