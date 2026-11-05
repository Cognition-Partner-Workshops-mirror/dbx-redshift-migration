-- BI report: RFM segment sizes and value.
-- Redshift AVG over an integer column returns a truncated integer.
SELECT rfm_segment,
       COUNT(*)                         AS customers,
       SUM(monetary)                    AS total_monetary,
       SUM(frequency) DIV COUNT(*)      AS avg_frequency
FROM   gold.rfm_segments
GROUP  BY rfm_segment
ORDER  BY rfm_segment;
