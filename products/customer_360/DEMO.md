# Customer 360 booth demo

**Story:** the Redshift estate was migrated faithfully, bugs included: revenue counts cancelled and returned orders, AOV averages line items, the fiscal calendar is off by a month and the return rate is always 0. Devin built a certified Customer 360 product next to it, with KPIs defined once in metric views and reused by the dashboard, Genie and the app. Build on Databricks, not just move to it.

## URLs
| Asset | URL |
| --- | --- |
| Dashboard: Customer Health & Revenue | https://dbc-c22a0245-3975.cloud.databricks.com/dashboardsv3/01f1dd85dcb91f82aa1ec623a98c1962/published?o=7474652505890469 |
| Genie: Account Manager Assistant | https://dbc-c22a0245-3975.cloud.databricks.com/genie/rooms/01f1dd862bcd1c1ca7e4aed81a0846c5?o=7474652505890469 |
| App: Customer Lookup | https://customer-lookup-7474652505890469.aws.databricksapps.com |
| Metric views | https://dbc-c22a0245-3975.cloud.databricks.com/explore/data/demo_redshift/customer_360?o=7474652505890469 |
| Build job | https://dbc-c22a0245-3975.cloud.databricks.com/jobs/1034591850185384?o=7474652505890469 |

## 9-minute click order
1. **Dashboard, Executive overview (2 min).** Net revenue $6.28M vs gross $10.54M: $4.27M of "revenue" was cancellations and returns. AOV $527.52, return rate 5%, on-time 68.3%, revenue at risk $1.33M. Filter Region = SOTH: risk $292.69K, the highest region. Click Refresh if tiles look stale.
2. **Legacy vs certified page (1.5 min).** Walk the 5 rows: revenue $10.54M → $6.28M, AOV $196.13 → $527.52, average LTV $7,029 → $4,637, fiscal Q1 (Mar–May → Feb–Apr), return rate 0 → 5.0%. Each row says why.
3. **Genie (2 min).** Ask 2–3 of:
   - "Which region has the most revenue at risk?" → SOTH, $292,691.46
   - "How many customers are in each health segment?" → Hibernating 294, Loyal 292, Champion 272, At risk 248, Promising 248, Never ordered 146
   - "Who are the top 10 At-risk customers by net LTV?"
   Open the SQL: it uses `MEASURE()` on the metric views.
4. **Customer Lookup app (2 min).** Search `342` (or "Emerson Silva", 9 matches, pick #342 WEST): At risk, net LTV $7,867.09, AOV $715.19, recency 50 days, last 10 orders newest first. Sidebar portfolio counts come from `customer_health_metrics`. Ask Genie tab: "Which region has the most revenue at risk?" shows answer, SQL and table. First open may show an OAuth consent page: click Authorize.
5. **Live "Devin, add a measure" (1.5 min).** Prompt:
   > Devin, add a `discount_amount` column to `order_facts` (from `silver.order_items.discount`) and a `discount_rate` measure (discount over list value) to `revenue_metrics` in `products/customer_360`, add it to the dashboard KPI row and as a Genie synonym, run verify and open a PR.

   (Revenue at risk by region already exists, so don't use it as the live ask.)

## Reset
Run the `!c360_reset` playbook, or manually: delete app `customer-lookup`, trash the "Account Manager Assistant" Genie space, `databricks bundle destroy -t demo_redshift` in this folder (job and dashboard), then `DROP SCHEMA demo_redshift.customer_360 CASCADE`. Leave `bronze/silver/gold`, `consumer_parity`, "Commerce Analytics" and the "Redshift Migration - Gold Sales & Customers" dashboard alone.
