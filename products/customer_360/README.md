# Customer 360

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
make deploy                         # validate dashboard SQL, reconcile Genie, deploy bundle + start app
make build                          # schema -> tables -> metrics
make verify                         # live reconciliation, metrics and invariants
make verify-dashboard               # every dashboard dataset via warehouse CLI
make deploy-genie                   # create/update Account Manager Assistant by title
make verify-genie                   # three live Conversation API checks, no browser
make reset                          # DESTRUCTIVE: bundle destroy (app/dashboard/job), trash Genie,
                                    # then Statement API DROP SCHEMA ... CASCADE
```

`PROFILE=DEFAULT` and `TARGET=demo` may be passed to make. Catalog/warehouse
variables have the approved defaults; alternative catalog writes require prior
approval. Reset is intentionally hard-scoped to `demo_redshift.customer_360`.
Reset deletes the Genie space, this bundle's dashboard and job and the product
schema, never bronze/silver/gold.

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

## Account Manager Assistant (step 3)

`genie/space.json` is the versioned, parsed serialized-space definition: five
certified sources, eight sample questions, four example SQL assets and merged
business instructions. Revenue/LTV always mean completed-order net value; the
snapshot date, fiscal boundaries, RFM precedence and customer lookup guidance
are explicit. No migrated gold tables are exposed.

`genie/manage.py deploy` uses the Genie API through the repository's pinned
Databricks SDK. It paginates spaces and creates or updates by exact title;
duplicate titles fail closed. It creates a parent folder under the authenticated
user's workspace home if needed and grants `users` CAN_RUN. Deploy twice to
reconcile the same space; do not run deployments concurrently. The ID is printed
with its URL and saved to gitignored `genie/.space_id`. The definition is scoped
to `demo_redshift.customer_360` and warehouse `6dc4b80538621b7b`, like the dashboard.

`make deploy` reconciles Genie then deploys the dashboard/app bundle. Tables and
metric views must already exist (`make build` on a new environment).
`make reset` destroys the bundle before trashing the space by title and dropping the schema;
deleting an absent space is a no-op. Genie is API-managed, not a bundle resource,
so use `make reset`, not only `bundle destroy`, for complete teardown.

`make verify-genie` starts three independent conversations via API, prints the
generated SQL and previews, and saves full evidence in gitignored
`genie/verification.local.json`. It checks certified source use, FY2025 Q3 for
the last completed fiscal quarter, and regional risk summing to $1,327,164.70.
These are live model responses, not a guarantee that every possible question
will produce correct SQL. No browser automation is used.

## Customer Lookup app (step 4)

`app/` contains a Streamlit app displayed as **Customer Lookup**, deployed as
bundle app resource `customer-lookup`. It uses app authorization: all authorized
app users share the app service principal's certified data access, not per-user
row-level identity. Group `users` has CAN_USE. No tokens are stored in code.

The cached SDK client uses `Config()` and the app's injected credentials. Bound
SQL Statement API parameters support case-insensitive literal name/email search
and exact customer ID lookup (up to 50 matches). Customer cards join profile and
health at customer grain; order history is separately limited to the last 10.
Portfolio counts use `MEASURE(customers)` from `customer_health_metrics`.
Ask Genie starts an independent conversation per question and displays answer
text, expandable SQL and result previews. Loading, empty and error states are
handled without displaying credentials or raw backend errors.

Bundle resources grant the app CAN_USE on the SQL warehouse and CAN_RUN on Genie;
`app/app.yaml` uses `valueFrom` for both IDs. `deploy_app.py` reconciles Genie,
passes its ID as `BUNDLE_VAR_genie_space_id`, deploys the bundle, grants the app
principal USE CATALOG on `demo_redshift` and USE SCHEMA/SELECT only on
`demo_redshift.customer_360`, then runs `bundle run customer-lookup`. Grants are
idempotent. No bronze/silver/gold permissions or objects are changed.

Use `make deploy` rather than bare bundle deploy for complete lifecycle handling.
For direct bundle commands, export `BUNDLE_VAR_genie_space_id` from
`genie/.space_id`; it is not committed. `make reset` removes the app through
bundle destruction, then trashes Genie and drops the certified schema.

Offline backend checks:
`python -m pytest products/customer_360/test_app.py -q` from the repository root.
To run locally, install `app/requirements.txt`, set `DATABRICKS_WAREHOUSE_ID` and
`GENIE_SPACE_ID` to the provisioned resource IDs, then run
`streamlit run app/app.py` from this directory using your existing CLI profile.
Local runs use your identity; deployed runs use the app principal.

Deployment checks: `databricks apps get customer-lookup` and
`databricks apps logs customer-lookup`. Verification for this step is CLI/HTTP
and local backend/framework checks only; the desktop browser is not used.

## Scope

PR target for this product is main; do not merge automatically.
