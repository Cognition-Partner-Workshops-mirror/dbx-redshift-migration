CREATE OR REPLACE TABLE demo_redshift.customer_360.order_facts
TBLPROPERTIES ('delta.feature.timestampNtz' = 'supported')
COMMENT 'One row per order. Gross is after line discounts across all statuses. Net includes completed orders.'
AS
WITH returns_by_item AS (
  SELECT order_item_id, SUM(quantity) AS returned_items
  FROM demo_redshift.silver.returns
  GROUP BY order_item_id
), baskets AS (
  SELECT i.order_id, SUM(i.quantity) AS items,
         SUM(i.quantity * (i.unit_price - i.discount)) AS amount,
         SUM(COALESCE(r.returned_items, 0)) AS returned_items
  FROM demo_redshift.silver.order_items i
  LEFT JOIN returns_by_item r USING (order_item_id)
  GROUP BY i.order_id
), shipments AS (
  SELECT order_id,
         MAX(CASE WHEN delivered_ts >= ship_ts
                  THEN TIMESTAMPDIFF(SECOND, ship_ts, delivered_ts) / 3600.0 END) AS hours_to_deliver
  FROM demo_redshift.silver.shipments
  GROUP BY order_id
)
SELECT o.order_id, o.customer_id, o.order_ts,
       CAST(o.order_ts AS DATE) AS order_date,
       TRUNC(CAST(o.order_ts AS DATE), 'MONTH') AS order_month,
       YEAR(ADD_MONTHS(CAST(o.order_ts AS DATE), -1)) AS fiscal_year,
       QUARTER(ADD_MONTHS(CAST(o.order_ts AS DATE), -1)) AS fiscal_quarter,
       o.sales_channel AS channel, o.store_id, s.store_name, TRIM(s.region) AS region, o.status,
       CAST(COALESCE(b.amount, 0) AS DECIMAL(18, 2)) AS gross_amount,
       CAST(CASE WHEN o.status = 'complete' THEN COALESCE(b.amount, 0) ELSE 0 END AS DECIMAL(18, 2)) AS net_amount,
       o.status = 'cancelled' AS is_cancelled, o.status = 'returned' AS is_returned,
       COALESCE(b.items, 0) AS items, COALESCE(b.returned_items, 0) AS returned_items,
       sh.hours_to_deliver, sh.hours_to_deliver <= 96 AS delivered_within_96h
FROM demo_redshift.silver.orders o
LEFT JOIN demo_redshift.silver.stores s USING (store_id)
LEFT JOIN baskets b USING (order_id)
LEFT JOIN shipments sh USING (order_id);

CREATE OR REPLACE TABLE demo_redshift.customer_360.customer_profile
COMMENT 'One row per customer with contact details and 2025 order history'
AS
WITH summary AS (
  SELECT customer_id, MIN(order_date) AS first_order_date, MAX(order_date) AS last_order_date,
         MAX(order_date) FILTER (WHERE status = 'complete') AS last_completed_order_date,
         COUNT_IF(status = 'complete') AS completed_orders, SUM(net_amount) AS net_ltv,
         SUM(gross_amount) AS gross_spend, SUM(returned_items) AS returned_items
  FROM demo_redshift.customer_360.order_facts
  GROUP BY customer_id
), category_spend AS (
  SELECT o.customer_id, p.category, SUM(i.quantity * (i.unit_price - i.discount)) AS spend
  FROM demo_redshift.customer_360.order_facts o
  JOIN demo_redshift.silver.order_items i USING (order_id)
  JOIN demo_redshift.silver.products p USING (product_id)
  WHERE o.status = 'complete'
  GROUP BY o.customer_id, p.category
), top_category AS (
  SELECT customer_id, category FROM category_spend
  QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY spend DESC, category) = 1
)
SELECT c.customer_id, c.first_name, c.last_name, c.email, c.phone,
       TRIM(c.region) AS region, c.is_business, c.signup_date,
       c.preferred_store_id, st.store_name AS preferred_store, s.first_order_date, s.last_order_date,
       s.last_completed_order_date, COALESCE(s.completed_orders, 0) AS completed_orders,
       COALESCE(s.net_ltv, 0) AS net_ltv, COALESCE(s.gross_spend, 0) AS gross_spend,
       CAST(TRY_DIVIDE(s.net_ltv, s.completed_orders) AS DECIMAL(18, 2)) AS aov,
       COALESCE(s.returned_items, 0) AS returned_items, t.category AS top_category
FROM demo_redshift.silver.customers c
LEFT JOIN demo_redshift.silver.stores st ON c.preferred_store_id = st.store_id
LEFT JOIN summary s ON c.customer_id = s.customer_id
LEFT JOIN top_category t ON c.customer_id = t.customer_id;

CREATE OR REPLACE TABLE demo_redshift.customer_360.customer_health
COMMENT 'One row per customer with completed-order RFM as of 2025-12-31'
AS
WITH scores AS (
  SELECT customer_id,
         NTILE(5) OVER (ORDER BY last_completed_order_date, customer_id) AS r_score,
         NTILE(5) OVER (ORDER BY completed_orders, customer_id) AS f_score,
         NTILE(5) OVER (ORDER BY net_ltv, customer_id) AS m_score
  FROM demo_redshift.customer_360.customer_profile
  WHERE completed_orders > 0
), segments AS (
  SELECT p.customer_id, p.region, p.is_business, p.completed_orders, p.net_ltv,
         DATEDIFF(DATE '2025-12-31', p.last_completed_order_date) AS recency_days,
         s.r_score, s.f_score, s.m_score,
         CASE
           WHEN p.completed_orders = 0 THEN 'Never ordered'
           WHEN s.r_score >= 4 AND s.f_score >= 4 THEN 'Champion'
           WHEN s.r_score <= 2 AND s.f_score >= 3 THEN 'At risk'
           WHEN s.f_score >= 3 THEN 'Loyal'
           WHEN s.r_score <= 2 THEN 'Hibernating'
           ELSE 'Promising'
         END AS segment
  FROM demo_redshift.customer_360.customer_profile p
  LEFT JOIN scores s USING (customer_id)
)
SELECT *, DATE '2025-12-31' AS as_of_date,
       CASE WHEN segment = 'At risk' THEN net_ltv ELSE 0 END AS revenue_at_risk
FROM segments;
