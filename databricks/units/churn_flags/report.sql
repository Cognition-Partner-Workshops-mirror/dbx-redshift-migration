SELECT churn_flag,
       COUNT(*) AS customers,
       SUM(CAST(days_since_order AS BIGINT)) DIV NULLIF(COUNT(days_since_order), 0) AS avg_days_since_order
FROM gold.churn_flags
GROUP BY churn_flag
ORDER BY churn_flag NULLS LAST;
