-- Certified KPI definitions. These two metric views are the single source of truth
-- for the dashboard, the Genie space and the Customer Lookup app.
-- Keep semicolons out of the YAML: SQL-file job tasks split statements on them.

CREATE OR REPLACE VIEW demo_redshift.customer_360.revenue_metrics
WITH METRICS
LANGUAGE YAML
COMMENT 'Certified revenue KPIs over order_facts. Net revenue counts completed orders only. Fiscal year starts Feb 1.'
AS $$
version: 1.1
comment: Certified revenue KPIs, one row per order in the source. Net means completed orders only. Data as of 2025-12-31.
source: demo_redshift.customer_360.order_facts
dimensions:
  - name: order_date
    expr: order_date
    comment: Calendar date the order was placed
    synonyms: [date, day]
  - name: order_month
    expr: order_month
    comment: First day of the calendar month of the order
    synonyms: [month]
  - name: fiscal_year
    expr: fiscal_year
    comment: Fiscal year, starting Feb 1
    synonyms: [FY]
  - name: fiscal_quarter
    expr: fiscal_quarter
    comment: Fiscal quarter, Q1 = Feb to Apr
    synonyms: [quarter, FQ]
  - name: channel
    expr: channel
    comment: Sales channel
    synonyms: [sales channel]
  - name: region
    expr: region
    comment: Store region code
    synonyms: [territory, area]
  - name: store
    expr: store
    comment: Store name
    synonyms: [shop, location]
  - name: status
    expr: status
    comment: Order status (complete, cancelled, returned)
    synonyms: [order status]
  - name: customer_id
    expr: customer_id
    comment: Customer identifier
measures:
  - name: gross_revenue
    expr: SUM(gross_amount)
    comment: Order value across all statuses, including cancelled and returned. This is what legacy reported as revenue.
    synonyms: [gross sales, booked revenue]
    format:
      type: currency
      currency_code: USD
  - name: net_revenue
    expr: SUM(net_amount)
    comment: Certified revenue. Order value of completed orders only.
    synonyms: [revenue, sales, net sales]
    format:
      type: currency
      currency_code: USD
  - name: revenue_leakage
    expr: SUM(gross_amount) - SUM(net_amount)
    comment: Gross minus net revenue, the value lost to cancellations and returns
    synonyms: [leakage, lost revenue]
    format:
      type: currency
      currency_code: USD
  - name: orders
    expr: COUNT(1)
    comment: Number of orders in any status
    synonyms: [order count, total orders]
  - name: completed_orders
    expr: COUNT_IF(is_completed)
    comment: Number of completed orders
    synonyms: [completed order count]
  - name: aov
    expr: TRY_DIVIDE(SUM(net_amount), COUNT_IF(is_completed))
    comment: Average order value, net revenue per completed order
    synonyms: [average order value, basket size]
    format:
      type: currency
      currency_code: USD
  - name: cancel_rate
    expr: TRY_DIVIDE(COUNT_IF(is_cancelled), COUNT(1))
    comment: Share of orders cancelled
    synonyms: [cancellation rate]
    format:
      type: percentage
  - name: return_rate
    expr: TRY_DIVIDE(SUM(returned_units), SUM(items))
    comment: Returned units over sold units
    synonyms: [returns rate]
    format:
      type: percentage
  - name: on_time_delivery_pct
    expr: TRY_DIVIDE(COUNT_IF(delivered_within_96h), COUNT(delivered_within_96h))
    comment: Share of delivered shipments delivered within 96 hours of shipping
    synonyms: [on time rate, SLA, delivery SLA]
    format:
      type: percentage
$$;

CREATE OR REPLACE VIEW demo_redshift.customer_360.customer_health_metrics
WITH METRICS
LANGUAGE YAML
COMMENT 'Certified customer health KPIs over customer_health. LTV is net (completed orders). As of 2025-12-31.'
AS $$
version: 1.1
comment: Certified customer health KPIs, one row per customer in the source. As of 2025-12-31.
source: demo_redshift.customer_360.customer_health
dimensions:
  - name: segment
    expr: segment
    comment: Health segment. Never ordered, Champion, At risk, Loyal, Hibernating or Promising.
    synonyms: [health segment, customer segment, RFM segment]
  - name: region
    expr: region
    comment: Customer home region code
    synonyms: [territory, area]
  - name: is_business
    expr: is_business
    comment: True for business (B2B) customers
    synonyms: [business customer, B2B]
  - name: customer_id
    expr: customer_id
    comment: Customer identifier
  - name: customer_name
    expr: customer_name
    comment: Customer full name
    synonyms: [name, customer]
measures:
  - name: customers
    expr: COUNT(1)
    comment: Number of customers
    synonyms: [customer count, accounts]
  - name: active_customers
    expr: COUNT_IF(is_active)
    comment: Customers with a completed order in the last 90 days before 2025-12-31
    synonyms: [active accounts]
  - name: repeat_rate
    expr: TRY_DIVIDE(COUNT_IF(is_repeat), COUNT_IF(is_purchaser))
    comment: Share of purchasers with two or more completed orders
    synonyms: [repeat purchase rate]
    format:
      type: percentage
  - name: avg_net_ltv
    expr: AVG(CASE WHEN is_purchaser THEN net_ltv END)
    comment: Average net lifetime value over purchasers
    synonyms: [average LTV, average lifetime value]
    format:
      type: currency
      currency_code: USD
  - name: total_net_ltv
    expr: SUM(net_ltv)
    comment: Total net lifetime value
    synonyms: [total LTV, lifetime value]
    format:
      type: currency
      currency_code: USD
  - name: revenue_at_risk
    expr: SUM(revenue_at_risk)
    comment: Net LTV of At risk customers
    synonyms: [at risk revenue, churn exposure]
    format:
      type: currency
      currency_code: USD
$$;
