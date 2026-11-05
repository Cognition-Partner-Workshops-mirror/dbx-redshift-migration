-- cohort_retention: retention matrix (cohort month x month offset).
-- Redshift TEMP TABLE steps become CTEs; DATEDIFF(month) on month-truncated
-- dates is a calendar-month boundary count.
CREATE OR REPLACE TABLE gold.cohort_retention (
    cohort_month   DATE,
    month_offset   INT,
    cohort_size    BIGINT,
    active_buyers  BIGINT
)
CLUSTER BY (cohort_month, month_offset);

INSERT OVERWRITE gold.cohort_retention
WITH cohorts AS (
    SELECT customer_id,
           CAST(DATE_TRUNC('MONTH', MIN(order_ts)) AS DATE) AS cohort_month
    FROM   silver.orders
    GROUP  BY customer_id
),
activity AS (
    SELECT c.cohort_month,
           CAST((YEAR(o.order_ts) - YEAR(c.cohort_month)) * 12
                + (MONTH(o.order_ts) - MONTH(c.cohort_month)) AS INT) AS month_offset,
           COUNT(DISTINCT c.customer_id) AS active_buyers
    FROM   silver.orders o
    JOIN   cohorts c ON c.customer_id = o.customer_id
    GROUP  BY 1, 2
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM   cohorts
    GROUP  BY cohort_month
)
SELECT s.cohort_month,
       s.month_offset,
       sz.cohort_size,
       s.active_buyers
FROM   activity s
JOIN   cohort_sizes sz ON sz.cohort_month = s.cohort_month;
