import ast
import re
from pathlib import Path

from validation.sqlsplit import splitStatements


def test_runner_splitter():
    root = Path(__file__).resolve().parents[2]
    module = ast.parse((root / "databricks/orchestration/run_sql.py").read_text())
    function = next(node for node in module.body if isinstance(node, ast.FunctionDef))
    namespace = {"re": re}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "splitter", "exec"), namespace)  # noqa: S102
    split = namespace["split_statements"]
    samples = [
        "",
        "-- comment only;\n",
        "SELECT 1; SELECT 'escaped\\\';literal'; -- comment;\nSELECT 2;",
        'SELECT "quoted;identifier", `another;identifier`; /* comment; */ SELECT 2;',
        "BEGIN DECLARE x INT DEFAULT 1; SELECT CASE WHEN x=1 THEN 2 END; END; SELECT 3;",
        "BEGIN; SELECT 1; COMMIT;",
        "CREATE PROCEDURE p() AS $tag$ BEGIN SELECT 1; END; $tag$; CALL p();",
        (root / "databricks/foundation/etl.sql").read_text(),
        (root / "databricks/units/inventory_snapshot/etl.sql").read_text(),
    ]
    for sql in samples:
        actual = [s.strip() for s in split(sql)
                  if re.sub(r"--[^\n]*|/\*.*?\*/", "", s, flags=re.DOTALL).strip()]
        assert actual == splitStatements(sql)
