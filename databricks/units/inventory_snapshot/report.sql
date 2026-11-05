-- BI report: low stock as of the snapshot.
-- Redshift sorts NULLs high (ASC = NULLS LAST); made explicit for Databricks.
SELECT product_id, snapshot_date, units_sold, on_hand
FROM   gold.inventory_snapshot
ORDER  BY on_hand ASC NULLS LAST, product_id ASC NULLS LAST
LIMIT  50;
