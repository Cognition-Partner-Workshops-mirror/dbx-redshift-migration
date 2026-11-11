"""Dashboard contracts and validation failure paths without warehouse access."""
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import verify_dashboard


def dashboard():
    return json.loads((Path(__file__).parent / "dashboards/customer_health_revenue.lvdash.json").read_text())


def test_widget_bindings_and_grid():
    content = dashboard()
    datasets = {d["name"] for d in content["datasets"]}
    for page in content["pages"]:
        assert page["layoutVersion"] == "GRID_V1"
        occupied = set()
        for entry in page["layout"]:
            p = entry["position"]
            for x in range(p["x"], p["x"] + p["width"]):
                for y in range(p["y"], p["y"] + p["height"]):
                    assert (x, y) not in occupied
                    occupied.add((x, y))
            widget = entry["widget"]
            for query in widget.get("queries", []):
                assert query["query"]["datasetName"] in datasets
            if "spec" in widget:
                assert widget["spec"]["frame"]["title"]
                if widget["spec"]["widgetType"].startswith("filter-"):
                    continue
                fields = {f["name"] for f in widget["queries"][0]["query"]["fields"]}

                def check(value, fields=fields):
                    if isinstance(value, dict):
                        if "fieldName" in value:
                            assert value["fieldName"] in fields
                        for v in value.values():
                            check(v)
                    elif isinstance(value, list):
                        for v in value:
                            check(v)

                check(widget["spec"]["encodings"])
        for y in {p[1] for p in occupied}:
            assert {x for x, row in occupied if row == y} == set(range(12))


def test_global_parameter_coverage():
    content = dashboard()
    filters = content["pages"][2]["layout"]
    for dataset in content["datasets"]:
        assert "demo_redshift.customer_360." in "".join(dataset["queryLines"])
        for parameter in dataset.get("parameters", []):
            key = parameter["keyword"]
            matching = next(f["widget"] for f in filters if f["widget"]["name"] == "filter_" + key)
            assert any(q["query"]["datasetName"] == dataset["name"] for q in matching["queries"])


@pytest.mark.parametrize("rows", [[{"value": "1"}], []])
def test_cli_result_parsing(rows):
    completed = subprocess.CompletedProcess([], 0, stdout=json.dumps(rows))
    with patch.object(verify_dashboard.subprocess, "run", return_value=completed):
        assert verify_dashboard.run_dataset({"queryLines": ["SELECT 1"]}) == rows


def test_cli_failure_propagates():
    with patch.object(verify_dashboard.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "databricks")), pytest.raises(subprocess.CalledProcessError):
        verify_dashboard.run_dataset({"queryLines": ["SELECT invalid"]})
