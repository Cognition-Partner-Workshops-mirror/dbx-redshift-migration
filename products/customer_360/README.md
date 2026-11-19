# Customer 360

This product publishes a certified snapshot of the retail demo on December 31, 2025. The data job reads the existing silver estate and references gold only for the legacy comparison. Its output is `demo_redshift.customer_360`. The dashboard, Genie space and Customer Lookup app share the same two Unity Catalog metric views.

## Rebuild in Databricks

Use Databricks CLI with the existing workspace OIDC profile. Run these commands from this product directory after installing the repository's Python requirements.

```sh
make deploy build verify
make dashboard
make genie genie-check
make app
```

- `make deploy` deploys the build job and `make build` runs the three sequential SQL-file tasks.
- `make verify` checks table grain, status, fiscal and SLA invariants, as well as the seeded comparison values and customer lookup.
- `make dashboard` runs the dashboard's SQL and representative filter bindings, then deploys and publishes with embedded credentials.
- `make genie` creates or updates Account Manager Assistant by title, and `make genie-check` checks three conversations.
- `make app` resolves the Genie resource ID, deploys the app, applies explicit data access to its service principal, and starts the deployment. The app serves the synthetic demo data to workspace `users` through its service principal.

`PROFILE` defaults to `DEFAULT` and `WAREHOUSE` to `6dc4b80538621b7b`. `WAREHOUSE_ADMIN_PROFILE` defaults to `devin-admin` and is used for the app principal's warehouse ACL. Keep the bundle owner profile consistent across deploys to reuse the existing deployment state.

## Published definitions

The order metrics use the store region and the customer metrics use the customer's home region. On the dashboard, region applies to both. Fiscal quarter and sales channel apply only to order measures because the portfolio is a point-in-time snapshot.

Fiscal years are named for their starting year. February 2025 starts FY2025 Q1. Return rate is returned item units divided by sold item units. On-time delivery uses valid ship-to-delivery durations of up to 96 hours. Active customers placed a completed order in the last 90 days. Repeat rate is the fraction of purchasers with at least two completed orders. See the metric view YAML for the governed formulas.

Run `make test` for offline product checks. See [the booth guide](DEMO.md) for the click order and manual reset.
