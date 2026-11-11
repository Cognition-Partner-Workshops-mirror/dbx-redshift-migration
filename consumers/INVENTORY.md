# Retail downstream inventory

| Owner / surface | File | Query locator | Source / reference | Migration |
|---|---|---|---|---|
| Tableau Executive | consumers/tableau/Retail Executive.twb | daily_revenue | daily_revenue / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Tableau Executive | consumers/tableau/Retail Executive.twb | category_mix | category_mix / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Tableau Executive | consumers/tableau/Retail Executive.twb | customer_ltv | customer_ltv / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Tableau Executive | consumers/tableau/Retail Executive.twb | store_weekly | store_weekly / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Power BI Finance | consumers/powerbi/Finance Reporting.SemanticModel/definition/tables/finance_export.tmdl | finance_export | finance_export / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Power BI Finance | consumers/powerbi/Finance Reporting.SemanticModel/definition/tables/payment_mix.tmdl | payment_mix | payment_mix / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Power BI Finance | consumers/powerbi/Finance Reporting.SemanticModel/definition/tables/promo_lift.tmdl | promo_lift | promo_lift / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Reporting API | consumers/reporting-api/service.py | EXEC_SUMMARY_SQL | orchestration / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Reporting API | consumers/reporting-api/service.py | CHURN_SUMMARY_SQL | churn_flags / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Reporting API | consumers/reporting-api/service.py | SHIPPING_SLA_SQL | shipping_sla / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Reporting API | consumers/reporting-api/service.py | HEALTH_SQL | svv_table_info (operational) | Use Unity Catalog table inventory and row-count freshness probe |
| Customer Analytics | consumers/notebooks/customer_segments.ipynb | rfm_segments | rfm_segments / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Customer Analytics | consumers/notebooks/customer_segments.ipynb | cohort_retention | cohort_retention / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Finance Reconciliation | consumers/notebooks/finance_reconciliation.ipynb | finance_monthly / export_path | finance_export / finance_monthly | Replace S3 with monthly UC volume CSV |
| KPI Digest | ops/cron/kpi_digest.sh | RETURNS_RATE_SQL | returns_rate / report | Databricks connection, gold/silver SQL; preserve published aggregate types |
| Excel Geography | shared/excel/Geo Rollup.odc | Geo Rollup | geo_rollup / report | Databricks connection, gold/silver SQL; preserve published aggregate types |

Connections are embedded in TWB, shared Power Query expressions, Python connection factories, notebook setup, shell execution, and ODBC metadata. Credentials remain environment-provided or supplied through each BI client's credential store. No write access to warehouse source or published tables is required.
