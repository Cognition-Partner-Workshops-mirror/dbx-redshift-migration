-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'CREATE': extra input 'CREATE'. SQLSTATE: 42601 (line 3, pos 0)

== SQL ==
EXPLAIN -- basket_affinity: product pairs bought in the same order, support >= 5.
DROP TABLE IF EXISTS mart.basket_affinity;
CREATE OR REPLACE TABLE mart.basket_affinity AS
^^^
SELECT a.product_id AS product_id_a,
       b.product_id AS product_id_b,
       COUNT(DISTINCT a.order_id) AS pair_orders
FROM   core.order_items a
JOIN   core.order_items b
       ON b.order_id = a.order_id AND b.product_id > a.product_id
GROUP  BY a.product_id, b.product_id
HAVING COUNT(DISTINCT a.order_id) >= 5
ORDER  BY product_id_a, product_id_b;

*/

 ---------------Exception End --------------------
