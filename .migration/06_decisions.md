# Decision log

| id | date | decision | by | status |
| --- | --- | --- | --- | --- |
| D-001 | 2026-09-30 | Recon oracle = golden snapshot captured from Redshift `mig_redshift_src`; tolerances per `validation/tolerances.yaml` | lead | proposed |
| D-002 | 2026-11-19 | Customer 360 demo may write to `demo_redshift.customer_360` via its own bundle in `products/customer_360/`. Deliver via one PR targeting `main` for a human to merge. | Mason Batchelor | approved |
