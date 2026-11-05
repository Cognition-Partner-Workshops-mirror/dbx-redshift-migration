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
| rfm_segments | NTILE(5), NULL ordering on NULL metrics | mismatch | Lakebridge 0.13.0 + Bladebridge 0.3.0: both drafts failed EXPLAIN. etl.sql was wrapped in an exception comment block: kept `DROP TABLE` + `CREATE OR REPLACE`, `mart.*`/`core.*` namespaces, turned SORTKEY into `ZORDER BY(customer_id)` (parse error), mistranslated `::DATE` to `::CURRENT_DATE` and `DATE '2025-12-31'` to `CURRENT_DATE '2025-12-31'` (non-deterministic/invalid), left NTILE ORDER BY without null placement (Databricks NULLS FIRST on ASC vs Redshift NULLS LAST) and VARCHAR(3)->STRING. report.sql passed through unchanged, still on `mart.rfm_segments` (EXPLAIN: TABLE_OR_VIEW_NOT_FOUND), and keeps `AVG(frequency)` (DOUBLE on Databricks vs Redshift truncated BIGINT). | Rewritten by hand: single `CREATE OR REPLACE TABLE gold.rfm_segments CLUSTER BY (customer_id) AS` over `silver.*`, `CAST(MAX(order_ts) AS DATE)` with literal `DATE '2025-12-31'`, DATEDIFF(DAY) kept, NTILE ORDER BY with explicit Redshift null placement (`ASC NULLS LAST`, `DESC NULLS FIRST`) plus `customer_id` tie-break; report on `gold.rfm_segments` with `SUM(frequency) DIV COUNT(*)` for Redshift integer AVG. `make validate UNIT=rfm_segments` PASS on attempt 1 and on the post-PR re-run, attempt 2 (1500/1500 rows, report 103/103, 0 mismatches). |
| promo_lift | MEDIAN, PERCENTILE_CONT WITHIN GROUP | mismatch | | |
| payment_mix | DECODE, NVL, NVL2 | mismatch | | |
| returns_rate | integer division on INTs, :: casts | mismatch | | |
| attribution | SUPER / PartiQL unnesting (t, t.payload.touches tc) | rejected | | |
| inventory_snapshot | plpgsql upsert: staging + DELETE/INSERT | rejected | | |
| finance_export | UNLOAD TO s3 IAM_ROLE (export skipped at capture) | rejected | | |
| cohort_retention | TEMP TABLE steps, DATEDIFF(month) matrix | rejected | | |
| orchestration | cross-mart joins, refresh_schedule.yaml → Lakeflow job | clean | | |
