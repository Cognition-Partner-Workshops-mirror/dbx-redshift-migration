# dbx-redshift-migration

A reusable **Redshift → Databricks SQL** migration demo. This repository holds a
self-contained "before" estate — a retail order-analytics warehouse written in
real Redshift SQL — plus the kit to migrate it to Databricks SQL with parallel
Devin sessions, each validating on its own VM against committed golden outputs
captured from the live Redshift estate.

`main` is the pristine "before" estate. Converted Databricks SQL lands on
migration branches (`migration-run-N` integration branch, `unit/<name>` child
branches); `databricks/units/<unit>/` starts empty and is filled by the
migration sessions. Nothing under `legacy/`, `golden/`, `data/seed/` or
`validation/` may be edited by a migration session — see `AGENTS.md`.

## The estate

- `legacy/redshift/00_foundation/` — schemas `core` + `mart`, ten `core.*`
  tables (DISTKEY/SORTKEY/DISTSTYLE/ENCODE, CHAR, SUPER) and two SQL
  UDFs (`f_fiscal_qtr`, `f_clean_phone`). Primary keys are explicit `BIGINT`
  keys — Redshift `IDENTITY` columns can't take explicit seeded ids on INSERT.
- `legacy/redshift/units/<unit>/` — 18 migration units, each with `etl.sql`
  (builds `mart.<unit>` using Redshift idioms) and `report.sql` (a BI query
  over the mart). `finance_export` also has `export.sql` (UNLOAD).
- `legacy/redshift/99_orchestration/` — `refresh_schedule.yaml` (legacy nightly
  job order/dependencies) and the `exec_summary` mart that joins four marts.
- `data/seed/` — deterministic generator (`random.Random(42)`, anchored to
  END_DATE = 2025-12-31) and the committed seed CSVs it produces.
- `golden/` — captured outputs of every unit run on Redshift
  `mig_redshift_src`, with `PROVENANCE.json`.
- `.migration/units.yaml` — the manifest: waves, unit files, reads/writes,
  outputs, keys, expected Lakebridge outcome.

The units deliberately exercise constructs that migrate unevenly: CHAR
padding, NUMERIC result scale, `GROUPING SETS`, `LISTAGG ... WITHIN GROUP`,
`DATEDIFF(hour)` boundary counting, `CONVERT_TIMEZONE`, `RATIO_TO_REPORT`,
`NTILE`, `MEDIAN`/`PERCENTILE_CONT`, `DECODE`/`NVL`/`NVL2`, integer division,
SUPER/PartiQL navigation, plpgsql procedures, TEMP tables and UNLOAD. Each
unit's *expected* Lakebridge outcome (clean / mismatch / rejected) is a
hypothesis for the demo narrative, never a fact; actuals are recorded in
`.migration/coverage.md`.

## Databricks layout

- Catalogs: `mig_redshift_dev` (dev/migration runs, env `MIG_CATALOG`) and
  `mig_redshift` (accepted/prod, deployed only from merged PRs via the DAB
  `prod` target). Both tagged `demo_type=redshift`,
  `source_repo=dbx-redshift-migration`.
- Medallion schemas inside each catalog: `bronze` (managed volume `raw`
  holding the seed CSVs as the "historical extract", raw Delta tables loaded
  as-is), `silver` (typed tables mirroring the Redshift core layer), `gold`
  (unit marts). Converted SQL references unqualified `silver.x` / `gold.x`;
  the harness sets the catalog.
- Goldens stay in git (`golden/`): validation compares on the VM — no golden
  tables are created in Databricks.
- The DAB `warehouse_id` variable has no default: pass
  `databricks bundle deploy --var warehouse_id=<id>` or set env
  `BUNDLE_VAR_warehouse_id`.

## Demo flow

1. An orchestrator session runs Lakebridge per-unit transpile
   (commands in `demo-ops/ORCHESTRATOR_PROMPT.md`), commits the drafts to
   `migration-run-N`, and runs
   wave 0 (`foundation`: bronze from `/Volumes/<catalog>/bronze/raw`, then
   typed `silver.*`). A foundation can alternatively be pre-built by its own
   session using `demo-ops/FOUNDATION_PROMPT.md` before the orchestrator runs.
2. Waves 1a (5 units) and 1b (13 units) fan out to parallel child sessions,
   one unit each: start from the Lakebridge draft if present, write only
   `databricks/units/<unit>/{etl,report}.sql`, run `make validate UNIT=<unit>`
   until PASS.
3. Wave 2 converts the orchestration (`exec_summary` + Lakeflow job from
   `refresh_schedule.yaml`).
4. A verifier session re-runs `make validate` for every merged unit.

Recon mode is **golden snapshot**: each VM compares its Databricks results
against `golden/` on disk — no live federation into Redshift (see
`.migration/00_context.md`).

## Quickstart

```bash
pip install -r requirements.txt

# one-time, operator-run, against Redshift only:
export REDSHIFT_HOST=... REDSHIFT_PORT=5439 REDSHIFT_USER=... REDSHIFT_PASSWORD=...
make legacy-all          # creates mig_redshift_src, loads seed, builds marts, captures goldens

# per migration session:
export DATABRICKS_HOST=... DATABRICKS_TOKEN=... DATABRICKS_WAREHOUSE_ID=...
make db-setup            # catalog mig_redshift_dev, schemas, volume, seed upload
make validate UNIT=daily_revenue
make check               # ruff + pytest + manifest checks (no secrets needed)
```

## Environment variables

| Variable | Purpose |
| --- | --- |
| `REDSHIFT_HOST` / `REDSHIFT_PORT` / `REDSHIFT_USER` / `REDSHIFT_PASSWORD` | Redshift Serverless connection (golden capture only) |
| `REDSHIFT_DATABASE` | source database (default `mig_redshift_src`) |
| `REDSHIFT_ADMIN_DATABASE` | database to connect to for `CREATE DATABASE` (default `dev`) |
| `DATABRICKS_HOST` / `DATABRICKS_TOKEN` or `DATABRICKS_CONFIG_PROFILE` | Databricks auth (standard SDK config) |
| `DATABRICKS_WAREHOUSE_ID` | SQL warehouse for validation |
| `MIG_CATALOG` | dev catalog (default `mig_redshift_dev`; prod is `mig_redshift`) |

See `.env.example` for placeholders.

## Make targets

| Target | What it does |
| --- | --- |
| `make check` | `ruff check .` + `pytest` + `python tools/check_manifest.py` |
| `make seed` | regenerate `data/seed/csv/` deterministically |
| `make db-setup` / `make db-reset` | create (or fully reset) the dev catalog via `tools/databricks_setup.py` |
| `make validate UNIT=x` | build the unit's converted SQL on Databricks and compare all outputs to goldens |
| `make validate-all` | validate every unit that has converted `etl.sql` |
| `make legacy-all` | one-time Redshift setup + build + golden capture (operator only) |
| `make capture-golden` | re-capture goldens from Redshift |
