-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'CREATE': extra input 'CREATE'. SQLSTATE: 42601 (line 3, pos 0)

== SQL ==
EXPLAIN -- cohort_retention: TEMP TABLE steps + DATEDIFF(month) retention matrix.
DROP TABLE IF EXISTS mart.cohort_retention;
CREATE OR REPLACE TABLE mart.cohort_retention (
^^^
    cohort_month   DATE,
    month_offset   INT,
    cohort_size    BIGINT,
    active_buyers  BIGINT
)
ZORDER BY(cohort_month);

DROP TABLE IF EXISTS tmp_cohorts;
CREATE TEMP TABLE tmp_cohorts AS
SELECT customer_id,
       DATE_TRUNC('month', MIN(order_ts))::CURRENT_DATE AS cohort_month
FROM   core.orders
GROUP  BY customer_id;

DROP TABLE IF EXISTS tmp_activity;
CREATE TEMP TABLE tmp_activity AS
SELECT c.cohort_month,
       MONTH(DATE_TRUNC('month', o.order_ts)::CURRENT_DATE) - MONTH(c.cohort_month) + 12 * (YEAR(DATE_TRUNC('month', o.order_ts)::CURRENT_DATE) - YEAR(DATE_TRUNC('month', o.order_ts)::CURRENT_DATE)) AS month_offset,
       COUNT(DISTINCT c.customer_id)                                     AS active_buyers
FROM   core.orders o
JOIN   tmp_cohorts c ON c.customer_id = o.customer_id
GROUP  BY c.cohort_month,
          MONTH(DATE_TRUNC('month', o.order_ts)::CURRENT_DATE) - MONTH(c.cohort_month) + 12 * (YEAR(DATE_TRUNC('month', o.order_ts)::CURRENT_DATE) - YEAR(DATE_TRUNC('month', o.order_ts)::CURRENT_DATE));

INSERT INTO mart.cohort_retention
SELECT s.cohort_month,
       s.month_offset,
       sz.cohort_size,
       s.active_buyers
FROM   tmp_activity s
JOIN (SELECT cohort_month, COUNT(*) AS cohort_size
      FROM tmp_cohorts GROUP BY cohort_month) sz
  ON sz.cohort_month = s.cohort_month
ORDER  BY s.cohort_month, s.month_offset;

DROP TABLE IF EXISTS tmp_cohorts;
DROP TABLE IF EXISTS tmp_activity;

*/

 ---------------Exception End --------------------
