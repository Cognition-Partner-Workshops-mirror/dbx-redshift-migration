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
| promo_lift | MEDIAN, PERCENTILE_CONT WITHIN GROUP | mismatch | | |
| payment_mix | DECODE, NVL, NVL2 | mismatch | Lakebridge 0.13.0 + Bladebridge 0.3.0: etl.sql draft failed EXPLAIN (PARSE_SYNTAX_ERROR at the second statement, DROP + CREATE in one EXPLAIN) and was wrapped in an exception comment block; it kept `core.payments`/`mart.payment_mix`, made CREATE OR REPLACE, NVL->COALESCE, kept DECODE/NVL2, left `SUM/SUM(SUM) OVER()` share as plain decimal division. report.sql passed through unchanged with `mart.payment_mix` (EXPLAIN warning TABLE_OR_VIEW_NOT_FOUND). | Removed wrapper and DROP; `core`->`silver`, `mart`->`gold`; dropped ORDER BY in CTAS. DECODE/NVL2/COALESCE kept (native). Redshift NUMERIC(38,2)/NUMERIC(38,2) truncates to scale 4 while Databricks decimal division rounds (gift_card 0.14574 ok, cash 0.14726 would round to 0.1473 vs golden 0.1472), so share = `CAST(FLOOR(x, 4) AS DECIMAL(38,4))`. `make validate UNIT=payment_mix` PASS 2/2 outputs on attempt 1. |
| returns_rate | integer division on INTs, :: casts | mismatch | | |
| attribution | SUPER / PartiQL unnesting (t, t.payload.touches tc) | rejected | | |
| inventory_snapshot | plpgsql upsert: staging + DELETE/INSERT | rejected | | |
| finance_export | UNLOAD TO s3 IAM_ROLE (export skipped at capture) | rejected | | |
| cohort_retention | TEMP TABLE steps, DATEDIFF(month) matrix | rejected | | |
| orchestration | cross-mart joins, refresh_schedule.yaml → Lakeflow job | clean | | |
