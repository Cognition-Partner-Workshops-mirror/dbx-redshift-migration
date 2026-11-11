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
make deploy                         # bundle deploy
make build                          # schema -> tables -> metrics
make verify                         # live reconciliation, metrics and invariants
make reset                          # DESTRUCTIVE: bundle destroy --auto-approve,
                                    # then Statement API DROP SCHEMA ... CASCADE
```

`PROFILE=DEFAULT` and `TARGET=demo` may be passed to make. Catalog/warehouse
variables have the approved defaults; alternative catalog writes require prior
approval. Reset is intentionally hard-scoped to `demo_redshift.customer_360`.
Reset deletes only this bundle's job and the product schema, never bronze/silver/gold.

## Later steps (not implemented)

Add dashboard resources consuming metric views, a Genie space with these semantic
definitions, and an app as separate follow-up steps. No dashboard, Genie or app is
created by this bundle. PR target for this product is main; do not merge automatically.
