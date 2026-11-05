-------------- Exception Start-------------------
/*

[PARSE_SYNTAX_ERROR] Syntax error at or near 'UNLOAD'. SQLSTATE: 42601 (line 3, pos 0)

== SQL ==
EXPLAIN -- Monthly finance export to S3. Placeholders — never executed at capture
-- (listed in the unit's capture_skip in .migration/units.yaml).
UNLOAD ('SELECT * FROM mart.finance_monthly ORDER BY month')
^^^
TO 's3://<bucket>/finance_export/monthly/'
IAM_ROLE '<role-arn>'
PARALLEL OFF
CSV
HEADER;

*/

 ---------------Exception End --------------------
