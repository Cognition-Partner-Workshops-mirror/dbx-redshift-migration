# Customer 360 data product (`demo_redshift.customer_360`)

A certified Customer 360 product built next to the migrated Redshift estate. It reads `demo_redshift.silver` (and `gold` only for the legacy comparison) and writes only `demo_redshift.customer_360`. See decision D-002 in `.migration/06_decisions.md`.

| Asset | What it is |
| --- | --- |
| `sql/00_schema.sql` | Creates the `customer_360` schema |
| `sql/01_tables.sql` | `order_facts` (1 row per order), `customer_profile` and `customer_health` (1 row per customer), `legacy_vs_certified` |
| `sql/02_metrics.sql` | Metric views `revenue_metrics` and `customer_health_metrics`: the single source of KPI definitions for the dashboard, Genie and the app |
| `resources/build_job.yml` | `customer_360_build`: sequential SQL-file job (schema → tables → metrics) |
| `dashboards/customer_health_revenue.lvdash.json` | AI/BI dashboard "Customer Health & Revenue" (Executive overview + Legacy vs certified) |
| `genie/space.json`, `genie/manage.py` | Genie space "Account Manager Assistant" (create-or-update by title, grants `users` CAN_RUN) |
| `app/` | Streamlit Databricks App "customer-lookup" (search, customer card, last 10 orders, portfolio counts, Ask Genie) |
| `verify.py` | Live checks: grains, invariants and the expected KPI values |
| `tests/` | Offline checks (no workspace needed) |

## Definitions
- As of `2025-12-31` (literal, no `CURRENT_DATE`). Fiscal year starts Feb 1 (`quarter(add_months(d, -1))`).
- Revenue and LTV are **net**: completed orders only. Gross includes cancelled and returned orders.
- Segments, in precedence order: Never ordered → Champion (R≥4, F≥4) → At risk (R≤2, F≥3) → Loyal (F≥3) → Hibernating (R≤2) → Promising. Revenue at risk = net LTV of At-risk customers.
- On-time delivery = delivered within 96 hours (NULL when a timestamp is missing or the duration is negative).

## Build and deploy
Uses the existing Databricks CLI profile (`DATABRICKS_CONFIG_PROFILE`, default `DEFAULT`).

```bash
cd products/customer_360
make deploy build verify   # bundle (job, dashboard, app), run the build job, live checks
make genie                 # create or update the Genie space
make app-grants app-deploy # UC grants for the app service principal, then start the app
make test                  # offline tests
```

If the Genie space is recreated, update `genie_space_id` in `databricks.yml` and redeploy so the app points at it.
