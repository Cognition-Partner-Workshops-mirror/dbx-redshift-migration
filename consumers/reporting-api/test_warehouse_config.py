import ast
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("surface", ["service", "notebook", "cron"])
@pytest.mark.parametrize("warehouse,http_path,expected", [
    (None, None, "/sql/1.0/warehouses/6dc4b80538621b7b"),
    ("warehouse-override", None, "/sql/1.0/warehouses/warehouse-override"),
    ("warehouse-override", "/custom/path", "/custom/path"),
])
def test_warehouse_path(monkeypatch, surface, warehouse, http_path, expected):
    for key, value in [("DATABRICKS_WAREHOUSE_ID", warehouse), ("DATABRICKS_HTTP_PATH", http_path)]:
        monkeypatch.delenv(key, raising=False)
        if value is not None:
            monkeypatch.setenv(key, value)
    if surface == "service":
        source = (ROOT / "consumers/reporting-api/service.py").read_text()
    elif surface == "notebook":
        notebook = json.loads((ROOT / "consumers/notebooks/customer_segments.ipynb").read_text())
        source = "".join(notebook["cells"][0]["source"])
    else:
        source = (ROOT / "ops/cron/kpi_digest.sh").read_text().split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    expression = next(node.value for node in ast.walk(ast.parse(source))
                      if isinstance(node, ast.keyword) and node.arg == "http_path")
    assert eval(compile(ast.Expression(expression), "<http_path>", "eval"), {"os": os}) == expected
