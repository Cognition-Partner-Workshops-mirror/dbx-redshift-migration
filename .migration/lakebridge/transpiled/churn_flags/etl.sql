-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'CREATE': extra input 'CREATE'. SQLSTATE: 42601 (line 4, pos 0)

== SQL ==
EXPLAIN -- churn_flags: plpgsql procedure with a FOR loop over customers and a temp
-- table, then CALL. Flags are computed as of the fixed literal '2025-12-31'.
DROP TABLE IF EXISTS mart.churn_flags;
CREATE OR REPLACE TABLE mart.churn_flags (
^^^
    customer_id      BIGINT,
    last_order_date  DATE,
    days_since_order INT,
    churn_flag STRING
)

ZORDER BY(customer_id)CREATE OR REPLACE PROCEDURE sp_build_churn_flags(
)
LANGUAGE SQL
SQL SECURITY INVOKER
AS

$$

DECLARE
    rec RECORD;
THEN

    
CREATE TEMP TABLE tmp_last_orders (
        customer_id     BIGINT,
        last_order_date DATE
    );

    INSERT INTO tmp_last_orders
    SELECT c.customer_id,
           MAX(o.order_ts)::DATE
    FROM   core.customers c
    LEFT JOIN core.orders o ON o.customer_id = c.customer_id
    GROUP  BY c.customer_id;
 for_loop_2:  for_loop_1: 
    FOR rec IN
        SELECT customer_id, last_order_date FROM tmp_last_orders ORDER BY customer_id
     DO
        INSERT INTO mart.churn_flags
        VALUES (
            rec.customer_id,
            rec.last_order_date,
            CASE WHEN rec.last_order_date IS NULL
                 THEN NULL
                 ELSE '2025-12-31'::DATE - rec.last_order_date END,
            CASE
                WHEN rec.last_order_date IS NULL                        THEN 'never_ordered'
                WHEN '2025-12-31'::DATE - rec.last_order_date > 180     THEN 'churned'
                WHEN '2025-12-31'::DATE - rec.last_order_date > 90      THEN 'at_risk'
                ELSE 'active'
            END
        );

END IF  DO


    DROP TABLE IF EXISTS tmp_last_orders;
END;

CALL sp_build_churn_flags();

*/

 ---------------Exception End --------------------
