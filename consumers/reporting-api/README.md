# Retail Reporting API

Run `python consumers/reporting-api/service.py`. Install `databricks-sql-connector` and `databricks-sdk`. Configure Databricks unified authentication through `DATABRICKS_CONFIG_PROFILE` or the deployment identity; optionally set `DATABRICKS_HOST` and `DATABRICKS_HTTP_PATH`. Credentials remain in the identity provider or secret store.

GET routes: `/executive-summary`, `/churn-summary`, `/shipping-sla`, `/health`. The health route returns gold table inventory and `last_altered` timestamps from Unity Catalog. Warehouse errors return HTTP 503.
