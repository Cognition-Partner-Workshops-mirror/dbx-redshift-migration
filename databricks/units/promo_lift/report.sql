-- BI report: channel order-value distribution as published.
SELECT sales_channel, order_count, median_order_value, p90_order_value
FROM   gold.promo_lift
ORDER  BY sales_channel;
