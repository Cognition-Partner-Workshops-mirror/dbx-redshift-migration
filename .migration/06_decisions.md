# Decision log

| id | date | decision | by | status |
| --- | --- | --- | --- | --- |
| D-001 | 2026-09-30 | Recon oracle = golden snapshot captured from Redshift `mig_redshift_src`; tolerances per `validation/tolerances.yaml` | lead | proposed |
| D-002 | 2026-11-11 | Customer 360 data product: add `demo_redshift` to `allowed_targets.json`; new product schema `demo_redshift.customer_360` (reads `demo_redshift.silver`/`gold`, never writes them); new folder `products/customer_360/` with its own bundle (build job, dashboard, app) plus a Genie space; lands as one PR to `main` that the human merges | Mason | approved |
