"""Execute every exact dashboard dataset via CLI before deployment."""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def run_dataset(dataset, selections=None):
    command = ["databricks", "experimental", "aitools", "tools", "query",
               "--warehouse", "6dc4b80538621b7b", "--output", "json"]
    for parameter in dataset.get("parameters", []):
        name = parameter["keyword"]
        command += ["--param", f"{name}={(selections or {}).get(name, 'All')}"]
    command.append("".join(dataset["queryLines"]))
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def main():
    dashboard = json.loads((Path(__file__).parent / "dashboards/customer_health_revenue.lvdash.json").read_text())
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run_dataset, dashboard["datasets"]))
    for dataset, result in zip(dashboard["datasets"], results, strict=True):
        rows = result
        assert rows, f"No rows: {dataset['name']}"
        print(f"{dataset['name']}: {len(rows)} rows")
    selected = {"fiscal_quarter": "Q1", "sales_channel": "web", "region": "EAST"}
    for dataset in dashboard["datasets"]:
        if dataset.get("parameters"):
            result = run_dataset(dataset, selected)
            assert result, f"Filtered scope returned no rows: {dataset['name']}"
    print("PASS: all dataset queries return rows; Q1/web/EAST parameter bindings execute")


if __name__ == "__main__":
    main()
