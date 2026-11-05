-- product_perf: per-product sales with a comma list of the top 3 store regions.
CREATE OR REPLACE TABLE gold.product_perf
CLUSTER BY (product_id)
AS
WITH per_store AS (
    SELECT oi.product_id,
           s.region,
           SUM(oi.quantity) AS units
    FROM   silver.order_items oi
    JOIN   silver.orders o ON o.order_id = oi.order_id
    JOIN   silver.stores s ON s.store_id = o.store_id
    GROUP  BY oi.product_id, s.region
),
-- Redshift default NULL ordering: NULLs sort as the largest value.
ranked AS (
    SELECT product_id, region, units,
           ROW_NUMBER() OVER (PARTITION BY product_id
                              ORDER BY units DESC NULLS FIRST, region ASC NULLS LAST) AS rn
    FROM   per_store
),
top_stores AS (
    -- Redshift LISTAGG over CHAR drops trailing pad blanks; order by rank.
    SELECT product_id,
           CAST(array_join(
                  transform(array_sort(collect_list(struct(rn, rtrim(CAST(region AS STRING)) AS region))),
                            x -> x.region),
                  ',') AS STRING) AS codes
    FROM   ranked
    WHERE  rn <= 3
    GROUP  BY product_id
),
agg AS (
    SELECT product_id,
           CAST(SUM(quantity) AS BIGINT)                                  AS units_sold,
           CAST(SUM(quantity * (unit_price - discount)) AS DECIMAL(18,2)) AS revenue
    FROM   silver.order_items
    GROUP  BY product_id
)
SELECT p.product_id,
       p.category,
       COALESCE(a.units_sold, 0)                    AS units_sold,
       COALESCE(a.revenue, CAST(0 AS DECIMAL(18,2))) AS revenue,
       ts.codes                                     AS top_stores
FROM   silver.products p
LEFT JOIN agg        a  ON a.product_id = p.product_id
LEFT JOIN top_stores ts ON ts.product_id = p.product_id;
