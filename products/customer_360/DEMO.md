# Customer 360 booth walkthrough

Migration gave the business its existing reports on Databricks. Customer 360 gives leadership and account managers one set of definitions they can use across a dashboard, Genie, and an app. The retail data is frozen on December 31, 2025.

## Open before the demo

- [Customer Health & Revenue](https://dbc-c22a0245-3975.cloud.databricks.com/dashboardsv3/01f1e420cf6615819f6d27629810657e/published?o=7474652505890469)
- [Legacy vs certified](https://dbc-c22a0245-3975.cloud.databricks.com/dashboardsv3/01f1e420cf6615819f6d27629810657e/published/pages/legacy_comparison?o=7474652505890469)
- [Account Manager Assistant](https://dbc-c22a0245-3975.cloud.databricks.com/genie/rooms/01f1e420dfbd135fb3d5d5deb32f5659?o=7474652505890469)
- [Customer Lookup](https://customer-lookup-7474652505890469.aws.databricksapps.com)
- [Customer 360 in Catalog Explorer](https://dbc-c22a0245-3975.cloud.databricks.com/explore/data/demo_redshift/customer_360?o=7474652505890469)

Sign in to the workspace and authorize Customer Lookup if prompted. Refresh the published dashboard and clear its filters before presenting. The links are from this deployment. A rebuild after a reset can assign new dashboard and Genie IDs.

## Nine-minute click order

| Time | Action | Point to make |
| --- | --- | --- |
| 0:00–2:00 | Open the executive page. Point to net revenue, excluded order value and monthly gross vs net. Select fiscal Q1, then clear it. | $6.28M net on 11,902 completed orders. Q1 starts in February and shows $1.56M net. The customer snapshot can be filtered by region. |
| 2:00–3:30 | Open **Legacy vs certified**. | Revenue moves from $10.54M to $6.28M. AOV rises from $196.13 to $527.52 when the unit becomes a whole completed order. Explain the fiscal and return-rate changes from the comparison table. |
| 3:30–5:30 | In Genie, ask “Which regions have the most revenue at risk?” and “How many customers are in each health segment?” Optionally ask for monthly net revenue by sales channel. | SOTH leads with $292,691.46 at risk. Highlight the certified metric in the generated SQL. |
| 5:30–7:30 | Search for `#342` in Customer Lookup. Review Emerson Silva’s card and recent orders, then open **Ask Genie** and ask which regions have the most revenue at risk. | Emerson is At risk in WEST with $7,867.09 net LTV, a $715.19 average order and 50 days of recency. The embedded answer uses the same Genie space. |
| 7:30–9:00 | Live prompt Devin to add a governed measure. | “Devin, add an `at_risk_customer_rate` measure to `customer_health_metrics` for the share of all customers classified as At risk. Verify it on the seeded snapshot and show the SQL.” Expect 248 ÷ 1,500, or about 16.53%. |

## Manual reset

From this product directory, use the OIDC profile that owns the demo bundle. Run `databricks bundle destroy --profile DEFAULT` and review the resources listed before confirming. This removes the build job, published dashboard and Customer Lookup app. Trash **Account Manager Assistant** from its Genie page, or use `databricks genie trash-space <space-id> --profile DEFAULT` after confirming the ID with `databricks genie list-spaces --profile DEFAULT`.

On the demo warehouse, run `DROP SCHEMA IF EXISTS demo_redshift.customer_360 CASCADE` using the product owner. Verify the schema and the three audience artifacts are absent before rebuilding.
