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
FROM   mart.exec_summary
ORDER  BY snapshot_label;
"""
CHURN_SUMMARY_SQL = """-- BI report: churn flag distribution.
SELECT churn_flag,
       COUNT(*)                  AS customers,
       AVG(days_since_order)     AS avg_days_since_order
FROM   mart.churn_flags
GROUP  BY churn_flag
ORDER  BY churn_flag;
"""
SHIPPING_SLA_SQL = """-- BI report: carrier SLA as published.
SELECT carrier, shipments, delivered, in_flight,
       avg_hours_to_deliver, max_hours_to_deliver, on_time_96h
FROM   mart.shipping_sla
ORDER  BY carrier;
"""
HEALTH_SQL = """SELECT "schema", "table", tbl_rows, stats_off AS statistics_staleness_pct
FROM svv_table_info
WHERE "schema" = 'mart'
ORDER BY "table";"""

QUERIES = {
    "/executive-summary": EXEC_SUMMARY_SQL,
    "/churn-summary": CHURN_SUMMARY_SQL,
    "/shipping-sla": SHIPPING_SLA_SQL,
    "/health": HEALTH_SQL,
}


def connect():
    import redshift_connector

    return redshift_connector.connect(
        host=os.environ.get("REDSHIFT_HOST", "retail-dw.482716309154.us-west-2.redshift-serverless.amazonaws.com"),
        port=int(os.environ.get("REDSHIFT_PORT", "5439")),
        database=os.environ.get("REDSHIFT_DATABASE", "mig_redshift_src"),
        user=os.environ["REDSHIFT_USER"],
        password=os.environ["REDSHIFT_PASSWORD"],
        ssl=True,
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
