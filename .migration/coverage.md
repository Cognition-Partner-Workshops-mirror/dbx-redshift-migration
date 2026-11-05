# Construct coverage

Redshift construct → *expected* Lakebridge outcome (hypothesis, not fact) →
observed (filled by migration sessions) → fix pattern. "review feedback
updates the playbook": when a session hits a mismatch, it records the observed
outcome and the fix that made `make validate` pass.

| unit | construct | expected | observed | fix pattern |
| --- | --- | --- | --- | --- |
| foundation | DISTKEY/SORTKEY/DISTSTYLE/ENCODE, IDENTITY, SUPER | clean | Lakebridge 0.13.0 + Bladebridge 0.3.0: all 3 drafts failed EXPLAIN. 02_core_tables kept `core.*`, made tables CREATE OR REPLACE, turned SORTKEY into `ZORDER BY(...)` (parse error), dropped ENCODE/DISTKEY/DISTSTYLE, VARCHAR->STRING, NUMERIC->DECIMAL, kept CHAR(4) and left `SUPER` untranslated. 03_udfs kept `IMMUTABLE` + `$$` bodies (parse error) and replaced `$1` with the literal word `STRING`. 01_schemas failed at the second CREATE SCHEMA. | Rewritten by hand: bronze = `read_files` on `/Volumes/<current_catalog()>/bronze/raw` via EXECUTE IMMEDIATE param, all STRING, `nullValue \N`, quote/escape `"`, FAILFAST; silver = explicit typed DDL + INSERT OVERWRITE (RTAS rejects a column list), Redshift types kept, TIMESTAMP->TIMESTAMP_NTZ, SUPER->STRING JSON text, CHAR(4) blank-padded explicitly (Databricks CHAR does not pad on write or read), CLUSTER BY on former dist/sort keys; UDFs = `silver.f_fiscal_qtr` (`div` for integer division) and `silver.f_clean_phone`. `make validate UNIT=foundation` PASS 10/10 outputs. |
| daily_revenue | DATE_TRUNC/TRUNC, SUM GROUP BY | clean | | |
| customer_ltv | CHAR(4) padding carried into output, AVG on NUMERIC(12,2) scale | mismatch | | |
| geo_rollup | GROUPING SETS, GROUPING() id column | clean | | |
| churn_flags | plpgsql procedure, FOR loop, temp table, CALL | rejected | | |
| product_perf | LISTAGG(...) WITHIN GROUP (ORDER BY ...), ::casts | mismatch | | |
| store_weekly | DATE_TRUNC('week'), DATEADD, DATEDIFF(week) | clean | | |
| category_mix | RATIO_TO_REPORT | clean | | |
| basket_affinity | self-join pairs, HAVING support >= threshold | clean | | |
| sessionization | LAG, 30-min gap, running SUM session id | clean | | |
| shipping_sla | DATEDIFF(hour) boundary counting, CONVERT_TIMEZONE | mismatch | | |
| rfm_segments | NTILE(5), NULL ordering on NULL metrics | mismatch | | |
| promo_lift | MEDIAN, PERCENTILE_CONT WITHIN GROUP | mismatch | Lakebridge 0.13.0 + Bladebridge 0.3.0: etl draft failed EXPLAIN (PARSE_SYNTAX_ERROR at the second statement; DROP + CREATE OR REPLACE submitted as one) and was emitted only inside an exception comment wrapper; it kept `core.*`/`mart.*`, made CREATE TABLE -> CREATE OR REPLACE, and rewrote MEDIAN -> `PERCENTILE_CONT(0.5) WITHIN GROUP`. report draft unchanged but kept `mart.promo_lift` (TABLE_OR_VIEW_NOT_FOUND). As drafted, Databricks percentile_cont returns DOUBLE (e.g. 390.21500000000003, 1110.566) while Redshift goldens are NUMERIC truncated to input scale (390.21, 1110.56), so a straight port mismatches. | Hand-fixed: `silver.*`/`gold.*`, single CREATE OR REPLACE TABLE (no DROP), MEDIAN/PERCENTILE_CONT as exact DECIMAL linear interpolation (ROW_NUMBER + COUNT window, position 1+p*(n-1), lo + frac*(hi-lo)) then truncate toward zero to scale 2 (FLOOR/CEIL(x,2)) and CAST DECIMAL(38,2); order_count BIGINT. `make validate UNIT=promo_lift` PASS 2/2 outputs (attempt 1; post-PR re-run attempt 2 PASS). |
| payment_mix | DECODE, NVL, NVL2 | mismatch | | |
| returns_rate | integer division on INTs, :: casts | mismatch | | |
| attribution | SUPER / PartiQL unnesting (t, t.payload.touches tc) | rejected | | |
| inventory_snapshot | plpgsql upsert: staging + DELETE/INSERT | rejected | | |
| finance_export | UNLOAD TO s3 IAM_ROLE (export skipped at capture) | rejected | | |
| cohort_retention | TEMP TABLE steps, DATEDIFF(month) matrix | rejected | | |
| orchestration | cross-mart joins, refresh_schedule.yaml → Lakeflow job | clean | | |
