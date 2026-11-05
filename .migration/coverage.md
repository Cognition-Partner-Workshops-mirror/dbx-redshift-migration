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
| payment_mix | DECODE, NVL, NVL2 | mismatch | | |
| returns_rate | integer division on INTs, :: casts | mismatch | | |
| attribution | SUPER / PartiQL unnesting (t, t.payload.touches tc) | rejected | | |
| inventory_snapshot | plpgsql upsert: staging + DELETE/INSERT | rejected | | |
| finance_export | UNLOAD TO s3 IAM_ROLE (export skipped at capture) | rejected | | |
| cohort_retention | TEMP TABLE steps, DATEDIFF(month) matrix | rejected | Lakebridge 0.13.0 + Bladebridge 0.3.0: etl.sql wrapped in an exception block (EXPLAIN parse error at the second statement); draft kept `mart.*`/`core.*`, turned SORTKEY into `ZORDER BY(...)`, kept `CREATE TEMP TABLE`, mistranslated `::DATE` as `::CURRENT_DATE`, and rewrote DATEDIFF(month) with a wrong year term (`YEAR(order month) - YEAR(order month)`, always 0). report.sql came out unchanged but failed EXPLAIN on `mart.cohort_retention`. | Rewritten by hand: temp tables -> CTEs in one `INSERT OVERWRITE` after typed `CREATE OR REPLACE TABLE gold.cohort_retention` DDL (DATE/INT/BIGINT/BIGINT, CLUSTER BY former sort key); `CAST(DATE_TRUNC('MONTH', ...) AS DATE)`; DATEDIFF(month) as calendar-boundary count `(YEAR diff)*12 + (MONTH diff)` cast to INT; report reads `gold.cohort_retention`, `ROUND(100.0 * a / b, 2)` unchanged. `make validate UNIT=cohort_retention` PASS 2/2 outputs (65 rows each) on attempt 1. |
| orchestration | cross-mart joins, refresh_schedule.yaml → Lakeflow job | clean | | |
