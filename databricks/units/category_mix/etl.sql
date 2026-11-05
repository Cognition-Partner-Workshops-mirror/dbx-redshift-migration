-- category_mix: revenue share per product category (Redshift RATIO_TO_REPORT -> value / SUM() OVER ()).
CREATE OR REPLACE TABLE gold.category_mix AS
SELECT category,
       units_sold,
       revenue,
       try_divide(CAST(revenue AS DOUBLE), SUM(CAST(revenue AS DOUBLE)) OVER ()) AS revenue_share
FROM (
    SELECT p.category,
           CAST(SUM(oi.quantity) AS BIGINT)                  AS units_sold,
           SUM(oi.quantity * (oi.unit_price - oi.discount))  AS revenue
    FROM   silver.order_items oi
    JOIN   silver.products p ON p.product_id = oi.product_id
    GROUP  BY p.category
) x;
