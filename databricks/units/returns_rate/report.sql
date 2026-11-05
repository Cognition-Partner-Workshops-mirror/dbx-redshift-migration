-- BI report: returns rate as published.
SELECT category, sold_qty, returned_qty, return_rate_int, return_pct
FROM   gold.returns_rate
ORDER  BY return_pct DESC NULLS FIRST, category;  -- Redshift sorts NULLs first on DESC
