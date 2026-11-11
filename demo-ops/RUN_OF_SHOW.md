# Consumer cutover

- Setup: land the reviewed baseline on `consumer-cutover` (never main), tag that
  baseline commit `consumer-cutover-baseline` and push the tag. Set
  `DATABRICKS_CONFIG_PROFILE=DEFAULT`, `DATABRICKS_WAREHOUSE_ID` and
  `MIG_CATALOG=demo_redshift`. Run `make consumer-setup`. Deploy the dashboard
  bundle separately after approval; setup does not deploy it.
- Run: hand `demo-ops/CONSUMER_CUTOVER_PROMPT.md` to a fresh session based on
  `consumer-cutover`. Watch the naive/current matrices and the latest-run
  dashboard. Keep the resulting PR open for review.
- Reset (operator only): switch to an operator branch, export `GH_TOKEN`, run
  `make consumer-reset ARGS=--dry-run`, review its exact PR/branch actions, then
  `make consumer-reset`. This closes PRs targeting consumer-cutover, deletes
  their same-repository heads, resets that branch to the baseline tag and clears
  only `demo_redshift.consumer_parity.results`. It does not reset your working
  tree; use a fresh checkout for the next run.

# Run of show

Reusable checklist for one migration demo run.

## Pre-flight (operator)

- [ ] `pip install -r requirements.txt`
- [ ] Goldens present: `python tools/check_manifest.py` passes on `main`.
- [ ] If re-capturing: set `REDSHIFT_*` env vars, `make legacy-all` (Redshift
      only — never in migration sessions).
- [ ] `databricks labs install lakebridge && databricks labs lakebridge install-transpile`

## Run

- [ ] Orchestrator session starts on `migration-run-N` (see
      `ORCHESTRATOR_PROMPT.md`).
- [ ] `make db-setup` — dev catalog `mig_redshift_dev`, schemas, volume, seed upload.
- [ ] Lakebridge analyze + per-unit transpile; drafts committed to run branch.
- [ ] Wave 0: `foundation` (own session via `demo-ops/FOUNDATION_PROMPT.md`,
      or orchestrator): bronze from `/Volumes/<catalog>/bronze/raw`, then
      `silver.*`, validates.
- [ ] Wave 1a: 5 parallel child sessions (one unit each).
- [ ] Wave 1b: 13 parallel child sessions.
- [ ] Wave 2: orchestration (`exec_summary` + Lakeflow job from
      `refresh_schedule.yaml`).
- [ ] Verifier session: `make validate-all`, summary table.
- [ ] Review PRs; merge run branch into `main` only by a human.

## Talking points

- Golden-snapshot recon: each child validates hermetically on its own VM.
- `expected_lakebridge` is a hypothesis — `.migration/coverage.md` is where
  observed outcomes and fix patterns accumulate (review feedback updates the
  playbook).
- Constructs that hurt: CHAR padding, NUMERIC scale, hour-boundary DATEDIFF,
  DECODE/NVL2, plpgsql procedures, SUPER navigation, UNLOAD.
