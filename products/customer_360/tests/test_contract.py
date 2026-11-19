import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import yaml
from app import data
from databricks.sdk.service.sql import StatementState
from verify import DASHBOARD, dashboard_queries

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_uses_only_the_published_measures():
    metrics = (ROOT / "sql/02_metrics.sql").read_text()
    definitions = {}
    for name, body in re.findall(r"CREATE OR REPLACE VIEW ([\w.]+)\s+WITH METRICS LANGUAGE YAML AS \$\$(.*?)\$\$",
                                 metrics, flags=re.DOTALL):
        definitions[name] = {measure["name"] for measure in yaml.safe_load(body)["measures"]}
    dashboard = json.loads(DASHBOARD.read_text())
    datasets = {dataset["name"]: dataset for dataset in dashboard["datasets"]}
    for page in dashboard["pages"]:
        for tile in page["layout"]:
            for binding in tile["widget"]["queries"]:
                query = binding["query"]
                source = datasets[query["datasetName"]].get("asset_name")
                for field in query["fields"]:
                    measure = re.fullmatch(r"MEASURE\(`(\w+)`\)", field["expression"])
                    if measure:
                        assert measure.group(1) in definitions[source]

    filtered = {name: [parameter.name for parameter in params]
                for name, _, params in dashboard_queries(dashboard) if params}
    assert filtered["net_revenue (filtered)"] == ["channel", "fiscal_quarter", "region"]
    assert filtered["revenue_at_risk (filtered)"] == ["region"]


def test_genie_serialized_space_contract():
    space = json.loads((ROOT / "genie/space.json").read_text())
    samples = space["config"]["sample_questions"]
    examples = space["instructions"]["example_question_sqls"]
    instructions = space["instructions"]["text_instructions"]
    assert (len(samples), len(examples), len(instructions)) == (8, 4, 1)
    ids = [item["id"] for item in samples + examples + instructions]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch("[0-9a-f]{32}", identifier) for identifier in ids)
    assert [item["identifier"] for item in space["data_sources"]["tables"]] == sorted(
        f"demo_redshift.customer_360.{name}"
        for name in ["customer_health", "customer_health_metrics", "customer_profile", "order_facts", "revenue_metrics"]
    )


def test_customer_search_binds_input_and_returns_named_columns():
    workspace = Mock()
    workspace.statement_execution.execute_statement.return_value = SimpleNamespace(
        status=SimpleNamespace(state=StatementState.SUCCEEDED),
        manifest=SimpleNamespace(schema=SimpleNamespace(columns=[SimpleNamespace(name="customer_id")])),
        result=SimpleNamespace(data_array=[["342"]]),
    )
    term = "O'Brien"
    assert data.query(workspace, "warehouse", data.SEARCH, term=term) == [{"customer_id": "342"}]
    args, kwargs = workspace.statement_execution.execute_statement.call_args
    assert args == (data.SEARCH, "warehouse")
    assert term not in args[0]
    assert kwargs["parameters"][0].as_dict() == {"name": "term", "type": "STRING", "value": term}


def test_lookup_order_query_uses_date_and_id_tiebreaker():
    assert "WHERE customer_id = :customer_id" in data.ORDERS
    assert "ORDER BY order_ts DESC, order_id DESC\nLIMIT 10" in data.ORDERS
