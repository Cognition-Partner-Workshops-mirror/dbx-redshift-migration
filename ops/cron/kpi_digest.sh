#!/usr/bin/env bash
set -euo pipefail
export PGHOST="${REDSHIFT_HOST:-retail-dw.482716309154.us-west-2.redshift-serverless.amazonaws.com}"
export PGPORT="${REDSHIFT_PORT:-5439}"
export PGDATABASE="${REDSHIFT_DATABASE:-mig_redshift_src}"
export PGUSER="${REDSHIFT_USER:?REDSHIFT_USER is required}"
export PGPASSWORD="${REDSHIFT_PASSWORD:?REDSHIFT_PASSWORD is required}"
export PGSSLMODE=require
psql --no-psqlrc --csv --set ON_ERROR_STOP=1 <<'RETURNS_RATE_SQL'
-- BI report: returns rate as published.
SELECT category, sold_qty, returned_qty, return_rate_int, return_pct
FROM   mart.returns_rate
ORDER  BY return_pct DESC, category;
RETURNS_RATE_SQL
