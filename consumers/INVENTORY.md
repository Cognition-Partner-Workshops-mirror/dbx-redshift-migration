# Downstream consumer inventory

Repository-wide discovery searched tracked files for Redshift drivers and hosts,
`AmazonRedshift.Database`, `redshift_connector`, psql/ODBC markers, S3 URIs, and
`mart.`/`core.` references. Seven consumer surfaces contain 16 executable checks:
15 published report/file outputs mapped through `.migration/units.yaml`, and one
operational health query. Owners below describe the business surface; no named
individual owners are recorded in the assets.

| Surface / inferred owner | Connection location | Stable query locators | Migration |
| --- | --- | --- | --- |
| Tableau / executive analytics | `consumers/tableau/Retail Executive.twb`, four inline datasource connections | captions `daily_revenue`, `category_mix`, `customer_ltv`, `store_weekly` | Native Databricks connector with OAuth, embedded warehouse HTTP path, catalog `demo_redshift`, `gold`/`silver` SQL; preserve decimal AVG scale |
| Power BI / finance analytics | `consumers/powerbi/Finance Reporting.SemanticModel/definition/expressions.tmdl`, shared `Warehouse` expression | TMDL tables `finance_export`, `payment_mix`, `promo_lift` | `Databricks.Catalogs` catalog navigation; keep each literal `Value.NativeQuery` and use `gold` |
| Reporting HTTP API / reporting operations | `consumers/reporting-api/service.py`, `connect()` | `EXEC_SUMMARY_SQL`, `CHURN_SUMMARY_SQL`, `SHIPPING_SLA_SQL`, `HEALTH_SQL` | Databricks SQL connector with SDK/environment authentication; truncate integer AVG; replace `svv_table_info` with catalog information schema |
| Customer segments notebook / customer analytics | `consumers/notebooks/customer_segments.ipynb`, `warehouse` cell | tags `rfm_segments`, `cohort_retention`, literal `query` assignments | Databricks SQL connection; preserve integer AVG; read `gold` |
| Finance reconciliation notebook / finance operations | `consumers/notebooks/finance_reconciliation.ipynb`, `finance_monthly` cell, `export_path` variable | tag `finance_monthly`, path variable `export_path` | Replace legacy S3 prefix discovery with exact immutable CSV in `demo_redshift.gold.exports`, read via SDK Files API |
| **Cron outside consumers/** / operations | **`ops/cron/kpi_digest.sh`**, PG environment and psql invocation | heredoc `RETURNS_RATE_SQL` | Databricks SQL connector, environment warehouse ID, CSV stdout; read `gold.returns_rate` |
| **Excel outside consumers/** / regional reporting | **`shared/excel/Geo Rollup.odc`**, ODBC connection string | ODC Name `Geo Rollup`, CommandText | Databricks ODBC driver, HTTPS and embedded HTTP path, interactive OAuth, catalog `demo_redshift`, `gold.geo_rollup` |

## Coverage and boundaries

Each contract entry in `.migration/consumers.yaml` uses the original extractor
locator and maps to a declared output in `.migration/units.yaml`. Only the API
health query is smoke-only; all published reports and the delivered finance CSV
use existing Redshift goldens and unchanged tolerances. `mart` maps to `gold` and
`core` maps to `silver`. Code reads `DATABRICKS_WAREHOUSE_ID`; desktop files embed
`/sql/1.0/warehouses/6dc4b80538621b7b` and prompt the user to authenticate.

Other search matches belong to the pristine source estate, golden capture,
validation/setup/reset tools, migrated ETL, bundle resources, or historical
migration evidence. They are provenance or infrastructure, not additional live
downstream consumers, and are outside this consumer-only migration.

Parity executes extracted SQL and reads the delivered CSV on Databricks. It does
not launch Tableau, Power BI, or Excel. Their connection configuration also needs
inspection and a native desktop refresh before warehouse retirement.
