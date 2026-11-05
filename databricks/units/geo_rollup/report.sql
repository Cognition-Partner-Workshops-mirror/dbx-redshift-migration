SELECT grouping_id, region, state, order_count, revenue
FROM   gold.geo_rollup
ORDER BY grouping_id, region NULLS LAST, state NULLS LAST;
