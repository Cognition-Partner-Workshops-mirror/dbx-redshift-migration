"""Retail reporting HTTP service."""
import datetime as dt
import decimal
import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)

EXEC_SUMMARY_SQL = """-- BI report: the exec summary as published.
SELECT snapshot_label, as_of_date, total_revenue, total_orders,
       avg_customer_ltv, overall_return_pct, avg_ship_hours
FROM   gold.exec_summary
ORDER  BY snapshot_label;
"""
CHURN_SUMMARY_SQL = """-- BI report: churn flag distribution.
SELECT churn_flag,
       COUNT(*)                  AS customers,
       CAST(AVG(days_since_order) AS BIGINT)     AS avg_days_since_order
FROM   gold.churn_flags
GROUP  BY churn_flag
ORDER  BY churn_flag;
"""
SHIPPING_SLA_SQL = """-- BI report: carrier SLA as published.
SELECT carrier, shipments, delivered, in_flight,
       avg_hours_to_deliver, max_hours_to_deliver, on_time_96h
FROM   gold.shipping_sla
ORDER  BY carrier;
"""
HEALTH_SQL = """SELECT table_schema, table_name, last_altered
FROM demo_redshift.information_schema.tables
WHERE table_schema = 'gold'
ORDER BY table_name;"""

QUERIES = {
    "/executive-summary": EXEC_SUMMARY_SQL,
    "/churn-summary": CHURN_SUMMARY_SQL,
    "/shipping-sla": SHIPPING_SLA_SQL,
    "/health": HEALTH_SQL,
}


def connect():
    from databricks.sdk.core import Config

    from databricks import sql

    config = Config()
    return sql.connect(
        server_hostname=config.host.removeprefix("https://").rstrip("/"),
        http_path=os.environ.get(
            "DATABRICKS_HTTP_PATH",
            f"/sql/1.0/warehouses/{os.environ.get('DATABRICKS_WAREHOUSE_ID', '6dc4b80538621b7b')}",
        ),
        credentials_provider=lambda: config.authenticate,
        catalog="demo_redshift",
        schema="gold",
    )


def fetch(path, connection_factory=connect):
    sql = QUERIES[path]
    connection = connection_factory()
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(sql)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()
    finally:
        connection.close()


def encode(value):
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    raise TypeError(type(value).__name__)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in QUERIES:
            self.send_error(404)
            return
        try:
            body = json.dumps(fetch(self.path), default=encode).encode()
        except Exception:
            logger.exception("Warehouse request failed")
            self.send_error(503, "Warehouse unavailable")
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Handler).serve_forever()
