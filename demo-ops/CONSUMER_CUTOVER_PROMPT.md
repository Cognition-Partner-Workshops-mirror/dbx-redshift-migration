# Retail consumer cutover

The warehouse has moved from Redshift to Databricks. Find every downstream
consumer in this repository, including operational scripts and desktop
connection files, and migrate it without changing the published results.

1. Branch from `consumer-cutover`. Read AGENTS.md and D-004. Use Databricks profile
   DEFAULT, catalog `demo_redshift`, and the operator-provided
   `DATABRICKS_WAREHOUSE_ID`. The bronze, silver and gold schemas are read-only.
2. Discover every Redshift connection, query and exported-file dependency.
   Write `consumers/INVENTORY.md` with owners/surfaces, connection locations,
   query locators and proposed migration. Write `.migration/consumers.yaml`
   using the example format. Resolve each published output through
   `.migration/units.yaml`; operational checks use `check: smoke`.
   For file entries, `path` names the string variable holding the URI in the
   notebook cell selected by `query`. Do not replace a locator with a hardcoded
   expected result. Include consumers outside the consumers directory.
3. Run `make consumer-parity MODE=naive`. It reads original files from the
   operator's `consumer-cutover-baseline` tag, substitutes only connections and
   schema prefixes, and records the before matrix. A nonzero exit is expected
   when consumers require more than repointing.
4. Migrate each consumer in place: use Databricks connection classes or
   `databricks-sql-connector`, environment-based credentials, gold/silver
   references, and the existing monthly export under
   `/Volumes/demo_redshift/gold/exports/finance_export/monthly/as_of=2025-12-31/finance_monthly.csv`.
   Preserve stable extractor locators. TMDL shared connections belong in
   `definition/expressions.tmdl`; notebook SQL remains a literal `query` variable.
   Replace warehouse-specific operational checks with runnable Databricks reads.
   Do not execute legacy capture, ETL or writes to bronze/silver/gold.
5. Run `make consumer-parity MODE=current` until every entry passes. The current
   mode checks migrated connection markers and executes extracted queries on
   Databricks. It does not launch desktop BI products or notebook kernels;
   inspect and test those connection changes as well. Do not edit validation/,
   goldens, tolerances, dashboard resources, or setup tooling.
6. Open one PR into `consumer-cutover`, including the discovered inventory,
   contract, before/after matrices and evidence. Leave it open. Never merge.

The operator owns setup, the baseline tag, result storage and reset. Never run
`consumer-reset` during the migration session.
