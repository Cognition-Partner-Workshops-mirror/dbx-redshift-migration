-- returns_rate: returns per category (converted from legacy Redshift).
-- Redshift INT/INT integer division -> div (Databricks `/` returns DOUBLE).
-- Redshift NUMERIC(14,4)/NUMERIC(14,4) yields scale 15, truncated; Databricks
-- rounds at scale 19, so floor(..., 15) reproduces the Redshift value
-- (quantities are non-negative, so floor == truncation).
CREATE OR REPLACE TABLE gold.returns_rate AS
SELECT p.category,
       CAST(SUM(oi.quantity) AS BIGINT)                           AS sold_qty,
       CAST(COALESCE(SUM(r.quantity), 0) AS BIGINT)               AS returned_qty,
       CAST(COALESCE(SUM(r.quantity), 0) DIV SUM(oi.quantity) AS BIGINT) AS return_rate_int,
       CAST(floor(CAST(COALESCE(SUM(r.quantity), 0) AS DECIMAL(14,4))
                  / CAST(SUM(oi.quantity) AS DECIMAL(14,4)), 15) * 100
            AS DECIMAL(38,15))                                    AS return_pct
FROM   silver.order_items oi
JOIN   silver.products p   ON p.product_id    = oi.product_id
LEFT JOIN silver.returns r ON r.order_item_id = oi.order_item_id
GROUP  BY p.category;
