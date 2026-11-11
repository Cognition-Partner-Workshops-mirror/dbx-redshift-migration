# Databricks downstream consumers

Install the code-consumer dependencies from the repository root:

```sh
pip install -r consumers/requirements.txt
export DATABRICKS_CONFIG_PROFILE=DEFAULT
export DATABRICKS_WAREHOUSE_ID=6dc4b80538621b7b
```

The profile must already authenticate to the demo workspace. Deployments may
instead supply Databricks unified authentication in their environment. All code
uses the SDK credential provider; secrets are never embedded. The reporting API,
customer notebook and cron script read the warehouse ID from the environment.
The finance notebook downloads a UC volume file through the SDK and needs no
warehouse. Every consumer reads catalog `demo_redshift` without rebuilding marts.

Run the API with `python consumers/reporting-api/service.py`, run the digest with
`bash ops/cron/kpi_digest.sh`, and execute each notebook's cells in order with
the same authenticated environment. The digest preserves headered CSV stdout.
The notebook connection is closed by its final cell. Published SQL assignments,
datasource captions and heredoc tags remain stable for the parity extractor.

## Desktop connections

Desktop files contain the workspace host and HTTP path
`/sql/1.0/warehouses/6dc4b80538621b7b`; they do not expand shell environment
variables. Open the existing assets, authenticate using Databricks OAuth, then
refresh each datasource:

- Tableau: install the Databricks connector/ODBC driver supported by Tableau
  Desktop 2021.4 or later. All four inline datasources use the native
  `databricks` connector, `v-http-path`, OAuth and `Catalog=demo_redshift`.
  Fully qualified SQL also pins the catalog. Authenticate each connection when
  prompted; no OAuth tokens are stored in the workbook.
- Power BI: open the semantic model in Power BI Desktop with TMDL support,
  configure Databricks credentials in Data Source Settings, and approve the
  native queries if prompted. `Warehouse` navigates `Databricks.Catalogs` to
  the `demo_redshift` database; all three partitions retain their
  `Value.NativeQuery` locators.
- Excel: install the 64-bit Databricks ODBC driver 2.8.2 or later, matching
  Excel's bitness. Open `shared/excel/Geo Rollup.odc`. If the installed driver
  has another registered name, select it in the ODBC connection dialog.
  `AuthMech=11;Auth_Flow=2` launches local browser OAuth. Enter a local
  refresh-token encryption passphrase in the driver prompt (`PWD`) when
  requested; do not save it in the shared file. Catalog and schema are explicit.

Native Tableau, Power BI and Excel refreshes require their desktop products and
drivers. SQL/file parity does not certify those product-specific refresh paths.

## Published semantics and evidence

Redshift truncates AVG of an integer to an integer and AVG of a decimal to its
input scale. Preserve that contract in churn, RFM and LTV reports rather than
rounding or changing the goldens. The finance notebook reads only the immutable
`as_of=2025-12-31/finance_monthly.csv` export from `gold.exports`, avoiding a
prefix scan that could concatenate multiple snapshots.

Run `make consumer-parity MODE=naive` for the baseline-only repoint, and
`make consumer-parity MODE=current` for migrated assets. See `INVENTORY.md`,
`.migration/consumers.yaml` and `.migration/evidence/consumers_*.json` for coverage
and results. Only API health is smoke-only; its two unavailable metrics are
documented in `reporting-api/README.md`.

Connection guidance: [Python connector](https://docs.databricks.com/aws/en/dev-tools/python-sql-connector),
[Tableau](https://docs.databricks.com/aws/en/partners/bi/tableau),
[Power BI](https://docs.databricks.com/aws/en/partners/bi/power-bi-desktop),
[ODBC authentication](https://docs.databricks.com/aws/en/integrations/odbc/authentication).
