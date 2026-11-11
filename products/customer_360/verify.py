"""Read-only live product acceptance queries and grain/empty-case checks."""
import json
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState


def query(client, sql):
    response = client.statement_execution.execute_statement(
        warehouse_id="6dc4b80538621b7b", statement=sql, wait_timeout="50s"
    )
    while response.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(1)
        response = client.statement_execution.get_statement(response.statement_id)
    if response.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(response.status.as_dict())
    columns = [c.name for c in response.manifest.schema.columns]
    rows = response.result.data_array or []
    print(json.dumps({"columns": columns, "rows": rows}, indent=2))
    return rows


def main():
    client = WorkspaceClient()
    prefix = "demo_redshift.customer_360."
    for table in ("order_facts", "customer_profile", "customer_health"):
        rows = query(client, f"SELECT '{table}' AS table_name, COUNT(*) AS rows, "
                     f"COUNT(DISTINCT {('order_id' if table == 'order_facts' else 'customer_id')}) "
                     f"AS distinct_ids FROM {prefix}{table}")
        assert rows[0][1] == rows[0][2], f"Duplicate grain: {table}"
    query(client, f"SELECT * FROM {prefix}legacy_vs_certified ORDER BY kpi")
    query(client, f"SELECT order_month, MEASURE(net_revenue), MEASURE(gross_revenue), "
          f"MEASURE(aov) FROM {prefix}revenue_metrics GROUP BY ALL ORDER BY 1")
    query(client, f"SELECT health_segment, MEASURE(customers) FROM "
          f"{prefix}customer_health_metrics GROUP BY ALL ORDER BY 1")
    rows = query(client, f"SELECT SUM(net_amount), "
                 f"TRY_DIVIDE(SUM(net_amount), COUNT_IF(status = 'complete')) "
                 f"FROM {prefix}order_facts")
    assert abs(float(rows[0][0]) - 6278578) < 1
    assert abs(float(rows[0][1]) - 527.52) < 0.01
    rows = query(client, f"SELECT COUNT(*) FROM {prefix}order_facts "
                 "WHERE (status <> 'complete' AND net_amount <> 0) OR region <> RTRIM(region)")
    assert rows == [["0"]]
    rows = query(client, f"SELECT COUNT(*) FROM {prefix}customer_health "
                 "WHERE (frequency = 0 AND (r_tile IS NOT NULL OR recency_days IS NOT NULL "
                 "OR health_segment <> 'Never ordered')) "
                 "OR (r_tile <= 2 AND f_tile >= 3 AND health_segment <> 'At risk')")
    assert rows == [["0"]]
    rows = query(client, f"SELECT COUNT(*) FROM {prefix}customer_profile "
                 "WHERE completed_orders = 0 AND (aov IS NOT NULL OR net_ltv <> 0)")
    assert rows == [["0"]]
    rows = query(client, f"SELECT MEASURE(aov) FROM {prefix}revenue_metrics WHERE status = 'cancelled'")
    assert rows == [[None]], "Zero completed orders must yield NULL AOV"
    rows = query(client, f"SELECT MEASURE(aov) FROM {prefix}revenue_metrics WHERE 1=0")
    assert rows in ([], [[None]]), "Empty scope must not divide by zero"
    print("PASS: product grain, recognition, RFM precedence, zero/empty denominators and sanity checks")


if __name__ == "__main__":
    main()
