"""Compare declared downstream consumers without rebuilding migration units."""
import argparse
import csv
import datetime as dt
import io
import json
import os
import pathlib
import re
import subprocess
import uuid

from databricks.sdk.errors import DatabricksError

from validation.compare import compareOutput, loadGolden
from validation.consumer_extract import connectionIsDatabricks, extract
from validation.dbsql import DbSql
from validation.sqlsplit import splitStatements
from validation.validate_unit import ROOT, loadYaml, toleranceLookup


def catalogName(value):
    if value != "demo_redshift":
        raise ValueError("consumer operations are restricted to demo_redshift")
    return value


def literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("\\", "\\\\").replace("'", "\\'") + "'"


def setup(db):
    catalog = catalogName(db.catalog)
    for sql in [
        f"CREATE SCHEMA IF NOT EXISTS {catalog}.consumer_parity",
        f"GRANT ALL PRIVILEGES ON SCHEMA {catalog}.consumer_parity TO `account users`",
        f"""CREATE TABLE IF NOT EXISTS {catalog}.consumer_parity.results (
            run_id STRING, run_at TIMESTAMP, mode STRING, git_sha STRING,
            consumer STRING, query_id STRING, golden STRING, status STRING, detail STRING,
            rows_expected BIGINT, rows_actual BIGINT, mismatched_rows BIGINT
        ) USING DELTA""",
    ]:
        db.run(sql)


def readSource(root, file, mode, baseline):
    path = pathlib.PurePosixPath(file)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("consumer file must be repository-relative")
    if mode == "naive":
        return subprocess.check_output(["git", "show", f"{baseline}:{file}"], cwd=root, text=True)
    return (root / file).read_text()


def resolveGolden(entry, manifest):
    unit = entry.get("golden_unit")
    output = entry.get("golden_output", "report")
    if unit:
        declared = next(o for o in manifest["units"][unit]["outputs"] if o["name"] == output)
        return declared["golden"], entry.get("keys", declared["keys"]), unit, output
    golden = entry["golden"]
    for unit, spec in manifest["units"].items():
        for declared in spec["outputs"]:
            if declared["golden"] == golden:
                return golden, entry.get("keys", declared["keys"]), unit, declared["name"]
    return golden, entry["keys"], "", ""


def volumeRows(client, uri):
    if not uri.startswith("/Volumes/demo_redshift/") or ".." in pathlib.PurePosixPath(uri).parts:
        raise ValueError("only demo_redshift volume files can be read")
    response = client.files.download(uri)
    try:
        text = response.contents.read().decode("utf-8")
    finally:
        response.contents.close()
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    return [(c, "STRING") for c in header], [[None if v == "\\N" else v for v in r] for r in reader]


def isPublishedReport(sql, root):
    def normalized(value):
        return " ".join(re.sub(r"--[^\n]*|/\*.*?\*/", "", value, flags=re.DOTALL).split())

    candidate = normalized(sql)
    for report in (root / "legacy/redshift").rglob("report.sql"):
        source = report.read_text()
        if candidate in (normalized(source), normalized(source.replace("mart.", "gold.").replace("core.", "silver."))):
            return True
    return False


def successful(results):
    return all(r["status"] in ("PASS", "SMOKE") for r in results)


def evaluate(entry, mode, db, root=ROOT, baseline="consumer-cutover-baseline", reader=readSource):
    record = {"consumer": entry["consumer"], "query_id": entry["id"], "golden": None,
              "status": "ERROR", "detail": "", "rows_expected": None, "rows_actual": None,
              "mismatched_rows": None}
    try:
        text = reader(root, entry["file"], mode, baseline)
        value = extract(text, entry["file"], entry.get("query"), entry.get("path"))
        isFile = entry.get("kind") == "file" or "path" in entry
        if entry.get("check") == "smoke" and not isFile and isPublishedReport(value, root):
            raise ValueError("published reports require a golden comparison, not a smoke check")
        if not isFile and mode == "current":
            connectionText = text
            if entry["file"].endswith(".tmdl"):
                expressions = str(pathlib.PurePosixPath(entry["file"]).parent.parent / "expressions.tmdl")
                connectionText += reader(root, expressions, mode, baseline)
            if not connectionIsDatabricks(connectionText):
                raise ValueError("consumer connection is not configured for Databricks")
        if mode == "naive" and not isFile:
            value = value.replace("mart.", "gold.").replace("core.", "silver.")
        if entry.get("check") != "smoke":
            golden, keys, unit, output = resolveGolden(entry, loadYaml(root / ".migration/units.yaml"))
            record["golden"] = golden
            csvPath = (root / golden).resolve()
            if not csvPath.is_relative_to((root / "golden").resolve()):
                raise ValueError("reference CSV must be under golden/")
            gc, gr = loadGolden(csvPath, csvPath.with_suffix(".meta.json"))
            record["rows_expected"] = len(gr)
        if isFile:
            if value.startswith("s3://"):
                record.update(status="FAIL", detail="unreachable file source: " + value)
                return record
            columns, rows = volumeRows(db.client, value)
        else:
            # A consumer contract may execute reads, never ETL or DDL.
            executable = re.sub(r"--[^\n]*", "", value).strip()
            statements = splitStatements(executable)
            if len(statements) != 1 or not re.match(r"(?is)^(SELECT|WITH)\b", executable):
                raise ValueError("consumer query must be a single SELECT or WITH statement")
            if re.search(r"(?i)\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|COPY|CALL)\b", executable):
                raise ValueError("consumer query must be read-only")
            columns, rows = db.run(value)
        record["rows_actual"] = len(rows)
        if entry.get("check") == "smoke":
            record.update(status="SMOKE", detail="query executed successfully; no output comparison")
        else:
            tolFor, _ = toleranceLookup(loadYaml(root / "validation/tolerances.yaml"), unit, output)
            result = compareOutput(gc, gr, columns, rows, keys, tolFor)
            record["status"] = result["status"]
            record["checks"] = result["checks"]
            values = next((c for c in result["checks"] if c["check"] == "row_values"), {})
            record["mismatched_rows"] = values.get("mismatched_rows")
            record["detail"] = "matched" if result["status"] == "PASS" else json.dumps(
                [c for c in result["checks"] if c["status"] != "PASS"], default=str)
    except (ValueError, KeyError, OSError, RuntimeError, SyntaxError, StopIteration,
            DatabricksError, SystemExit) as exc:
        record.update(status="ERROR", detail=str(exc)[:4000])
    return record


def persist(db, evidence):
    catalog = catalogName(db.catalog)
    fields = ["consumer", "query_id", "golden", "status", "detail", "rows_expected", "rows_actual", "mismatched_rows"]
    rows = []
    for result in evidence["results"]:
        values = [evidence[k] for k in ("run_id", "run_at", "mode", "git_sha")]
        values += [result[k] for k in fields]
        rows.append("(" + ",".join(literal(v) for v in values) + ")")
    if rows:
        db.run(f"INSERT INTO {catalog}.consumer_parity.results VALUES " + ",\n".join(rows))


def matrix(results):
    lines = ["| Consumer | Query | Status | Expected | Actual | Detail |",
             "| --- | --- | --- | ---: | ---: | --- |"]
    for r in results:
        detail = r["detail"].replace("|", "\\|").replace("\n", " ")
        if r.get("checks") and r["status"] != "PASS":
            values = next(c for c in r["checks"] if c["check"] == "row_values")
            detail = json.dumps({k: values.get(k) for k in
                                 ("mismatched_rows", "mismatches_by_column", "missing_in_target", "extra_in_target")})
        lines.append(f'| {r["consumer"]} | {r["query_id"]} | {r["status"]} | '
                     f'{r["rows_expected"]} | {r["rows_actual"]} | {detail[:400]} |')
    return "\n".join(lines)


def run(entries, mode, db, root=ROOT, baseline="consumer-cutover-baseline"):
    catalogName(db.catalog)
    if mode not in ("naive", "current"):
        raise ValueError("mode must be naive or current")
    if not entries or len({e["id"] for e in entries}) != len(entries):
        raise ValueError("contract must contain entries with unique ids")
    sha = subprocess.check_output(["git", "rev-parse", baseline if mode == "naive" else "HEAD"],
                                  cwd=root, text=True).strip()
    evidence = {"run_id": str(uuid.uuid4()), "run_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "mode": mode, "git_sha": sha, "catalog": db.catalog,
                "results": [evaluate(e, mode, db, root, baseline) for e in entries]}
    evidenceDir = root / ".migration/evidence"
    evidenceDir.mkdir(parents=True, exist_ok=True)
    (evidenceDir / f"consumers_{mode}.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(matrix(evidence["results"]))
    persist(db, evidence)
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--mode", choices=["naive", "current"], default="current")
    parser.add_argument("--baseline", default="consumer-cutover-baseline")
    parser.add_argument("--contract", type=pathlib.Path, default=ROOT / ".migration/consumers.yaml")
    parser.add_argument("--catalog", default=os.environ.get("MIG_CATALOG", "demo_redshift"))
    args = parser.parse_args()
    db = DbSql(catalog=catalogName(args.catalog))
    if args.setup:
        setup(db)
        print(f"ready: {db.catalog}.consumer_parity.results")
        return
    contract = loadYaml(args.contract)
    evidence = run(contract["consumers"], args.mode, db, baseline=args.baseline)
    raise SystemExit(0 if successful(evidence["results"]) else 1)


if __name__ == "__main__":
    main()
