"""Statement API queries and Genie access for the Customer Lookup app."""

from datetime import timedelta
from time import monotonic, sleep

from databricks.sdk.service.sql import StatementParameterListItem, StatementState

PORTFOLIO = """
SELECT MEASURE(customers) AS customers, MEASURE(active_customers) AS active_customers
FROM demo_redshift.customer_360.customer_health_metrics
"""
PORTFOLIO_SEGMENTS = """
SELECT segment, MEASURE(customers) AS customers
FROM demo_redshift.customer_360.customer_health_metrics
GROUP BY segment
"""
SEARCH = """
SELECT p.customer_id, CONCAT_WS(' ', p.first_name, p.last_name) AS full_name, p.email,
       p.phone, p.region, p.is_business, p.signup_date, p.preferred_store,
       p.first_order_date, p.last_order_date, p.completed_orders, p.net_ltv,
       p.gross_spend, p.aov, p.returned_items, p.top_category, h.segment, h.recency_days
FROM demo_redshift.customer_360.customer_profile p
JOIN demo_redshift.customer_360.customer_health h USING (customer_id)
WHERE p.customer_id = TRY_CAST(REGEXP_REPLACE(:term, '^#', '') AS BIGINT)
   OR CONTAINS(LOWER(CONCAT_WS(' ', p.first_name, p.last_name)), LOWER(:term))
   OR CONTAINS(LOWER(p.email), LOWER(:term))
ORDER BY p.last_name, p.first_name, p.customer_id
LIMIT 25
"""
ORDERS = """
SELECT order_id AS `Order`, order_ts AS `Placed at`, channel AS Channel, status AS Status,
       items AS Items, gross_amount AS `Gross (USD)`, net_amount AS `Net (USD)`
FROM demo_redshift.customer_360.order_facts
WHERE customer_id = :customer_id
ORDER BY order_ts DESC, order_id DESC
LIMIT 10
"""


def records(response):
    if not response or not response.manifest or not response.result:
        return []
    columns = [column.name for column in response.manifest.schema.columns]
    return [
        dict(zip(columns, row, strict=True))
        for row in response.result.data_array or []
    ]


def query(workspace, warehouse, sql, **values):
    parameters = [
        StatementParameterListItem(
            name=name, value=str(value), type="BIGINT" if isinstance(value, int) else "STRING"
        )
        for name, value in values.items()
    ]
    result = workspace.statement_execution.execute_statement(
        sql, warehouse, parameters=parameters, wait_timeout="10s", row_limit=100
    )
    deadline = monotonic() + 45
    while result.status.state in (StatementState.PENDING, StatementState.RUNNING) and monotonic() < deadline:
        sleep(1)
        result = workspace.statement_execution.get_statement(result.statement_id)
    if result.status.state != StatementState.SUCCEEDED:
        raise RuntimeError(f"SQL statement {result.statement_id} ended in state {result.status.state}")
    return records(result)


def ask(workspace, space_id, question, conversation_id):
    timeout = timedelta(seconds=105)
    if conversation_id:
        message = workspace.genie.create_message_and_wait(space_id, conversation_id, question, timeout=timeout)
    else:
        message = workspace.genie.start_conversation_and_wait(space_id, question, timeout=timeout)

    answer = []
    queries = []
    for item in message.attachments or []:
        if item.text and item.text.content:
            answer.append(item.text.content)
        if item.query:
            result = workspace.genie.get_message_attachment_query_result(
                space_id, message.conversation_id, message.message_id, item.attachment_id
            ).statement_response
            queries.append({
                "sql": item.query.query,
                "description": item.query.description,
                "rows": records(result)[:50],
            })
    return message.conversation_id, {"answer": answer, "queries": queries}
