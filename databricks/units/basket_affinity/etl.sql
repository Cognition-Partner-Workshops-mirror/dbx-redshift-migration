-- basket_affinity: product pairs bought in the same order, support >= 5.
CREATE OR REPLACE TABLE gold.basket_affinity AS
SELECT a.product_id AS product_id_a,
       b.product_id AS product_id_b,
       COUNT(DISTINCT a.order_id) AS pair_orders
FROM   silver.order_items a
JOIN   silver.order_items b
       ON b.order_id = a.order_id AND b.product_id > a.product_id
GROUP  BY a.product_id, b.product_id
HAVING COUNT(DISTINCT a.order_id) >= 5;
