-- Redshift NUMERIC AVG truncates at the input scale; divide integer cents.
CREATE OR REPLACE TABLE gold.customer_ltv
CLUSTER BY (customer_id)
AS
SELECT c.customer_id,
       rpad(c.region, 4, ' ')                                      AS region,
       silver.f_clean_phone(c.phone)                              AS clean_phone,
       COUNT(DISTINCT o.order_id)                                 AS order_count,
       COALESCE(SUM(oi.quantity * (oi.unit_price - oi.discount)), 0) AS ltv,
       CAST((SUM(oi.unit_price - oi.discount) * 100
             DIV NULLIF(COUNT(oi.unit_price - oi.discount), 0)) / 100
            AS DECIMAL(38,2))                                     AS aov
FROM   silver.customers c
LEFT JOIN silver.orders      o  ON o.customer_id = c.customer_id
LEFT JOIN silver.order_items oi ON oi.order_id   = o.order_id
GROUP  BY c.customer_id, c.region, c.phone
ORDER  BY c.customer_id;
