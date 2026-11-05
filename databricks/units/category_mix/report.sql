-- BI report: category mix as published.
SELECT category, units_sold, revenue, revenue_share
FROM   gold.category_mix
ORDER  BY revenue DESC, category;
