USE CATALOG IDENTIFIER(:catalog);
USE SCHEMA customer_360;

CREATE OR REPLACE VIEW revenue_metrics
WITH METRICS LANGUAGE YAML AS $$
version: 1.1
source: order_facts
comment: Certified order revenue. Net recognizes complete orders only. All rates are fractions except on_time_delivery_pct.
dimensions:
  - name: order_month
    expr: order_month
    comment: Calendar month of order.
    synonyms: [sales month]
  - name: fiscal_year
    expr: fiscal_year
    comment: Fiscal start year, February 1 through January 31.
  - name: fiscal_quarter
    expr: fiscal_quarter
    comment: Q1 Feb-Apr, Q2 May-Jul, Q3 Aug-Oct, Q4 Nov-Jan.
  - name: sales_channel
    expr: sales_channel
    synonyms: [channel]
  - name: region
    expr: region
    comment: Customer region, trailing padding removed.
  - name: status
    expr: status
    comment: Order status, complete/cancelled/returned.
measures:
  - name: gross_revenue
    expr: SUM(gross_amount)
    comment: Discounted line spend across all statuses, not recognized revenue.
    synonyms: [gross spend]
  - name: net_revenue
    expr: SUM(net_amount)
    comment: Recognized revenue from complete orders only.
    synonyms: [certified revenue, net sales]
  - name: revenue_leakage
    expr: SUM(gross_amount) - SUM(net_amount)
    comment: Cancelled and returned order spend excluded from net revenue.
  - name: orders
    expr: COUNT(*)
    comment: All orders, including cancelled and returned.
  - name: completed_orders
    expr: COUNT_IF(status = 'complete')
  - name: aov
    expr: TRY_DIVIDE(SUM(net_amount), COUNT_IF(status = 'complete'))
    comment: Net revenue per completed order, NULL when none complete.
    synonyms: [average order value]
  - name: cancel_rate
    expr: TRY_DIVIDE(COUNT_IF(is_cancelled), COUNT(*))
    comment: Cancelled orders / all orders, fraction 0-1.
  - name: return_rate
    expr: TRY_DIVIDE(COUNT_IF(is_returned), COUNT(*))
    comment: Returned-status orders / all orders, fraction 0-1. Not the unit return rate in legacy_vs_certified.
  - name: on_time_delivery_pct
    expr: 100.0 * TRY_DIVIDE(COUNT_IF(delivered_within_96h), COUNT(hours_to_deliver))
    comment: Percent of valid delivered orders whose slowest shipment arrived within 96 decimal hours of shipping. Incomplete or negative shipment durations excluded.
$$;

CREATE OR REPLACE VIEW customer_health_metrics
WITH METRICS LANGUAGE YAML AS $$
version: 1.1
source: customer_health
comment: Completed-order RFM and customer value, as of 2025-12-31.
joins:
  - name: profile
    source: customer_profile
    on: source.customer_id = profile.customer_id
dimensions:
  - name: health_segment
    expr: source.health_segment
    comment: Never ordered, Champion, At risk, Loyal, Hibernating, Promising (in precedence order).
    synonyms: [customer segment]
  - name: region
    expr: profile.region
    comment: Customer region without trailing padding.
  - name: is_business
    expr: profile.is_business
    synonyms: [business customer]
  - name: signup_month
    expr: CAST(DATE_TRUNC('MONTH', profile.signup_date) AS DATE)
  - name: r_tile
    expr: source.r_tile
    comment: Recency quintile, 5 most recent, NULL without completed orders.
  - name: f_tile
    expr: source.f_tile
    comment: Completed-order frequency quintile, 5 most frequent.
  - name: m_tile
    expr: source.m_tile
    comment: Completed-order spend quintile, 5 highest.
measures:
  - name: customers
    expr: COUNT(*)
    synonyms: [customer count]
  - name: active_customers
    expr: COUNT_IF(source.frequency > 0 AND source.recency_days <= 90)
    comment: Customers completing an order in the last 90 days as of 2025-12-31.
  - name: repeat_rate
    expr: TRY_DIVIDE(COUNT_IF(source.frequency >= 2), COUNT_IF(source.frequency > 0))
    comment: Repeat purchasers / purchasers, NULL without purchasers. Fraction 0-1.
  - name: avg_net_ltv
    expr: AVG(profile.net_ltv) FILTER (WHERE source.frequency > 0)
    comment: Mean complete-order LTV among purchasers only. Excludes zero-order customers.
    synonyms: [average customer lifetime value]
  - name: total_net_ltv
    expr: SUM(profile.net_ltv)
    comment: Total recognized customer lifetime revenue.
  - name: revenue_at_risk
    expr: SUM(source.revenue_at_risk)
    comment: Net LTV of At risk customers only.
    synonyms: [at risk revenue]
$$;
