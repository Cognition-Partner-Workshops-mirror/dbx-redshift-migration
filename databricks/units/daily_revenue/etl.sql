-- daily_revenue: revenue and order count per day x channel.
-- Redshift DISTSTYLE ALL / SORTKEY -> CLUSTER BY on the former sort key.
CREATE OR REPLACE TABLE gold.daily_revenue
CLUSTER BY (order_date, sales_channel)
AS
SELECT CAST(o.order_ts AS DATE)                                          AS order_date,
       o.sales_channel                                                   AS sales_channel,
       CAST(COUNT(DISTINCT o.order_id) AS BIGINT)                        AS order_count,
       CAST(SUM(oi.quantity * (oi.unit_price - oi.discount)) AS DECIMAL(38,2)) AS revenue
FROM   silver.orders o
JOIN   silver.order_items oi ON oi.order_id = o.order_id
GROUP  BY 1, 2;
