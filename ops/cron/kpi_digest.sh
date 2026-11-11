#!/usr/bin/env bash
set -euo pipefail
# SDK unified authentication (profile or deployment environment); no stored secrets.
: "${DATABRICKS_WAREHOUSE_ID:?DATABRICKS_WAREHOUSE_ID is required}"
python -c '
import csv
import os
import sys
from urllib.parse import urlparse
from databricks import sql
from databricks.sdk.core import Config

config = Config()
with sql.connect(
    server_hostname=urlparse(config.host).hostname,
    http_path="/sql/1.0/warehouses/" + os.environ["DATABRICKS_WAREHOUSE_ID"],
    credentials_provider=lambda: config.authenticate,
    catalog="demo_redshift", schema="gold", user_agent_entry="Cognition_Devin",
) as connection:
    with connection.cursor() as cursor:
        cursor.execute(sys.stdin.read())
        writer = csv.writer(sys.stdout, lineterminator="\n")
        writer.writerow([c[0] for c in cursor.description])
        writer.writerows(cursor.fetchall())
' <<'RETURNS_RATE_SQL'
-- BI report: returns rate as published.
SELECT category, sold_qty, returned_qty, return_rate_int, return_pct
FROM   gold.returns_rate
ORDER  BY return_pct DESC, category;
RETURNS_RATE_SQL
