# Migration session guardrails

These rules apply to every Devin session working in this repository.

Run-specific approved exceptions for `migration-run-2` are recorded in
`.migration/06_decisions.md`: use only catalog `demo_redshift` via profile
`DEFAULT` (never access `mig_redshift_dev`). Mason's latest instruction
supersedes the earlier merge exception: do not merge any PR or branch.
Start from main and leave all child PRs open for human review. Full-run
verification may assemble file copies in a disposable checkout, without
merging or committing child contributions into the run branch.

- `legacy/`, `golden/`, `data/seed/` and `validation/` are **read-only** for
  migration sessions. Reconciliation failures are fixed in converted code only.
- One unit per child session. A child writes only `databricks/units/<unit>/`
  (`etl.sql`, `report.sql`), its evidence file `.migration/evidence/<unit>.json`
  (produced by `make validate`), and one row in `.migration/coverage.md`.
- Never edit goldens, tolerances, or legacy SQL. Tolerance or scope changes
  happen only with a human-approved row recorded in `.migration/06_decisions.md`.
- Write only to catalogs listed in `.migration/allowed_targets.json`
  (`demo_redshift` for this isolated run). Never create or modify objects
  in any other catalog; do not access the prior dev catalog.
- Never print, commit or paste tokens or passwords; reference env var names
  only.
- Never merge to `main`. Child PRs target `migration-run-N`; the orchestrator
  owns the run branch. Devin does not approve or merge its own PRs.
- Never run `tools/legacy_redshift.py` (operator-only golden capture).
  Redshift `mig_redshift_src` is read-only: the orchestrator may run SELECT /
  catalog queries for discovery; no session writes to it, and validation
  always compares to `golden/`, never live Redshift.
- Converted SQL reads `silver.*` and writes `gold.*` (Redshift `core.x` →
  `silver.x`, `mart.x` → `gold.x`); `bronze.*` is written only by
  `foundation`.
- All logic must be deterministic: no `GETDATE()`/`CURRENT_DATE`/`SYSDATE`/
  `RANDOM()` in outputs; "as of" is the literal `2025-12-31`.
