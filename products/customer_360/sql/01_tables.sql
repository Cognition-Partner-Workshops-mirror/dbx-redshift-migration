USE CATALOG IDENTIFIER(:catalog);

CREATE OR REPLACE TABLE customer_360.order_facts
COMMENT 'One row per order as of 2025-12-31. Gross is discounted line spend for all statuses; net recognizes complete orders only.'
AS
WITH lines AS (
  SELECT order_id, SUM(quantity * (unit_price - discount)) AS gross_amount,
         SUM(quantity) AS items
  FROM silver.order_items GROUP BY order_id
), delivery AS (
  SELECT order_id,
         CASE WHEN COUNT(*) = COUNT(delivered_ts) AND COUNT(*) = COUNT(ship_ts)
                   AND MIN(timestampdiff(SECOND, ship_ts, delivered_ts)) >= 0
              THEN MAX(timestampdiff(SECOND, ship_ts, delivered_ts)) / 3600.0 END
              AS hours_to_deliver
  FROM silver.shipments GROUP BY order_id
)
SELECT o.order_id, o.customer_id, o.order_ts, CAST(o.order_ts AS DATE) AS order_date,
       CAST(date_trunc('MONTH', o.order_ts) AS DATE) AS order_month,
       year(add_months(CAST(o.order_ts AS DATE), -1)) AS fiscal_year,
       concat('Q', quarter(add_months(CAST(o.order_ts AS DATE), -1))) AS fiscal_quarter,
       o.sales_channel, o.store_id, rtrim(c.region) AS region, o.status,
       COALESCE(l.gross_amount, 0) AS gross_amount,
       CASE WHEN o.status = 'complete' THEN COALESCE(l.gross_amount, 0) ELSE 0 END AS net_amount,
       o.status = 'cancelled' AS is_cancelled, o.status = 'returned' AS is_returned,
       COALESCE(l.items, 0) AS items,
       d.hours_to_deliver BETWEEN 0 AND 96 AS delivered_within_96h,
       CAST(d.hours_to_deliver AS DECIMAL(18,6)) AS hours_to_deliver
FROM silver.orders o
LEFT JOIN lines l USING (order_id)
LEFT JOIN delivery d USING (order_id)
LEFT JOIN silver.customers c USING (customer_id)
WHERE CAST(o.order_ts AS DATE) <= DATE'2025-12-31';

CREATE OR REPLACE TABLE customer_360.customer_profile
COMMENT 'One row per registered customer. AOV and net LTV use complete orders; customers without complete orders have NULL AOV and zero net LTV.'
AS
WITH spend AS (
  SELECT customer_id, MIN(order_date) AS first_order_date, MAX(order_date) AS last_order_date,
         MAX(order_date) FILTER (WHERE status = 'complete') AS last_completed_order_date,
         COUNT(*) AS all_orders, count_if(status = 'complete') AS completed_orders,
         SUM(net_amount) AS net_ltv, SUM(gross_amount) AS gross_spend,
         try_divide(SUM(net_amount), count_if(status = 'complete')) AS aov
  FROM customer_360.order_facts GROUP BY customer_id
), returned AS (
  SELECT o.customer_id, COUNT(DISTINCT r.return_id) AS return_count
  FROM silver.returns r JOIN silver.order_items i USING (order_item_id)
  JOIN customer_360.order_facts o USING (order_id)
  WHERE CAST(r.returned_ts AS DATE) <= DATE'2025-12-31'
  GROUP BY o.customer_id
), categories AS (
  SELECT o.customer_id, p.category,
         row_number() OVER (PARTITION BY o.customer_id
           ORDER BY SUM(i.quantity * (i.unit_price - i.discount)) DESC, p.category ASC) AS rn
  FROM customer_360.order_facts o JOIN silver.order_items i USING (order_id)
  JOIN silver.products p USING (product_id)
  WHERE o.status = 'complete'
  GROUP BY o.customer_id, p.category
)
SELECT c.customer_id, concat_ws(' ', c.first_name, c.last_name) AS name,
       c.email, c.phone, rtrim(c.region) AS region, c.is_business, c.signup_date,
       s.store_name AS preferred_store_name, s.city AS preferred_store_city,
       a.first_order_date, a.last_order_date, a.last_completed_order_date,
       COALESCE(a.all_orders, 0) AS all_orders,
       COALESCE(a.completed_orders, 0) AS completed_orders,
       COALESCE(a.net_ltv, 0) AS net_ltv, COALESCE(a.gross_spend, 0) AS gross_spend,
       a.aov, COALESCE(r.return_count, 0) AS return_count, cat.category AS top_category
FROM silver.customers c LEFT JOIN silver.stores s ON c.preferred_store_id = s.store_id
LEFT JOIN spend a USING (customer_id)
LEFT JOIN returned r USING (customer_id)
LEFT JOIN categories cat ON c.customer_id = cat.customer_id AND cat.rn = 1
WHERE c.signup_date <= DATE'2025-12-31';

CREATE OR REPLACE TABLE customer_360.customer_health
COMMENT 'Completed-order RFM at 2025-12-31. Precedence: Never ordered, Champion, At risk, Loyal, Hibernating, Promising. Never ordered means no completed orders; tiles NULL for these customers.'
AS
WITH ordering AS (
  SELECT customer_id, datediff(DATE'2025-12-31', last_completed_order_date) AS recency_days,
         completed_orders AS frequency, net_ltv AS monetary,
         ntile(5) OVER (ORDER BY last_completed_order_date ASC, customer_id) AS r_tile,
         ntile(5) OVER (ORDER BY completed_orders ASC, customer_id) AS f_tile,
         ntile(5) OVER (ORDER BY net_ltv ASC, customer_id) AS m_tile
  FROM customer_360.customer_profile WHERE completed_orders > 0
), segmented AS (
  SELECT p.customer_id, o.recency_days, COALESCE(o.frequency, 0) AS frequency,
         p.net_ltv AS monetary, o.r_tile, o.f_tile, o.m_tile,
         CASE WHEN p.completed_orders = 0 THEN 'Never ordered'
              WHEN o.r_tile >= 4 AND o.f_tile >= 4 THEN 'Champion'
              WHEN o.r_tile <= 2 AND o.f_tile >= 3 THEN 'At risk'
              WHEN o.f_tile >= 3 THEN 'Loyal'
              WHEN o.r_tile <= 2 THEN 'Hibernating'
              ELSE 'Promising' END AS health_segment
  FROM customer_360.customer_profile p LEFT JOIN ordering o USING (customer_id)
)
SELECT *, CASE WHEN health_segment = 'At risk' THEN monetary ELSE 0 END AS revenue_at_risk
FROM segmented;

CREATE OR REPLACE VIEW customer_360.legacy_vs_certified
COMMENT 'Legacy versus certified KPIs. Difference = certified minus legacy; rates are fractions. Q1 isolates the calendar correction at equal all-status scope.'
AS
WITH comparisons AS (
  SELECT 'total_revenue' AS kpi,
    (SELECT total_revenue FROM gold.exec_summary LIMIT 1) AS legacy_value,
    (SELECT SUM(net_amount) FROM customer_360.order_facts) AS certified_value,
    'Complete orders only; cancelled and returned orders recognize zero net revenue.' AS explanation
  UNION ALL
  SELECT 'aov', (SELECT AVG(aov) FROM gold.customer_ltv),
    (SELECT try_divide(SUM(net_amount), count_if(status = 'complete')) FROM customer_360.order_facts),
    'Legacy averages customer line-price averages; certified is net revenue divided by completed orders.'
  UNION ALL
  SELECT 'avg_customer_ltv', (SELECT avg_customer_ltv FROM gold.exec_summary LIMIT 1),
    (SELECT AVG(net_ltv) FROM customer_360.customer_profile WHERE completed_orders > 0),
    'Certified averages complete-order LTV over customers with completed orders, excluding never purchasers.'
  UNION ALL
  SELECT 'q1_revenue', (SELECT SUM(revenue) FROM gold.finance_monthly WHERE fiscal_qtr = 'Q1'),
    (SELECT SUM(gross_amount) FROM customer_360.order_facts WHERE fiscal_quarter = 'Q1'),
    'Calendar-only comparison on all-status gross: legacy Q1 Mar-May; certified Q1 Feb-Apr. Fiscal year is start year.'
  UNION ALL
  SELECT 'return_rate', (SELECT AVG(return_rate_int) FROM gold.returns_rate),
    (SELECT try_divide(
      (SELECT SUM(r.quantity) FROM silver.returns r
       JOIN silver.order_items i USING (order_item_id)
       JOIN customer_360.order_facts o USING (order_id)
       WHERE CAST(r.returned_ts AS DATE) <= DATE'2025-12-31'),
      (SELECT SUM(items) FROM customer_360.order_facts))),
    'Legacy integer division yields zero; certified returned units / sold units is fractional, across all order statuses.'
)
SELECT kpi, legacy_value, certified_value, certified_value - legacy_value AS difference, explanation
FROM comparisons;

ALTER TABLE customer_360.order_facts ALTER COLUMN order_id COMMENT 'Unique order identifier; table grain.';
ALTER TABLE customer_360.order_facts ALTER COLUMN customer_id COMMENT 'Customer identifier.';
ALTER TABLE customer_360.order_facts ALTER COLUMN order_ts COMMENT 'Source order timestamp used for chronological order history.';
ALTER TABLE customer_360.order_facts ALTER COLUMN order_date COMMENT 'Calendar order date.';
ALTER TABLE customer_360.order_facts ALTER COLUMN order_month COMMENT 'First day of order calendar month.';
ALTER TABLE customer_360.order_facts ALTER COLUMN fiscal_year COMMENT 'Fiscal start year; Feb 1 through Jan 31.';
ALTER TABLE customer_360.order_facts ALTER COLUMN fiscal_quarter COMMENT 'Q1 Feb-Apr; Q2 May-Jul; Q3 Aug-Oct; Q4 Nov-Jan.';
ALTER TABLE customer_360.order_facts ALTER COLUMN sales_channel COMMENT 'Source sales channel.';
ALTER TABLE customer_360.order_facts ALTER COLUMN store_id COMMENT 'Order store identifier.';
ALTER TABLE customer_360.order_facts ALTER COLUMN region COMMENT 'Customer region with trailing padding removed.';
ALTER TABLE customer_360.order_facts ALTER COLUMN status COMMENT 'Original complete, cancelled or returned order status.';
ALTER TABLE customer_360.order_facts ALTER COLUMN gross_amount COMMENT 'Sum of quantity times discounted unit price, all statuses.';
ALTER TABLE customer_360.order_facts ALTER COLUMN net_amount COMMENT 'Gross amount for complete orders; otherwise zero.';
ALTER TABLE customer_360.order_facts ALTER COLUMN is_cancelled COMMENT 'True when order status is cancelled.';
ALTER TABLE customer_360.order_facts ALTER COLUMN is_returned COMMENT 'True when order status is returned.';
ALTER TABLE customer_360.order_facts ALTER COLUMN items COMMENT 'Total ordered unit quantity.';
ALTER TABLE customer_360.order_facts ALTER COLUMN delivered_within_96h COMMENT 'All shipments delivered within 96 elapsed hours; NULL if incomplete or any shipment duration is negative.';
ALTER TABLE customer_360.order_facts ALTER COLUMN hours_to_deliver COMMENT 'Slowest shipment elapsed seconds / 3600; decimal hours, NULL if timestamps are missing or any shipment duration is negative.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN customer_id COMMENT 'Unique registered customer identifier; table grain.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN name COMMENT 'Customer first and last name.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN email COMMENT 'Source customer email address.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN phone COMMENT 'Source customer phone; may be NULL.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN region COMMENT 'Customer region with trailing padding removed.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN is_business COMMENT 'Business customer flag.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN signup_date COMMENT 'Customer registration date.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN preferred_store_name COMMENT 'Name of preferred store.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN preferred_store_city COMMENT 'City of preferred store.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN first_order_date COMMENT 'First order date, any status.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN last_order_date COMMENT 'Last order date, any status.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN last_completed_order_date COMMENT 'Last completed order date used for RFM.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN all_orders COMMENT 'Number of orders across all statuses.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN completed_orders COMMENT 'Number of complete orders.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN net_ltv COMMENT 'Lifetime recognized revenue, complete orders only; zero without purchases.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN gross_spend COMMENT 'Lifetime discounted line spend across all statuses.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN aov COMMENT 'Net LTV / completed orders; NULL if no completed orders.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN return_count COMMENT 'Distinct return records through 2025-12-31.';
ALTER TABLE customer_360.customer_profile ALTER COLUMN top_category COMMENT 'Category with highest completed-order spend; alphabetic tie break.';
ALTER TABLE customer_360.customer_health ALTER COLUMN customer_id COMMENT 'Unique customer identifier; table grain.';
ALTER TABLE customer_360.customer_health ALTER COLUMN recency_days COMMENT 'Days since last complete order as of 2025-12-31; NULL for never purchasers.';
ALTER TABLE customer_360.customer_health ALTER COLUMN frequency COMMENT 'Completed order count; zero without purchases.';
ALTER TABLE customer_360.customer_health ALTER COLUMN monetary COMMENT 'Complete-order net LTV.';
ALTER TABLE customer_360.customer_health ALTER COLUMN r_tile COMMENT 'Recency NTILE(5), 5 most recent; customer ID breaks ties.';
ALTER TABLE customer_360.customer_health ALTER COLUMN f_tile COMMENT 'Frequency NTILE(5), 5 most frequent; customer ID breaks ties.';
ALTER TABLE customer_360.customer_health ALTER COLUMN m_tile COMMENT 'Monetary NTILE(5), 5 highest; customer ID breaks ties.';
ALTER TABLE customer_360.customer_health ALTER COLUMN health_segment COMMENT 'Precedence: Never ordered, Champion, At risk, Loyal, Hibernating, Promising.';
ALTER TABLE customer_360.customer_health ALTER COLUMN revenue_at_risk COMMENT 'Net LTV for At risk customers only, zero otherwise.';
