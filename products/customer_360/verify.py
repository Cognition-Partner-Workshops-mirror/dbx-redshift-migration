"""Verify the live Customer 360 data and the dashboard's actual widget queries."""

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from time import monotonic, sleep

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementParameterListItem, StatementState

CATALOG = "demo_redshift"
SCHEMA = "customer_360"
DASHBOARD = Path(__file__).parent / "dashboard" / "customer-health.lvdash.json"
SEGMENTS = {
    "At risk": 248,
    "Champion": 272,
    "Hibernating": 294,
    "Loyal": 292,
    "Never ordered": 146,
    "Promising": 248,
}


def query(workspace, warehouse, statement, parameters=None):
    response = workspace.statement_execution.execute_statement(
        statement, warehouse, catalog=CATALOG, schema=SCHEMA, parameters=parameters, wait_timeout="30s"
    )
    deadline = monotonic() + 120
    while response.status.state in (StatementState.PENDING, StatementState.RUNNING) and monotonic() < deadline:
        sleep(2)
        response = workspace.statement_execution.get_statement(response.statement_id)
    if response.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(f"{response.status}: {statement}")
    return response.result.data_array or []


def equal(actual, expected):
    if actual != expected:
        raise AssertionError(f"Expected {expected!r}, got {actual!r}")


def verify_data(run):
    for table, key, size in (
        ("order_facts", "order_id", 20000),
        ("customer_profile", "customer_id", 1500),
        ("customer_health", "customer_id", 1500),
    ):
        equal(run(f"SELECT COUNT(*), COUNT(DISTINCT {key}) FROM {table}"), [[str(size), str(size)]])
    equal(run("""
        SELECT COUNT(*) FROM order_facts
        WHERE net_amount <> IF(status = 'complete', gross_amount, 0)
           OR fiscal_year <> YEAR(ADD_MONTHS(order_date, -1))
           OR fiscal_quarter <> QUARTER(ADD_MONTHS(order_date, -1))
           OR hours_to_deliver < 0
           OR NOT (delivered_within_96h <=> (hours_to_deliver <= 96))
    """), [["0"]])
    equal(run("""
        SELECT COUNT(*) FROM customer_health
        WHERE as_of_date <> DATE '2025-12-31'
           OR (segment = 'Never ordered') <> (completed_orders = 0)
           OR NOT (revenue_at_risk <=> IF(segment = 'At risk', net_ltv, 0))
           OR (completed_orders = 0 AND COALESCE(r_score, f_score, m_score, recency_days) IS NOT NULL)
    """), [["0"]])
    equal(run("""
        SELECT CAST(ROUND(MEASURE(net_revenue), 2) AS DECIMAL(18,2)),
               CAST(MEASURE(leakage) AS DECIMAL(18,2)), MEASURE(completed_orders),
               CAST(ROUND(MEASURE(aov), 2) AS DECIMAL(18,2)),
               ROUND(MEASURE(return_rate), 4), ROUND(MEASURE(on_time_delivery_pct), 4)
        FROM revenue_metrics
    """), [["6278577.77", "4265247.48", "11902", "527.52", "0.0501", "0.6835"]])
    equal(run("""
        SELECT CAST(ROUND(MEASURE(avg_net_ltv), 2) AS DECIMAL(18,2)), MEASURE(revenue_at_risk)
        FROM customer_health_metrics
    """), [["4637.06", "1327164.70"]])
    equal(
        {name: int(count) for name, count in run(
            "SELECT segment, MEASURE(customers) FROM customer_health_metrics GROUP BY segment"
        )},
        SEGMENTS,
    )
    equal(run("""
        SELECT region, MEASURE(revenue_at_risk) AS risk FROM customer_health_metrics
        GROUP BY region ORDER BY risk DESC LIMIT 1
    """), [["SOTH", "292691.46"]])
    equal(run("""
        SELECT first_name, last_name, p.region, h.segment, p.net_ltv, p.aov, h.recency_days
        FROM customer_profile p JOIN customer_health h USING (customer_id) WHERE customer_id = 342
    """), [["Emerson", "Silva", "WEST", "At risk", "7867.09", "715.19", "50"]])
    equal(
        [(Decimal(legacy), Decimal(certified)) for legacy, certified in run(
            "SELECT legacy_value, certified_value FROM legacy_vs_certified ORDER BY display_order"
        )],
        [(Decimal(a), Decimal(b)) for a, b in (
            ("10543825.25", "6278577.77"), ("196.1281", "527.5229"), ("7029.21", "4637.0589"),
            ("2692252.78", "1563987.88"), ("0", "5.0138"),
        )],
    )
    print("Certified grains, invariants, seeded KPIs, six segments, regional risk and customer #342 passed.")


def dashboard_queries(dashboard):
    datasets = {dataset["name"]: dataset for dataset in dashboard["datasets"]}
    sample_values = {"fiscal_quarter": ("1", "INT"), "channel": ("web", "STRING"), "region": ("WEST", "STRING")}
    filters = {}
    for page in dashboard["pages"]:
        for tile in page["layout"]:
            widget = tile["widget"]
            if widget.get("spec", {}).get("widgetType") == "filter-multi-select":
                for binding in widget["queries"]:
                    target = binding["query"]
                    filters.setdefault(target["datasetName"], set()).add(target["fields"][0]["name"])

    for page in dashboard["pages"]:
        for tile in page["layout"]:
            widget = tile["widget"]
            for binding in widget.get("queries", []):
                target = binding["query"]
                dataset = datasets[target["datasetName"]]
                source = dataset.get("asset_name")
                if not source:
                    source = f"({''.join(dataset['queryLines'])}) AS dataset"
                expressions = [field["expression"] for field in target["fields"]]
                select = f"SELECT {', '.join(expressions)} FROM {source}"
                groups = [expr for expr in expressions if re.fullmatch(r"`[a-z_]+`", expr)]
                group_sql = f" GROUP BY {', '.join(groups)}" if groups and not target["disaggregated"] else ""
                yield widget["name"], select + group_sql, None
                bound = sorted(filters.get(dataset["name"], ()))
                if bound:
                    where = " AND ".join(f"`{field}` = :{field}" for field in bound)
                    parameters = [
                        StatementParameterListItem(name=field, value=sample_values[field][0], type=sample_values[field][1])
                        for field in bound
                    ]
                    yield f"{widget['name']} (filtered)", f"{select} WHERE {where}{group_sql}", parameters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--dashboard", action="store_true")
    args = parser.parse_args()
    workspace = WorkspaceClient()

    if args.dashboard:
        def check(case):
            name, statement, parameters = case
            rows = query(workspace, args.warehouse, statement, parameters)
            if not rows:
                raise AssertionError(f"{name} returned no rows")
            return name

        payload = json.loads(DASHBOARD.read_text())
        with ThreadPoolExecutor(max_workers=6) as executor:
            for name in executor.map(check, dashboard_queries(payload)):
                print(f"Dashboard SQL passed: {name}")
    else:
        verify_data(lambda statement: query(workspace, args.warehouse, statement))


if __name__ == "__main__":
    main()
