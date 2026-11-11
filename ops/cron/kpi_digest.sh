#!/usr/bin/env bash
set -euo pipefail
query="$(cat <<'RETURNS_RATE_SQL'
-- BI report: returns rate as published.
SELECT category, sold_qty, returned_qty, return_rate_int, return_pct
FROM   gold.returns_rate
ORDER  BY return_pct DESC, category;
RETURNS_RATE_SQL
)"
python - "$query" <<'PY'
import csv
import os
import sys
from databricks import sql
from databricks.sdk.core import Config

config = Config()
with sql.connect(
    server_hostname=config.host.removeprefix("https://").rstrip("/"),
    http_path=os.environ.get("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/6dc4b80538621b7b"),
    credentials_provider=lambda: config.authenticate,
    catalog="demo_redshift", schema="gold",
) as connection:
    with connection.cursor() as cursor:
        cursor.execute(sys.argv[1])
        writer = csv.writer(sys.stdout)
        writer.writerow(column[0] for column in cursor.description)
        writer.writerows(cursor.fetchall())
PY
