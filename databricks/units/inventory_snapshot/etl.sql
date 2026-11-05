-- inventory_snapshot: Redshift plpgsql upsert (staging temp table + DELETE/INSERT)
-- rewritten as a Delta MERGE keyed on product_id. The snapshot date stays a
-- reusable parameter (p_snapshot), bound to the as-of literal 2025-12-31.
CREATE OR REPLACE TABLE gold.inventory_snapshot (
    product_id    INT,
    snapshot_date DATE,
    units_sold    BIGINT,
    on_hand       INT
)
CLUSTER BY (product_id);

BEGIN
    DECLARE p_snapshot DATE DEFAULT DATE'2025-12-31';

    MERGE INTO gold.inventory_snapshot AS t
    USING (
        WITH stg_inventory AS (
            SELECT product_id, CAST(SUM(quantity) AS BIGINT) AS units_sold
            FROM   silver.order_items
            GROUP  BY product_id
        )
        SELECT p.product_id,
               p_snapshot                                             AS snapshot_date,
               COALESCE(s.units_sold, 0)                              AS units_sold,
               CAST(GREATEST(500 - COALESCE(s.units_sold, 0), 0) AS INT) AS on_hand
        FROM   silver.products p
        LEFT JOIN stg_inventory s ON s.product_id = p.product_id
    ) AS src
    ON t.product_id = src.product_id
    WHEN MATCHED THEN UPDATE SET
        snapshot_date = src.snapshot_date,
        units_sold    = src.units_sold,
        on_hand       = src.on_hand
    WHEN NOT MATCHED THEN INSERT (product_id, snapshot_date, units_sold, on_hand)
        VALUES (src.product_id, src.snapshot_date, src.units_sold, src.on_hand);
END;
