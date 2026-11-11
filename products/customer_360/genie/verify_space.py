"""API-only acceptance checks; retain generated SQL and result previews locally."""
import json
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from databricks.sdk import WorkspaceClient
from manage import ROOT, find_space


def ask(client, space_id, question):
    message = client.genie.start_conversation_and_wait(space_id, question)
    evidence = {"question": question, "conversation_id": message.conversation_id,
                "message_id": message.id, "status": message.status.value, "queries": []}
    for attachment in message.attachments or []:
        if not attachment.query:
            continue
        result = client.genie.get_message_attachment_query_result(
            space_id, message.conversation_id, message.id, attachment.attachment_id)
        response = result.statement_response
        if not response or not response.result or not response.result.data_array:
            raise AssertionError(f"No result rows for {question}")
        evidence["queries"].append({
            "sql": attachment.query.query,
            "columns": [c.name for c in response.manifest.schema.columns],
            "rows": response.result.data_array,
        })
    if not evidence["queries"]:
        raise AssertionError(f"No SQL returned: {message.as_dict()}")
    return evidence


def validate(evidence):
    expected = ["customer_health", "customer_health_metrics", "revenue_metrics"]
    for item, source in zip(evidence, expected, strict=True):
        sql = "\n".join(q["sql"] for q in item["queries"]).lower().replace("`", "")
        assert f"demo_redshift.customer_360.{source}" in sql, sql
        assert "current_date" not in sql and ".gold." not in sql, sql
    risk = evidence[1]["queries"][0]
    index = risk["columns"].index("revenue_at_risk")
    total = sum(Decimal(row[index]) for row in risk["rows"])
    assert abs(total - Decimal("1327164.70")) < Decimal("0.01"), total
    quarter_sql = evidence[2]["queries"][0]["sql"].lower()
    assert "2025" in quarter_sql and ("q3" in quarter_sql or "2025-08-01" in quarter_sql)
    assert "measure(" in quarter_sql.replace(" ", "")


def main():
    client = WorkspaceClient()
    space = find_space(client)
    if not space:
        raise RuntimeError("Deploy the Genie space first")
    config = json.loads((ROOT / "space.json").read_text())
    questions = [config["config"]["sample_questions"][i]["question"][0] for i in (0, 3, 2)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        evidence = list(pool.map(lambda q: ask(client, space.space_id, q), questions))
    (ROOT / "verification.local.json").write_text(json.dumps(evidence, indent=2) + "\n")
    for item in evidence:
        print(item["question"])
        for query in item["queries"]:
            print(query["sql"])
            print(json.dumps({"columns": query["columns"], "preview": query["rows"][:6]}, indent=2))
    validate(evidence)
    print("PASS: 3 Genie Conversation API answers; certified sources, FY2025 Q3, risk total 1327164.70")


if __name__ == "__main__":
    main()
