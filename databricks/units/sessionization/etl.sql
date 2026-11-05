-- sessionization: web sessions per customer, 30-minute gap, running SUM id.
-- DATEDIFF(second, a, b) counts second boundaries: difference of epoch seconds.
CREATE OR REPLACE TABLE gold.web_sessions
CLUSTER BY (customer_id, session_id)
AS
WITH flagged AS (
    SELECT customer_id,
           event_id,
           event_ts,
           event_type,
           CASE
             WHEN LAG(event_ts) OVER (PARTITION BY customer_id
                                      ORDER BY event_ts, event_id) IS NULL THEN 1
             WHEN unix_timestamp(event_ts)
                  - unix_timestamp(LAG(event_ts) OVER (PARTITION BY customer_id
                                                       ORDER BY event_ts, event_id)) > 1800 THEN 1
             ELSE 0
           END AS new_session
    FROM   silver.web_events
    WHERE  customer_id IS NOT NULL
),
numbered AS (
    SELECT customer_id,
           event_id,
           event_ts,
           event_type,
           CAST(SUM(new_session) OVER (PARTITION BY customer_id
                                       ORDER BY event_ts, event_id
                                       ROWS UNBOUNDED PRECEDING) AS BIGINT) AS session_id
    FROM   flagged
)
SELECT customer_id,
       session_id,
       MIN(event_ts)                                                       AS session_start_ts,
       MAX(event_ts)                                                       AS session_end_ts,
       CAST(COUNT(*) AS BIGINT)                                            AS event_count,
       CAST(SUM(CASE WHEN event_type = 'checkout' THEN 1 ELSE 0 END) AS BIGINT) AS checkout_events
FROM   numbered
GROUP  BY customer_id, session_id;
