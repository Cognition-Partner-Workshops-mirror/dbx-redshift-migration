# Retail Reporting API

Install `pip install -r consumers/requirements.txt`, then run
`python consumers/reporting-api/service.py`. Set `DATABRICKS_WAREHOUSE_ID`
(`6dc4b80538621b7b` for this demo) and configure Databricks SDK unified
authentication through the deployment environment, or set
`DATABRICKS_CONFIG_PROFILE=DEFAULT` to use the existing local profile. The SDK
supplies renewable credentials to the SQL connector over HTTPS. No credentials
are stored in the service. The catalog is `demo_redshift`, default schema `gold`.

GET routes: `/executive-summary`, `/churn-summary`, `/shipping-sla`, `/health`.
The three report routes preserve their Redshift outputs, including integer AVG
truncation in churn-summary. Warehouse errors return HTTP 503.

The health route reads the visible `gold` table inventory from
`demo_redshift.information_schema.tables`. It retains the JSON keys `schema`,
`table`, `tbl_rows`, and `statistics_staleness_pct`, but returns **null** for the
last two fields: information_schema does not expose Redshift's estimated row
counts or `stats_off`. Freshness monitoring must treat null as unavailable;
the smoke check proves this query runs, not statistics freshness. Replace those
two monitoring inputs before using this endpoint to gate freshness alerts.
