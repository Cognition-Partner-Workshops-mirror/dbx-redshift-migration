import io
import json
from types import SimpleNamespace

import pytest
import yaml

from validation.consumer_parity import evaluate, literal, matrix, persist, run, setup, successful, volumeRows


class FakeDb:
    catalog = "demo_redshift"

    def __init__(self, rows=None, error=None):
        self.rows = [["1", "10.00"]] if rows is None else rows
        self.error = error
        self.statements = []

    def run(self, sql):
        self.statements.append(sql)
        if self.error:
            raise RuntimeError(self.error)
        return [("id", "INT"), ("value", "DECIMAL")], self.rows


def test_sql_string_escaping():
    assert literal("O'Reilly\\archive") == "'O\\'Reilly\\\\archive'"
    assert literal(None) == "NULL"
    assert literal(42) == "42"


@pytest.fixture
def contract(tmp_path):
    for directory in ["golden/orders", ".migration", "validation", "consumers"]:
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)
    (tmp_path / "golden/orders/report.csv").write_text("id,value\n1,10.00\n")
    (tmp_path / "golden/orders/report.meta.json").write_text(json.dumps({"columns": [
        {"name": "id", "family": "int"}, {"name": "value", "family": "decimal"}]}))
    (tmp_path / ".migration/units.yaml").write_text(yaml.safe_dump({"units": {"orders": {"outputs": [
        {"name": "report", "golden": "golden/orders/report.csv", "keys": ["id"]}]}}}))
    (tmp_path / "validation/tolerances.yaml").write_text(yaml.safe_dump({"default": {
        "decimal_abs": .000001, "float_abs": 1e-9, "float_rel": 1e-9, "string_rstrip": False}}))
    (tmp_path / "consumers/service.py").write_text('"""databricks sql connection"""\nSQL = "SELECT * FROM gold.orders;"')
    return {"id": "orders", "consumer": "Reporting", "file": "consumers/service.py", "query": "SQL",
            "golden_unit": "orders"}


def test_current_normal_empty_mismatch_error(tmp_path, contract):
    assert evaluate(contract, "current", FakeDb(), tmp_path)["status"] == "PASS"
    assert evaluate(contract, "current", FakeDb([]), tmp_path)["status"] == "FAIL"
    result = evaluate(contract, "current", FakeDb([["1", "10.01"]]), tmp_path)
    assert result["mismatched_rows"] == 1
    assert evaluate(contract, "current", FakeDb(error="warehouse unavailable"), tmp_path)["status"] == "ERROR"


def test_naive_only_swaps_schema(tmp_path, contract):
    db = FakeDb()
    reader = lambda *args: 'SQL = "SELECT * FROM mart.orders JOIN core.stores USING (id);"'
    assert evaluate(contract, "naive", db, tmp_path, reader=reader)["status"] == "PASS"
    assert db.statements == ["SELECT * FROM gold.orders JOIN silver.stores USING (id);"]


def test_smoke_and_connection(tmp_path, contract):
    entry = {**contract, "check": "smoke"}
    result = evaluate(entry, "current", FakeDb([]), tmp_path)
    assert result["status"] == "SMOKE"
    assert "| SMOKE |" in matrix([result])
    assert successful([result])
    assert not successful([{"status": "FAIL"}])
    (tmp_path / entry["file"]).write_text('SQL = "SELECT 1"\n# redshift')
    assert evaluate(entry, "current", FakeDb(), tmp_path)["status"] == "ERROR"


def test_file_sources(tmp_path, contract):
    entry = {**contract, "kind": "file", "path": "URI"}
    reader = lambda *args: 'URI = "s3://retail/orders/"'
    assert evaluate(entry, "naive", FakeDb(), tmp_path, reader=reader)["status"] == "FAIL"
    db = FakeDb()
    db.client = SimpleNamespace(files=SimpleNamespace(download=lambda uri: SimpleNamespace(
        contents=io.BytesIO(b"id,value\n1,10.00\n"))))
    reader = lambda *args: 'URI = "/Volumes/demo_redshift/gold/exports/orders.csv"'
    assert evaluate(entry, "current", db, tmp_path, reader=reader)["status"] == "PASS"
    with pytest.raises(ValueError):
        volumeRows(db.client, "/Volumes/another/schema/files/x.csv")


def test_persistence_and_run(tmp_path, contract, monkeypatch):
    monkeypatch.setattr("validation.consumer_parity.subprocess.check_output", lambda *a, **kw: "abc123\n")
    db = FakeDb()
    evidence = run([contract], "current", db, tmp_path)
    assert evidence["results"][0]["status"] == "PASS"
    assert (tmp_path / ".migration/evidence/consumers_current.json").exists()
    assert "INSERT INTO demo_redshift.consumer_parity.results" in db.statements[-1]
    assert not (tmp_path / ".migration/evidence/orders.json").exists()
    with pytest.raises(ValueError):
        run([], "current", db, tmp_path)
    with pytest.raises(ValueError):
        run([contract, contract], "current", db, tmp_path)
    setup(db)
    assert any("GRANT ALL PRIVILEGES ON SCHEMA" in sql for sql in db.statements)
    persist(db, {**evidence, "results": []})


def test_reject_writes(tmp_path, contract):
    reader = lambda *args: 'SQL = "DELETE FROM mart.orders"'
    assert evaluate(contract, "naive", FakeDb(), tmp_path, reader=reader)["status"] == "ERROR"


@pytest.mark.parametrize("mode,schema", [("naive", "mart"), ("current", "gold")])
def test_reject_published_smoke(tmp_path, contract, mode, schema):
    reports = tmp_path / "legacy/redshift/units/orders"
    reports.mkdir(parents=True)
    (reports / "report.sql").write_text("SELECT *\nFROM mart.orders;")
    reader = lambda *args: f'from databricks import sql\nSQL = "SELECT  * FROM {schema}.orders;"'
    db = FakeDb()
    result = evaluate({**contract, "check": "smoke"}, mode, db, tmp_path, reader=reader)
    assert result["status"] == "ERROR"
    assert "published reports" in result["detail"]
    assert db.statements == []


def test_smoke_evidence_and_storage(tmp_path, contract, monkeypatch):
    monkeypatch.setattr("validation.consumer_parity.subprocess.check_output", lambda *a, **kw: "abc123\n")
    db = FakeDb([])
    evidence = run([{**contract, "check": "smoke"}], "current", db, tmp_path)
    assert evidence["results"][0]["status"] == "SMOKE"
    assert "SMOKE" in (tmp_path / ".migration/evidence/consumers_current.json").read_text()
    assert "'SMOKE'" in db.statements[-1]


@pytest.mark.parametrize("missing,extra", [(["revenue"], []), ([], ["unexpected"]),
                                         (["revenue"], ["unexpected"])])
def test_matrix_column_failures(missing, extra):
    result = {"consumer": "Reporting", "query_id": "orders", "status": "FAIL", "detail": "",
              "rows_expected": 1, "rows_actual": 1, "checks": [
                  {"check": "columns", "status": "FAIL", "missing": missing, "extra": extra},
                  {"check": "row_values", "status": "FAIL", "detail": "skipped: missing columns"}]}
    rendered = matrix([result])
    assert json.dumps({"missing": missing, "extra": extra}) in rendered
    assert "mismatched_rows" not in rendered
