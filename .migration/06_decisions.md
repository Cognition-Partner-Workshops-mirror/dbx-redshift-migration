# Decision log

| id | date | decision | by | status |
| --- | --- | --- | --- | --- |
| D-001 | 2026-09-30 | Recon oracle = golden snapshot captured from Redshift `mig_redshift_src`; tolerances per `validation/tolerances.yaml` | lead | proposed |
| D-002 | 2026-11-11 | Customer 360 data product may write only `demo_redshift.customer_360` in `demo_redshift`, with code in `products/customer_360/` and PR to main; legacy, gold, goldens, seed and validation remain untouched. Exception to migration-session scope and target guardrails. | Mason | approved |
