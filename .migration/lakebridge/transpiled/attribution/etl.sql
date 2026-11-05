-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'CREATE': extra input 'CREATE'. SQLSTATE: 42601 (line 3, pos 0)

== SQL ==
EXPLAIN -- attribution: SUPER/PartiQL navigation over campaign_touches payloads.
DROP TABLE IF EXISTS mart.attribution;
CREATE OR REPLACE TABLE mart.attribution AS
^^^
SELECT tc.campaign_id:: STRING          AS campaign_id,
       tc.channel:: STRING              AS touch_channel,
       COUNT(*)                             AS touches,
       COUNT(DISTINCT t.customer_id)        AS customers_reached
FROM   core.campaign_touches t, t.payload.touches tc
GROUP  BY tc.campaign_id:: STRING, tc.channel:: STRING
ORDER  BY campaign_id, touch_channel;

*/

 ---------------Exception End --------------------
