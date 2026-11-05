-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'CREATE': extra input 'CREATE'. SQLSTATE: 42601 (line 4, pos 0)

== SQL ==
EXPLAIN -- inventory_snapshot: plpgsql upsert — staging temp table + DELETE/INSERT
-- into an existing mart table.
DROP TABLE IF EXISTS mart.inventory_snapshot;
CREATE OR REPLACE TABLE mart.inventory_snapshot (
^^^
    product_id    INT,
    snapshot_date DATE,
    units_sold    BIGINT,
    on_hand       INT
)

ZORDER BY(product_id)CREATE OR REPLACE PROCEDURE sp_upsert_inventory(
IN p_snapshot DATE)
LANGUAGE SQL
SQL SECURITY INVOKER
AS

$$

THEN

    
CREATE TEMP TABLE stg_inventory (
        product_id  INT,
        units_sold  BIGINT
    );

    INSERT INTO stg_inventory
    SELECT product_id, SUM(quantity)::BIGINT
    FROM   core.order_items
    GROUP  BY product_id;

    DELETE FROM mart.inventory_snapshot
    WHERE  product_id IN (SELECT product_id FROM stg_inventory);

    INSERT INTO mart.inventory_snapshot
    SELECT p.product_id,
           p_snapshot,
           COALESCE(s.units_sold, 0),
           GREATEST(500 - COALESCE(s.units_sold, 0), 0)::INT
    FROM   core.products p
    LEFT JOIN stg_inventory s ON s.product_id = p.product_id;

    DROP TABLE IF EXISTS stg_inventory;

END IF;

CALL sp_upsert_inventory('2025-12-31'::DATE);

*/

 ---------------Exception End --------------------
