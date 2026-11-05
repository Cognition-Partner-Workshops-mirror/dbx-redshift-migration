# Decision log

| id | date | decision | by | status |
| --- | --- | --- | --- | --- |
| D-001 | 2026-09-30 | Recon oracle = golden snapshot captured from Redshift `mig_redshift_src`; tolerances per `validation/tolerances.yaml` | lead | proposed |
| D-002 | 2026-11-05 | Run `migration-run-2` uses only new catalog `demo_redshift` with profile `DEFAULT`; overrides environment/repo default catalog restrictions. Do not access `mig_redshift_dev` or deploy prod. No golden, tolerance, or scope changes. | Mason, explicit session approval | approved |
| D-003 | 2026-11-05 | Orchestrator may integrate child PRs into `migration-run-2` after checks and review. Exception to self-merge guardrail applies only to this run branch, never `main`. | Mason, explicit session approval | approved |
