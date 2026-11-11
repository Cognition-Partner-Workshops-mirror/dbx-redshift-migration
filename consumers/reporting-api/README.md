# Retail Reporting API

Run `python consumers/reporting-api/service.py`. Configure `REDSHIFT_HOST`, `REDSHIFT_PORT`, `REDSHIFT_DATABASE`, `REDSHIFT_USER`, and `REDSHIFT_PASSWORD` in the service environment. Credentials are supplied by the deployment secret store. TLS is required.

GET routes: `/executive-summary`, `/churn-summary`, `/shipping-sla`, `/health`. The health route returns the mart table inventory and estimated row counts used by the warehouse freshness monitor. Warehouse errors return HTTP 503.
