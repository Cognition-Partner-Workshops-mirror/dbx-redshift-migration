-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'CREATE': extra input 'CREATE'. SQLSTATE: 42601 (line 4, pos 0)

== SQL ==
EXPLAIN -- shipping_sla: carrier SLA using DATEDIFF(hour) (Redshift counts hour
-- boundaries) and CONVERT_TIMEZONE for the local delivery hour.
DROP TABLE IF EXISTS mart.shipping_sla;
CREATE OR REPLACE TABLE mart.shipping_sla AS
^^^
SELECT s.carrier,
       COUNT(*)                                                        AS shipments,
       COUNT(s.delivered_ts)                                           AS delivered,
       COUNT(*) - COUNT(s.delivered_ts)                                AS in_flight,
       AVG((UNIX_TIMESTAMP(s.delivered_ts) - UNIX_TIMESTAMP(s.ship_ts)) / 3600):: DECIMAL(10,2)   AS avg_hours_to_deliver,
       MAX((UNIX_TIMESTAMP(s.delivered_ts) - UNIX_TIMESTAMP(s.ship_ts)) / 3600)                  AS max_hours_to_deliver,
       SUM(CASE WHEN (UNIX_TIMESTAMP(s.delivered_ts) - UNIX_TIMESTAMP(s.ship_ts)) / 3600 <= 96
                THEN 1 ELSE 0 END)                                    AS on_time_96h,
       MIN(EXTRACT(HOUR FROM FROM_UTC_TIMESTAMP( TO_UTC_TIMESTAMP(s.delivered_ts,'UTC'), 'America/Los_Angeles')))::INT    AS earliest_local_delivery_hour
FROM   core.shipments s
GROUP  BY s.carrier
ORDER  BY s.carrier;

*/

 ---------------Exception End --------------------
