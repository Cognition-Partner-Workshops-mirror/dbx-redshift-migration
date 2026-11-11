-- Certified Customer 360 tables. Deterministic: "as of" is DATE'2025-12-31'.
-- Fiscal year starts Feb 1 (Feb-Apr = Q1), which the legacy f_fiscal_qtr got wrong.

CREATE OR REPLACE TABLE demo_redshift.customer_360.order_facts
COMMENT 'One row per order. net_amount counts completed orders only. Fiscal year starts Feb 1.'
TBLPROPERTIES ('delta.feature.timestampNtz' = 'supported')
AS
WITH items AS (
  SELECT order_id,
         SUM(quantity * (unit_price - discount)) AS gross_amount,
         SUM(quantity)                           AS items
  FROM demo_redshift.silver.order_items
  GROUP BY order_id
),
returned AS (
  SELECT oi.order_id, SUM(r.quantity) AS returned_units
  FROM demo_redshift.silver.returns r
  JOIN demo_redshift.silver.order_items oi ON oi.order_item_id = r.order_item_id
  GROUP BY oi.order_id
),
ship AS (
  SELECT order_id,
         CASE WHEN ship_ts IS NOT NULL AND delivered_ts IS NOT NULL AND delivered_ts >= ship_ts
              THEN CAST(timestampdiff(SECOND, ship_ts, delivered_ts) / 3600.0 AS DECIMAL(10,2)) END AS hours_to_deliver
  FROM demo_redshift.silver.shipments
)
SELECT o.order_id,
       o.customer_id,
       o.order_ts,
       CAST(o.order_ts AS DATE)                                        AS order_date,
       CAST(date_trunc('MONTH', o.order_ts) AS DATE)                   AS order_month,
       year(add_months(CAST(o.order_ts AS DATE), -1))                  AS fiscal_year,
       concat('Q', quarter(add_months(CAST(o.order_ts AS DATE), -1)))  AS fiscal_quarter,
       o.sales_channel                                                 AS channel,
       o.store_id,
       s.store_name                                                    AS store,
       rtrim(s.region)                                                 AS region,
       o.status,
       CAST(COALESCE(i.gross_amount, 0) AS DECIMAL(14,2))              AS gross_amount,
       CAST(CASE WHEN o.status = 'complete' THEN COALESCE(i.gross_amount, 0) ELSE 0 END AS DECIMAL(14,2)) AS net_amount,
       o.status = 'complete'                                           AS is_completed,
       o.status = 'cancelled'                                          AS is_cancelled,
       o.status = 'returned'                                           AS is_returned,
       CAST(COALESCE(i.items, 0) AS BIGINT)                            AS items,
       CAST(COALESCE(r.returned_units, 0) AS BIGINT)                   AS returned_units,
       sh.hours_to_deliver,
       CASE WHEN sh.hours_to_deliver IS NOT NULL THEN sh.hours_to_deliver <= 96 END AS delivered_within_96h
FROM demo_redshift.silver.orders o
LEFT JOIN items    i  ON i.order_id  = o.order_id
LEFT JOIN returned r  ON r.order_id  = o.order_id
LEFT JOIN ship     sh ON sh.order_id = o.order_id
LEFT JOIN demo_redshift.silver.stores s ON s.store_id = o.store_id;

CREATE OR REPLACE TABLE demo_redshift.customer_360.customer_profile
COMMENT 'One row per customer. LTV and AOV are net: completed orders only.'
AS
WITH completed AS (
  SELECT customer_id,
         COUNT(*)          AS completed_orders,
         SUM(net_amount)   AS net_ltv
  FROM demo_redshift.customer_360.order_facts
  WHERE is_completed
  GROUP BY customer_id
),
all_orders AS (
  SELECT customer_id,
         MIN(order_date)     AS first_order_date,
         MAX(order_date)     AS last_order_date,
         COUNT(*)            AS total_orders,
         SUM(gross_amount)   AS gross_spend,
         COUNT_IF(is_returned) AS returned_orders
  FROM demo_redshift.customer_360.order_facts
  GROUP BY customer_id
),
category_spend AS (
  SELECT o.customer_id, p.category,
         SUM(oi.quantity * (oi.unit_price - oi.discount)) AS spend
  FROM demo_redshift.silver.orders o
  JOIN demo_redshift.silver.order_items oi ON oi.order_id = o.order_id
  JOIN demo_redshift.silver.products p     ON p.product_id = oi.product_id
  WHERE o.status = 'complete'
  GROUP BY o.customer_id, p.category
),
top_category AS (
  SELECT customer_id, category AS top_category
  FROM (SELECT customer_id, category,
               ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY spend DESC, category) AS rn
        FROM category_spend)
  WHERE rn = 1
)
SELECT c.customer_id,
       concat_ws(' ', c.first_name, c.last_name)              AS customer_name,
       c.first_name,
       c.last_name,
       c.email,
       c.phone,
       rtrim(c.region)                                         AS region,
       c.is_business,
       c.signup_date,
       c.preferred_store_id,
       st.store_name                                           AS preferred_store,
       a.first_order_date,
       a.last_order_date,
       CAST(COALESCE(a.total_orders, 0) AS BIGINT)             AS total_orders,
       CAST(COALESCE(k.completed_orders, 0) AS BIGINT)         AS completed_orders,
       CAST(COALESCE(k.net_ltv, 0) AS DECIMAL(14,2))           AS net_ltv,
       CAST(COALESCE(a.gross_spend, 0) AS DECIMAL(14,2))       AS gross_spend,
       CAST(k.net_ltv / k.completed_orders AS DECIMAL(14,2))   AS aov,
       CAST(COALESCE(a.returned_orders, 0) AS BIGINT)          AS returned_orders,
       t.top_category
FROM demo_redshift.silver.customers c
LEFT JOIN all_orders   a  ON a.customer_id = c.customer_id
LEFT JOIN completed    k  ON k.customer_id = c.customer_id
LEFT JOIN top_category t  ON t.customer_id = c.customer_id
LEFT JOIN demo_redshift.silver.stores st ON st.store_id = c.preferred_store_id;

CREATE OR REPLACE TABLE demo_redshift.customer_360.customer_health
COMMENT 'One row per customer: RFM on completed orders as of 2025-12-31 and a health segment. Precedence: Never ordered, Champion, At risk, Loyal, Hibernating, Promising. revenue_at_risk is net LTV of At risk customers.'
AS
WITH rfm AS (
  SELECT customer_id,
         datediff(DATE'2025-12-31', MAX(order_date)) AS recency_days,
         COUNT(*)                                    AS frequency,
         SUM(net_amount)                             AS monetary,
         MAX(order_date)                             AS last_completed_order_date
  FROM demo_redshift.customer_360.order_facts
  WHERE is_completed
  GROUP BY customer_id
),
scored AS (
  SELECT *,
         NTILE(5) OVER (ORDER BY recency_days DESC, customer_id) AS r_score,
         NTILE(5) OVER (ORDER BY frequency, customer_id)         AS f_score,
         NTILE(5) OVER (ORDER BY monetary, customer_id)          AS m_score
  FROM rfm
),
segmented AS (
SELECT p.customer_id,
       p.customer_name,
       p.email,
       p.region,
       p.is_business,
       DATE'2025-12-31'                                   AS as_of_date,
       s.last_completed_order_date,
       s.recency_days,
       CAST(COALESCE(s.frequency, 0) AS BIGINT)           AS frequency,
       CAST(COALESCE(s.monetary, 0) AS DECIMAL(14,2))     AS monetary,
       s.r_score,
       s.f_score,
       s.m_score,
       p.net_ltv,
       p.aov,
       CASE WHEN s.customer_id IS NULL                 THEN 'Never ordered'
            WHEN s.r_score >= 4 AND s.f_score >= 4     THEN 'Champion'
            WHEN s.r_score <= 2 AND s.f_score >= 3     THEN 'At risk'
            WHEN s.f_score >= 3                        THEN 'Loyal'
            WHEN s.r_score <= 2                        THEN 'Hibernating'
            ELSE 'Promising' END                       AS segment,
       s.customer_id IS NOT NULL                       AS is_purchaser,
       COALESCE(s.frequency, 0) >= 2                   AS is_repeat,
       COALESCE(s.recency_days <= 90, FALSE)           AS is_active
FROM demo_redshift.customer_360.customer_profile p
LEFT JOIN scored s ON s.customer_id = p.customer_id
)
SELECT *,
       CAST(CASE WHEN segment = 'At risk' THEN net_ltv ELSE 0 END AS DECIMAL(14,2)) AS revenue_at_risk
FROM segmented;

CREATE OR REPLACE TABLE demo_redshift.customer_360.legacy_vs_certified
COMMENT 'Legacy Redshift-faithful KPIs (demo_redshift.gold) next to the certified customer_360 definitions, with the reason they differ.'
AS
SELECT 1 AS sort_order, 'Total revenue' AS kpi, 'USD' AS unit,
       (SELECT CAST(SUM(revenue) AS DECIMAL(14,4)) FROM demo_redshift.gold.daily_revenue) AS legacy_value,
       (SELECT CAST(SUM(net_amount) AS DECIMAL(14,4)) FROM demo_redshift.customer_360.order_facts) AS certified_value,
       'Legacy daily_revenue has no status filter, so cancelled and returned orders count as revenue. Certified net revenue counts completed orders only.' AS explanation
UNION ALL
SELECT 2 AS sort_order, 'Average order value' AS kpi, 'USD' AS unit,
       (SELECT CAST(AVG(aov) AS DECIMAL(14,4)) FROM demo_redshift.gold.customer_ltv) AS legacy_value,
       (SELECT CAST(SUM(net_amount) / COUNT_IF(is_completed) AS DECIMAL(14,4)) FROM demo_redshift.customer_360.order_facts) AS certified_value,
       'Legacy customer_ltv.aov averages line-item net price, not order totals. Certified AOV is net revenue per completed order.' AS explanation
UNION ALL
SELECT 3 AS sort_order, 'Average customer LTV' AS kpi, 'USD' AS unit,
       (SELECT CAST(AVG(ltv) AS DECIMAL(14,4)) FROM demo_redshift.gold.customer_ltv) AS legacy_value,
       (SELECT CAST(AVG(net_ltv) AS DECIMAL(14,4)) FROM demo_redshift.customer_360.customer_profile WHERE completed_orders > 0) AS certified_value,
       'Legacy LTV includes cancelled and returned orders and averages in never-ordered customers at 0. Certified LTV is net and averaged over purchasers.' AS explanation
UNION ALL
SELECT 4 AS sort_order, 'Fiscal Q1 revenue' AS kpi, 'USD' AS unit,
       (SELECT CAST(SUM(revenue) AS DECIMAL(14,4)) FROM demo_redshift.gold.finance_monthly WHERE fiscal_qtr = 'Q1') AS legacy_value,
       (SELECT CAST(SUM(net_amount) AS DECIMAL(14,4)) FROM demo_redshift.customer_360.order_facts WHERE fiscal_year = 2025 AND fiscal_quarter = 'Q1') AS certified_value,
       'Legacy f_fiscal_qtr maps Mar-May to Q1 although the fiscal year starts Feb 1, and counts all statuses. Certified Q1 is Feb-Apr net revenue.' AS explanation
UNION ALL
SELECT 5 AS sort_order, 'Return rate' AS kpi, 'ratio' AS unit,
       (SELECT CAST(SUM(return_rate_int) AS DECIMAL(14,4)) FROM demo_redshift.gold.returns_rate) AS legacy_value,
       (SELECT CAST(SUM(returned_units) / SUM(items) AS DECIMAL(14,4)) FROM demo_redshift.customer_360.order_facts) AS certified_value,
       'Legacy return_rate_int uses integer division, so it is always 0. Certified return rate is returned units over sold units.' AS explanation;
