# Customer 360 — booth run-of-show

## Story: build on Databricks, not just move to it

The migration preserved the legacy answers, including their bugs. Now build a
certified data product on that foundation: correct the business semantics once,
reuse them in a leadership dashboard, ask natural-language questions in Genie,
and put the same customer intelligence in an account manager's app. Close with
Devin extending the product live, with tests and reviewable code—not a one-off query.

All figures are a fixed **2025-12-31** snapshot, in USD. Revenue/LTV mean net
completed-order value. Legacy gross revenue is $10.54M; certified net is $6.28M,
with $4.27M excluded for cancelled/returned orders. True AOV is $527.52, not $196.13.

## Before the booth opens

- Use the already provisioned devin-gtm workspace, default CLI profile (Devin SP),
  warehouse `6dc4b80538621b7b`, and branch `devin/1794366823-customer-360-product`.
- From `products/customer_360/`, with repository requirements installed:

  ```sh
  databricks current-user me
  make build          # refresh deterministic tables and metric views
  make deploy         # validate dashboard SQL, reconcile Genie, publish dashboard, start app
  make verify
  databricks apps get customer-lookup
  ```

- Confirm app compute ACTIVE / deployment SUCCEEDED. Allow warehouse/app warm-up
  before presenting. `make deploy` requires existing certified tables/views;
  this checklist assumes the booth product is provisioned, not a fresh install
  after full teardown.
- Have the presenter open these links; reset dashboard filters to **All**:
  - [Dashboard draft](https://dbc-c22a0245-3975.cloud.databricks.com/dashboardsv3/01f1dd7f19fc1e6a909b3933d7b1f146?w=7474652505890469)
  - [Published leadership dashboard](https://dbc-c22a0245-3975.cloud.databricks.com/dashboardsv3/01f1dd7f19fc1e6a909b3933d7b1f146/published?w=7474652505890469)
  - [Account Manager Assistant — Genie](https://dbc-c22a0245-3975.cloud.databricks.com/genie/rooms/01f1dd7fa5fd1145bf01f01106d5a0c7)
  - [Customer Lookup app](https://customer-lookup-7474652505890469.aws.databricksapps.com)
- Use an authorized workspace user (`users` group). URLs above are for the
  current deployment; full teardown/recreation can change IDs. Genie deployment
  prints its URL and saves its ID in gitignored `genie/.space_id`; use bundle
  summary / `databricks apps get customer-lookup` for recreated resource links.
- Rehearse the live prompt in a separate session; keep the baseline clean.
  Genie answers can vary—show the SQL and certified sources, not just prose.

## Click order — 9 minutes, up to 10 with questions

| Time | Surface / action | Talk track |
|---|---|---|
| 0:00–0:30 | Open published dashboard | “Build on Databricks, not just move to it. Migration parity is the starting line.” |
| 0:30–2:00 | **Executive overview**: six KPIs, monthly gross/net gap, health and regional risk | Net $6.28M, leakage $4.27M, true AOV $527.52, revenue at risk $1.33M. Quarter/channel filter revenue; region also filters lifetime health. Reset to All. |
| 2:00–3:00 | **Legacy vs certified**: explanation table, normalized bars | Show why certified differs. Q1 isolates the fiscal calendar correction at gross scope; return rate here is unit-based, unlike the order-rate metric. This is governed semantics, not dashboard arithmetic. |
| 3:00–5:00 | Genie: ask the questions below; expand SQL on one | Same certified product, now conversational. Last fiscal quarter is anchored to the snapshot, not today's date. |
| 5:00–6:30 | App: search **Emerson Silva**, choose email `emerson.silva342@example.com` / ID **342** | Names repeat: disambiguate with email/ID. Show WEST, At risk badge, net LTV/revenue at risk **$7,867.09**, contact/store fields and last 10 orders. Optionally ask the regional-risk question in the app. |
| 6:30–8:30 | Live Devin session: paste prompt below; narrate diff, test plan and API query | Extend the reusable semantic layer, not a bespoke slide. If execution runs long, show progress and the acceptance query; do not claim completion. |
| 8:30–9:00 | Close on dashboard/app | “One certified product, multiple experiences, continuously extended with Devin.” Keep the remaining minute for questions. |

### Genie questions (two required, third if time)

1. **Which At risk customers in the WEST have the highest net LTV?**
   Expect customer #342, Emerson Silva, near the top. At risk is the stored RFM
   segment, not simply a 90-day cutoff.
2. **How much revenue is at risk by region?**
   Expect six regions totaling **$1,327,164.70**, using
   `customer_health_metrics` and `MEASURE(revenue_at_risk)`.
3. **What was net revenue by channel last fiscal quarter?**
   Expect FY2025 Q3 (Aug–Oct), using `revenue_metrics`, `MEASURE(net_revenue)`.

### Live Devin prompt — copy/paste

> Add revenue at risk by region measure support to the customer_360 product in
> ~/repos/dbx-redshift-migration. First inspect what exists: revenue_at_risk and
> the region dimension are already in customer_health_metrics and the dashboard
> already charts them, so do not duplicate or replace those assets. Extend the
> metric view with a complementary measure named
> avg_revenue_at_risk_per_at_risk_customer: SUM(source.revenue_at_risk) divided
> safely by COUNT_IF(source.health_segment = 'At risk'). Give it a concise USD
> comment and synonyms. Put it in products/customer_360/sql/02_metrics.sql only,
> with focused tests under products/customer_360/ for normal, empty and zero-risk
> denominators. Keep the literal 2025-12-31 snapshot and existing RFM precedence.
> Query the new measure by region with MEASURE(), and verify the original total
> revenue_at_risk remains 1327164.70. Run the repository and product tests before
> deploying with make build, then verify via the SQL warehouse API. Use the
> default CLI profile and warehouse 6dc4b80538621b7b; run current-user me first.
> Only demo_redshift.customer_360 writes are approved. Never modify migrated
> bronze/silver/gold, legacy/, golden/, data/seed/ or validation/. Use CLI/API
> only—do not touch the desktop browser. Show the diff and evidence; do not
> commit, push, reset, or change dashboard/Genie/app assets without approval.

Acceptance query after the live change:

```sql
SELECT region,
       MEASURE(revenue_at_risk) AS revenue_at_risk,
       MEASURE(avg_revenue_at_risk_per_at_risk_customer) AS avg_at_risk_ltv
FROM demo_redshift.customer_360.customer_health_metrics
GROUP BY region
ORDER BY revenue_at_risk DESC;
```

## Reset / repeat

**Between booth loops:** clear dashboard filters, start a fresh Genie conversation,
and clear the app search. Do not tear down the product just to restart the story.

**Remove only the live-added measure:** delete only the
`avg_revenue_at_risk_per_at_risk_customer` YAML measure block from
`sql/02_metrics.sql` and its demo-only tests. Review the diff, run tests, then
`make build` to restore the baseline metric view. This refreshes the deterministic
product tables too, but does not destroy the dashboard, Genie or app. Keep the
original `revenue_at_risk` measure and region dimension. If any extra consumers
were added outside this prompt, remove their references first. Do not DROP the
metric view, reset the branch, or discard unrelated work.

**Full teardown (after the event):** from `products/customer_360/`, run:

```sh
make reset
```

This destroys this bundle's app, dashboard and job, trashes **Account Manager
Assistant**, and executes `DROP SCHEMA IF EXISTS demo_redshift.customer_360 CASCADE`.
It does **not** drop `demo_redshift` or touch its bronze/silver/gold schemas, legacy
SQL, seeds or goldens. It removes live-added objects inside customer_360 as well.
This is destructive and is not part of the timed booth demo.
