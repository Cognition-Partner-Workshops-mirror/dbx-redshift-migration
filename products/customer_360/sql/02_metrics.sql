CREATE OR REPLACE VIEW demo_redshift.customer_360.revenue_metrics
WITH METRICS LANGUAGE YAML AS $$
version: 1.1
comment: Certified order revenue and fulfillment measures for the 2025 snapshot.
source: demo_redshift.customer_360.order_facts
dimensions:
  - name: order_month
    expr: order_month
  - name: fiscal_year
    expr: fiscal_year
  - name: fiscal_quarter
    expr: fiscal_quarter
    comment: Fiscal Q1 begins February 1.
  - name: channel
    expr: channel
  - name: region
    expr: region
    comment: Region of the store credited with the order.
  - name: customer_id
    expr: customer_id
measures:
  - name: gross_revenue
    expr: SUM(gross_amount)
    comment: Discounted basket value across all order statuses.
    synonyms: [gross sales, booked order value]
  - name: net_revenue
    expr: SUM(net_amount)
    comment: Discounted basket value for completed orders.
    synonyms: [revenue, net sales, certified revenue]
  - name: leakage
    expr: MEASURE(gross_revenue) - MEASURE(net_revenue)
    comment: Gross order value excluded by the completed-order rule.
    synonyms: [revenue leakage]
  - name: orders
    expr: COUNT(*)
    comment: Orders across all statuses.
    synonyms: [order count]
  - name: completed_orders
    expr: COUNT_IF(status = 'complete')
    comment: Orders with completed status.
    synonyms: [finished orders]
  - name: aov
    expr: TRY_DIVIDE(MEASURE(net_revenue), MEASURE(completed_orders))
    comment: Net revenue per completed order.
    synonyms: [average order value, average basket]
  - name: cancel_rate
    expr: TRY_DIVIDE(COUNT_IF(is_cancelled), MEASURE(orders))
    comment: Fraction of orders with cancelled status.
    synonyms: [cancellation rate]
  - name: return_rate
    expr: TRY_DIVIDE(SUM(returned_items), SUM(items))
    comment: Fraction of sold item units recorded as returned.
    synonyms: [item return rate, returns percentage]
  - name: on_time_delivery_pct
    expr: AVG(CAST(delivered_within_96h AS DOUBLE))
    comment: Fraction delivered within 96 hours among orders with valid durations.
    synonyms: [on-time delivery, shipping SLA]
$$;

CREATE OR REPLACE VIEW demo_redshift.customer_360.customer_health_metrics
WITH METRICS LANGUAGE YAML AS $$
version: 1.1
comment: Certified customer portfolio KPIs as of December 31 2025.
source: demo_redshift.customer_360.customer_health
dimensions:
  - name: customer_id
    expr: customer_id
  - name: region
    expr: region
    comment: Customer home region from the customer record.
  - name: segment
    expr: segment
    synonyms: [health segment, RFM segment]
  - name: is_business
    expr: is_business
  - name: as_of_date
    expr: as_of_date
measures:
  - name: customers
    expr: COUNT(*)
    comment: All customers in the snapshot.
    synonyms: [customer count, portfolio size]
  - name: active_customers
    expr: COUNT_IF(recency_days <= 90)
    comment: Customers with a completed order within 90 days of the snapshot.
    synonyms: [active, recent purchasers]
  - name: repeat_rate
    expr: TRY_DIVIDE(COUNT_IF(completed_orders >= 2), COUNT_IF(completed_orders > 0))
    comment: Fraction of purchasers with at least two completed orders.
    synonyms: [repeat purchase rate]
  - name: avg_net_ltv
    expr: AVG(net_ltv) FILTER (WHERE completed_orders > 0)
    comment: Average completed-order lifetime value among purchasers.
    synonyms: [average LTV, average lifetime value]
  - name: total_net_ltv
    expr: SUM(net_ltv)
    comment: Total completed-order lifetime value across customers.
    synonyms: [total LTV, lifetime value]
  - name: revenue_at_risk
    expr: SUM(revenue_at_risk)
    comment: Completed-order lifetime value of customers in the At risk segment.
    synonyms: [at-risk revenue, at-risk lifetime value]
$$;

CREATE OR REPLACE TABLE demo_redshift.customer_360.legacy_vs_certified
COMMENT 'Legacy gold calculations compared with the governed Customer 360 metrics'
AS
WITH legacy AS (
  SELECT e.total_revenue, e.avg_customer_ltv,
         (SELECT AVG(aov) FROM demo_redshift.gold.customer_ltv) AS aov,
         (SELECT SUM(revenue) FROM demo_redshift.gold.daily_revenue
          WHERE FLOOR(PMOD(MONTH(order_date) + 9, 12) / 3) + 1 = 1) AS q1,
         (SELECT MAX(return_rate_int) FROM demo_redshift.gold.returns_rate) AS return_rate
  FROM demo_redshift.gold.exec_summary e
  WHERE as_of_date = DATE '2025-12-31'
), revenue AS (
  SELECT MEASURE(net_revenue) AS total_revenue, MEASURE(aov) AS aov,
         MEASURE(return_rate) AS return_rate
  FROM demo_redshift.customer_360.revenue_metrics
), q1 AS (
  SELECT MEASURE(net_revenue) AS net_revenue
  FROM demo_redshift.customer_360.revenue_metrics
  WHERE fiscal_year = 2025 AND fiscal_quarter = 1
), health AS (
  SELECT MEASURE(avg_net_ltv) AS avg_ltv FROM demo_redshift.customer_360.customer_health_metrics
)
SELECT comparison.*
FROM legacy CROSS JOIN revenue CROSS JOIN q1 CROSS JOIN health
LATERAL VIEW INLINE(ARRAY(
  NAMED_STRUCT('display_order', 1, 'kpi', 'Total revenue',
    'legacy_value', CAST(legacy.total_revenue AS DECIMAL(20, 4)),
    'certified_value', CAST(revenue.total_revenue AS DECIMAL(20, 4)), 'unit', 'USD',
    'explanation', 'Legacy includes cancelled and returned baskets. Certified revenue counts completed orders.'),
  NAMED_STRUCT('display_order', 2, 'kpi', 'Average order value',
    'legacy_value', CAST(legacy.aov AS DECIMAL(20, 4)),
    'certified_value', CAST(revenue.aov AS DECIMAL(20, 4)), 'unit', 'USD',
    'explanation', 'Legacy averages unit prices. Certified AOV uses whole completed orders.'),
  NAMED_STRUCT('display_order', 3, 'kpi', 'Average customer LTV',
    'legacy_value', CAST(legacy.avg_customer_ltv AS DECIMAL(20, 4)),
    'certified_value', CAST(health.avg_ltv AS DECIMAL(20, 4)), 'unit', 'USD',
    'explanation', 'Legacy averages all spend across all customers. Certified averages net across purchasers.'),
  NAMED_STRUCT('display_order', 4, 'kpi', 'Fiscal Q1 revenue',
    'legacy_value', CAST(legacy.q1 AS DECIMAL(20, 4)),
    'certified_value', CAST(q1.net_revenue AS DECIMAL(20, 4)), 'unit', 'USD',
    'explanation', 'Legacy uses March–May and all orders. Certified uses February–April and completed orders.'),
  NAMED_STRUCT('display_order', 5, 'kpi', 'Returned item rate',
    'legacy_value', CAST(100 * legacy.return_rate AS DECIMAL(20, 4)),
    'certified_value', CAST(100 * revenue.return_rate AS DECIMAL(20, 4)), 'unit', '%',
    'explanation', 'The legacy integer rate truncates fractions. Certified rate divides returned units by sold units.')
)) comparison;
