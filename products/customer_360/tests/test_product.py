"""Offline checks for the Customer 360 product: no Databricks connection needed."""

import json
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from lookup import FOOTER, ORDERS_SQL, escape_dollars, money, search_query

SQL_FILES = sorted((ROOT / "sql").glob("*.sql"))
SCHEMA = "demo_redshift.customer_360"


def test_sql_is_deterministic():
    for f in SQL_FILES:
        text = f.read_text().upper()
        for banned in ("CURRENT_DATE", "NOW()", "RANDOM()", "GETDATE", "SYSDATE", "CURRENT_TIMESTAMP"):
            assert banned not in text, f"{f.name} uses {banned}"
    assert "DATE'2025-12-31'" in (ROOT / "sql/01_tables.sql").read_text()


def test_writes_only_customer_360():
    for f in SQL_FILES:
        for target in re.findall(r"CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|SCHEMA)(?:\s+IF\s+NOT\s+EXISTS)?\s+([\w.]+)", f.read_text(), re.IGNORECASE):
            assert target.startswith(SCHEMA), f"{f.name} writes {target}"


def _metric_yaml():
    text = (ROOT / "sql/02_metrics.sql").read_text()
    return dict(re.findall(r"VIEW\s+([\w.]+).*?\$\$(.*?)\$\$", text, re.DOTALL))


def test_metric_views_have_no_semicolons_and_expected_measures():
    views = _metric_yaml()
    assert set(views) == {f"{SCHEMA}.revenue_metrics", f"{SCHEMA}.customer_health_metrics"}
    for body in views.values():
        assert ";" not in body
    rev = {m["name"] for m in yaml.safe_load(views[f"{SCHEMA}.revenue_metrics"])["measures"]}
    health = {m["name"] for m in yaml.safe_load(views[f"{SCHEMA}.customer_health_metrics"])["measures"]}
    assert {"gross_revenue", "net_revenue", "revenue_leakage", "orders", "completed_orders", "aov", "cancel_rate", "return_rate", "on_time_delivery_pct"} <= rev
    assert {"customers", "active_customers", "repeat_rate", "avg_net_ltv", "total_net_ltv", "revenue_at_risk"} <= health


def test_segment_precedence():
    text = (ROOT / "sql/01_tables.sql").read_text()
    order = [text.index(f"'{s}'") for s in ("Never ordered", "Champion", "At risk", "Loyal", "Hibernating", "Promising")]
    assert order == sorted(order)


def test_dashboard_uses_metric_views_and_has_pages():
    dash = json.loads((ROOT / "dashboards/customer_health_revenue.lvdash.json").read_text())
    names = {d["name"]: d for d in dash["datasets"]}
    assert names["ds_revenue"]["asset_name"] == f"{SCHEMA}.revenue_metrics"
    assert names["ds_health"]["asset_name"] == f"{SCHEMA}.customer_health_metrics"
    assert [p["displayName"] for p in dash["pages"]] == ["Executive overview", "Legacy vs certified"]
    filters = {w["widget"]["name"] for w in dash["pages"][0]["layout"] if w["widget"].get("spec", {}).get("widgetType", "").startswith("filter")}
    assert filters == {"filter_fiscal_quarter", "filter_channel", "filter_region"}
    for page in dash["pages"]:
        for item in page["layout"]:
            w = item["widget"]
            for q in w.get("queries", []):
                assert q["query"]["datasetName"] in names


def test_genie_space():
    space = json.loads((ROOT / "genie/space.json").read_text())
    tables = [t["identifier"] for t in space["data_sources"]["tables"]]
    assert tables == sorted(tables)
    assert {f"{SCHEMA}.{t}" for t in ("revenue_metrics", "customer_health_metrics", "customer_profile", "customer_health", "order_facts")} == set(tables)
    assert len(space["config"]["sample_questions"]) == 8
    assert len(space["instructions"]["example_question_sqls"]) == 4
    assert len(space["instructions"]["text_instructions"]) == 1
    assert "2025-12-31" in "".join(space["instructions"]["text_instructions"][0]["content"])


def test_bundle_resources():
    app = yaml.safe_load((ROOT / "resources/app.yml").read_text())["resources"]["apps"]["customer_lookup"]
    assert app["name"] == "customer-lookup"
    assert {r["name"] for r in app["resources"]} == {"sql-warehouse", "genie-space"}
    dash = yaml.safe_load((ROOT / "resources/dashboard.yml").read_text())["resources"]["dashboards"]["customer_health_revenue"]
    assert dash["display_name"] == "Customer Health & Revenue" and dash["embed_credentials"] is True


def test_app_helpers():
    assert escape_dollars("$1 and $2") == "\\$1 and \\$2"
    assert money(7867.09) == "$7,867.09" and money(None) == "—"
    sql, params = search_query("#342")
    assert params["cid"] == "342" and ":cid" in sql and ":pattern" in sql
    sql, params = search_query("Emerson")
    assert "cid" not in params and params["pattern"] == "%emerson%"
    assert "'" not in sql.split("WHERE", 1)[1]
    assert "ORDER BY order_ts DESC LIMIT 10" in ORDERS_SQL
    assert FOOTER == "Data as of 2025-12-31 · certified customer_360 metrics"
