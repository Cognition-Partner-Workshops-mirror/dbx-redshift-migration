-- attribution: campaign reach by channel from campaign_touches JSON payloads.
-- Redshift SUPER + PartiQL unnesting (FROM t, t.payload.touches tc) becomes
-- from_json on the STRING payload + explode; explode drops rows whose touches
-- array is NULL or empty, matching PartiQL's inner unnest semantics.
CREATE OR REPLACE TABLE gold.attribution
COMMENT 'Campaign touches and distinct customers reached per campaign and channel'
AS
WITH touches AS (
  SELECT t.customer_id,
         explode(
           from_json(t.payload,
                     'STRUCT<touches: ARRAY<STRUCT<campaign_id: STRING, channel: STRING, ts: STRING>>>'
           ).touches
         ) AS tc
  FROM   silver.campaign_touches t
)
SELECT CAST(tc.campaign_id AS VARCHAR(16))  AS campaign_id,
       CAST(tc.channel AS VARCHAR(16))      AS touch_channel,
       COUNT(*)                             AS touches,
       COUNT(DISTINCT customer_id)          AS customers_reached
FROM   touches
GROUP  BY CAST(tc.campaign_id AS VARCHAR(16)), CAST(tc.channel AS VARCHAR(16));
