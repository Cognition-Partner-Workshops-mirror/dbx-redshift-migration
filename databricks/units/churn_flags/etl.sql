CREATE OR REPLACE TABLE gold.churn_flags (
    customer_id      BIGINT,
    last_order_date  DATE,
    days_since_order INT,
    churn_flag       VARCHAR(16)
);

INSERT OVERWRITE gold.churn_flags
WITH last_orders AS (
    SELECT c.customer_id,
           CAST(MAX(o.order_ts) AS DATE) AS last_order_date
    FROM silver.customers c
    LEFT JOIN silver.orders o ON o.customer_id = c.customer_id
    GROUP BY c.customer_id
), recency AS (
    SELECT customer_id,
           last_order_date,
           datediff(DATE '2025-12-31', last_order_date) AS days_since_order
    FROM last_orders
)
SELECT customer_id,
       last_order_date,
       days_since_order,
       CASE
           WHEN last_order_date IS NULL THEN 'never_ordered'
           WHEN days_since_order > 180 THEN 'churned'
           WHEN days_since_order > 90 THEN 'at_risk'
           ELSE 'active'
       END AS churn_flag
FROM recency;
