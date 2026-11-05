-- shipping_sla: carrier SLA. Redshift DATEDIFF(hour) counts hour boundaries
-- crossed (floor(epoch/3600) difference), AVG over BIGINT truncates to an
-- integer before the NUMERIC(10,2) cast, and CONVERT_TIMEZONE gives the
-- local delivery hour.
CREATE OR REPLACE TABLE gold.shipping_sla AS
WITH s AS (
  SELECT carrier,
         delivered_ts,
         div(timestampdiff(SECOND, TIMESTAMP_NTZ'1970-01-01 00:00:00', delivered_ts), 3600)
           - div(timestampdiff(SECOND, TIMESTAMP_NTZ'1970-01-01 00:00:00', ship_ts), 3600) AS hours_to_deliver
  FROM   silver.shipments
)
SELECT carrier,
       COUNT(*)                                             AS shipments,
       COUNT(delivered_ts)                                  AS delivered,
       COUNT(*) - COUNT(delivered_ts)                       AS in_flight,
       CAST(CAST(AVG(hours_to_deliver) AS BIGINT) AS DECIMAL(10,2)) AS avg_hours_to_deliver,
       MAX(hours_to_deliver)                                AS max_hours_to_deliver,
       SUM(CASE WHEN hours_to_deliver <= 96 THEN 1 ELSE 0 END) AS on_time_96h,
       CAST(MIN(hour(convert_timezone('UTC', 'America/Los_Angeles', delivered_ts))) AS INT)
                                                            AS earliest_local_delivery_hour
FROM   s
GROUP  BY carrier;
