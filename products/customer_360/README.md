# Customer 360 — step 1

An independent `customer-360` Databricks Asset Bundle. Reads `silver` and legacy
`gold` in the selected catalog and writes **only** `customer_360`. The approved
deployment is `demo_redshift.customer_360` on the devin-gtm workspace, using the
default CLI profile (Devin SP) and warehouse `6dc4b80538621b7b`. D-002 records
Mason's scope exception; this product does not repair or overwrite legacy marts.

## Model and semantics

* `order_facts`: one row/order, discounted line spend = quantity × (unit price −
  discount). Gross includes all statuses; net includes only `complete`.
  Fiscal year is the **start year**, February 1–January 31; Q1 is Feb–Apr.
  Items means unit quantity. Shipping uses decimal elapsed seconds/3600 from
  ship to delivery, taking the slowest shipment per order. Missing/incomplete
  delivery is NULL, excluded from on-time denominator (96 hours inclusive).
* `customer_profile`: all registered customers, trimmed region, raw contact
  fields, preferred store, order history and completed-order AOV. Never
  purchasers retain zero LTV and NULL AOV. Top category is ranked by complete
  order line spend, ties broken by category name. Return count is return records.
* `customer_health`: recency/frequency/monetary use **completed orders** at
  literal `DATE'2025-12-31'`. NTILE(5) runs only on purchasers; higher is better,
  ties ordered by customer ID. Non-purchasers have NULL recency/tiles, zero F/M.
  Precedence: **Never ordered** (no completed orders), **Champion** (r≥4,f≥4),
  **At risk** (r≤2,f≥3), **Loyal** (f≥3), **Hibernating** (r≤2), **Promising**.
  At risk must precede Loyal. Revenue at risk is that segment's complete-order LTV.
* `legacy_vs_certified`: five KPI rows, difference = certified − legacy.
  Revenue, order AOV and purchaser-only average LTV fix recognition/grain/scope.
  Q1 deliberately holds all-status spend constant to isolate the fiscal calendar
  bug. Return rate is returned **units** / sold units, compared to legacy integer
  division. This differs from the metric view's returned-status **order** rate.
* `revenue_metrics` and `customer_health_metrics`: governed YAML semantic views
  queried with `MEASURE(...)`. Rates are fractions except on-time delivery, which
  is 0–100 percent. Active means completed purchase within 90 days; repeat rate
  uses purchasers as denominator; average LTV excludes never purchasers.

No clock-based output or AI-generated values are persisted. Orders, signups and
returns after 2025-12-31 are excluded. Job parameters select the catalog through
`USE CATALOG IDENTIFIER(:catalog)`; semantic sources resolve in that catalog.
Job `CAN_MANAGE_RUN` includes read access; `users` can view and run the job.

## Operations

From this directory (CLI authenticated and repository requirements installed):

```sh
databricks current-user me
databricks bundle validate -t demo
make deploy                         # validate dashboard SQL, bundle deploy + publish
make build                          # schema -> tables -> metrics
make verify                         # live reconciliation, metrics and invariants
make verify-dashboard               # every dashboard dataset via warehouse CLI
make reset                          # DESTRUCTIVE: bundle destroy --auto-approve,
                                    # then Statement API DROP SCHEMA ... CASCADE
```

`PROFILE=DEFAULT` and `TARGET=demo` may be passed to make. Catalog/warehouse
variables have the approved defaults; alternative catalog writes require prior
approval. Reset is intentionally hard-scoped to `demo_redshift.customer_360`.
Reset deletes this bundle's dashboard and job and the product schema, never bronze/silver/gold.

## Leadership dashboard (step 2)

`dashboards/customer_health_revenue.lvdash.json` is managed by the bundle resource
`customer_health_revenue`: **Customer Health & Revenue**. Bundle deployment publishes
it with embedded publisher credentials on the configured SQL warehouse. Group
`users` has `CAN_RUN` (including view access). Bundle destroy trashes the dashboard.
The dashboard queries fully qualified `demo_redshift.customer_360` objects; changing
the bundle catalog variable does not retarget the dashboard SQL.

Page 1 shows six leadership KPIs, monthly gross versus net revenue, channel and
region revenue, customer health mix, and regional revenue at risk. Page 2 explains
the five legacy corrections, with revenue/AOV/LTV normalized to legacy = 100%.
Currency is USD; on-time delivery is displayed as a percentage.

Global single-select filters default to **All**. Fiscal quarter and channel apply
to revenue datasets **before** metric aggregation, preserving correct AOV and
on-time denominators. Region also applies to all customer-health datasets.
Lifetime customer health has no fiscal-quarter/channel dimensions, so those two
filters intentionally do not change the health snapshot. The precomputed legacy
comparison stays all-company and unfiltered. Both pages state this scope visibly.
Active customers means completed purchase within 90 days of 2025-12-31.

Regenerate the JSON with `make dashboard-json` after changing `build_dashboard.py`.
`make deploy` runs every exact dataset query with default parameters via CLI
before deployment, then checks a Q1/web/EAST slice. `make reset` removes the
dashboard through bundle destroy before dropping the product schema.

## Later steps (not implemented)

Add a Genie space with these semantic definitions and an app as separate follow-up
steps. No Genie or app is created by this bundle. PR target for this product is
main; do not merge automatically.
