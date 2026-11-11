"""Live checks for demo_redshift.customer_360: grains, invariants and the certified KPI values.

Run with `make verify` (uses the DEFAULT Databricks CLI profile).
"""

import os
import sys
from decimal import Decimal

from databricks.sdk import WorkspaceClient

WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "6dc4b80538621b7b")
S = "demo_redshift.customer_360"

CHECKS = [
    ("order_facts grain", f"SELECT COUNT(*), COUNT(DISTINCT order_id) FROM {S}.order_facts", ["20000", "20000"]),
    ("customer_profile grain", f"SELECT COUNT(*), COUNT(DISTINCT customer_id) FROM {S}.customer_profile", ["1500", "1500"]),
    ("customer_health grain", f"SELECT COUNT(*), COUNT(DISTINCT customer_id) FROM {S}.customer_health", ["1500", "1500"]),
    ("net <= gross on every order", f"SELECT COUNT_IF(net_amount > gross_amount) FROM {S}.order_facts", ["0"]),
    ("net only on completed orders", f"SELECT COUNT_IF(NOT is_completed AND net_amount <> 0) FROM {S}.order_facts", ["0"]),
    ("no negative delivery hours", f"SELECT COUNT_IF(hours_to_deliver < 0) FROM {S}.order_facts", ["0"]),
    ("Feb is fiscal Q1", f"SELECT DISTINCT fiscal_quarter FROM {S}.order_facts WHERE month(order_date) = 2", ["Q1"]),
    ("profile LTV ties to order facts",
     f"SELECT (SELECT SUM(net_ltv) FROM {S}.customer_profile) = (SELECT SUM(net_amount) FROM {S}.order_facts)",
     ["true"]),
    ("revenue KPIs",
     (f"SELECT MEASURE(net_revenue), MEASURE(gross_revenue), MEASURE(completed_orders), ROUND(MEASURE(aov), 2), "
     f"ROUND(MEASURE(return_rate), 3), ROUND(MEASURE(on_time_delivery_pct), 3) FROM {S}.revenue_metrics"),
     ["6278577.77", "10543825.25", "11902", "527.52", "0.050", "0.683"]),
    ("health KPIs",
     (f"SELECT ROUND(MEASURE(avg_net_ltv), 2), MEASURE(revenue_at_risk), MEASURE(customers) "
     f"FROM {S}.customer_health_metrics"),
     ["4637.06", "1327164.70", "1500"]),
    ("segment mix",
     (f"SELECT array_join(array_sort(collect_list(segment || '=' || n)), ',') FROM "
     f"(SELECT segment, MEASURE(customers) AS n FROM {S}.customer_health_metrics GROUP BY segment)"),
     ["At risk=248,Champion=272,Hibernating=294,Loyal=292,Never ordered=146,Promising=248"]),
    ("top regional revenue at risk",
     (f"SELECT region, MEASURE(revenue_at_risk) AS r FROM {S}.customer_health_metrics "
     f"GROUP BY region ORDER BY r DESC LIMIT 1"),
     ["SOTH", "292691.46"]),
    ("customer 342",
     f"SELECT customer_name, region, segment, net_ltv, aov, recency_days FROM {S}.customer_health WHERE customer_id = 342",
     ["Emerson Silva", "WEST", "At risk", "7867.09", "715.19", "50"]),
    ("legacy vs certified rows", f"SELECT COUNT(*) FROM {S}.legacy_vs_certified", ["5"]),
]


def _norm(v):
    try:
        return str(Decimal(v).normalize()) if v not in (None, "true", "false") else v
    except ArithmeticError:
        return v


def run(w, sql):
    r = w.statement_execution.execute_statement(warehouse_id=WAREHOUSE_ID, statement=sql, wait_timeout="50s")
    if r.status.state.value != "SUCCEEDED":
        raise RuntimeError(r.status.error.message if r.status.error else r.status.state.value)
    return (r.result.data_array or [[]])[0]


def main():
    w = WorkspaceClient()
    failed = 0
    for name, sql, expected in CHECKS:
        got = run(w, sql)
        ok = [_norm(g) for g in got] == [_norm(e) for e in expected]
        failed += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {got}" + ("" if ok else f" (expected {expected})"))
    print(f"{len(CHECKS) - failed}/{len(CHECKS)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
