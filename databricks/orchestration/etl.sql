CREATE OR REPLACE TABLE gold.exec_summary AS
SELECT CAST('as_of_2025-12-31' AS STRING) AS snapshot_label,
       DATE '2025-12-31' AS as_of_date,
       dr.total_revenue,
       dr.total_orders,
       ltv.avg_ltv AS avg_customer_ltv,
       rr.return_pct AS overall_return_pct,
       sla.avg_hours_to_deliver AS avg_ship_hours
FROM (SELECT SUM(revenue) AS total_revenue, SUM(order_count) AS total_orders
      FROM gold.daily_revenue) dr
CROSS JOIN (SELECT CAST((SUM(ltv) * 100 DIV COUNT(ltv)) / 100 AS DECIMAL(38,2)) AS avg_ltv
            FROM gold.customer_ltv) ltv
CROSS JOIN (SELECT CAST(floor(CAST(SUM(returned_qty) AS DECIMAL(14,4))
                              / CAST(SUM(sold_qty) AS DECIMAL(14,4)), 15) * 100
                        AS DECIMAL(38,15)) AS return_pct
            FROM gold.returns_rate) rr
CROSS JOIN (SELECT CAST(floor(SUM(avg_hours_to_deliver * delivered) / SUM(delivered), 4)
                        AS DECIMAL(38,4)) AS avg_hours_to_deliver
            FROM gold.shipping_sla) sla;
