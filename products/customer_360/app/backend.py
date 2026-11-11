"""Certified customer queries and Genie calls using app service-principal auth."""
import time
from datetime import timedelta

from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks.sdk.service.sql import StatementParameterListItem, StatementState


class Backend:
    def __init__(self, warehouse_id, space_id, client=None):
        self.client = client or WorkspaceClient(config=Config())
        self.warehouse_id = warehouse_id
        self.space_id = space_id

    def query(self, statement, parameters=()):
        response = self.client.statement_execution.execute_statement(
            warehouse_id=self.warehouse_id, statement=statement, parameters=list(parameters),
            wait_timeout="50s", row_limit=1000)
        deadline = time.monotonic() + 120
        while response.status.state in (StatementState.PENDING, StatementState.RUNNING):
            if time.monotonic() > deadline:
                self.client.statement_execution.cancel_execution(response.statement_id)
                raise TimeoutError("SQL query timed out")
            time.sleep(1)
            response = self.client.statement_execution.get_statement(response.statement_id)
        if response.status.state != StatementState.SUCCEEDED:
            raise RuntimeError("SQL query failed; check warehouse access and availability")
        columns = [c.name for c in response.manifest.schema.columns]
        return [dict(zip(columns, row, strict=True)) for row in response.result.data_array or []]

    def search(self, term):
        term = term.strip()
        if not term:
            return []
        return self.query(
            "SELECT customer_id, name, email, region FROM demo_redshift.customer_360.customer_profile "
            "WHERE contains(lower(name), lower(:term)) OR contains(lower(email), lower(:term)) "
            "OR CAST(customer_id AS STRING) = :term ORDER BY name, customer_id LIMIT 50",
            [StatementParameterListItem(name="term", value=term, type="STRING")])

    def customer(self, customer_id):
        rows = self.query(
            "SELECT p.*, h.health_segment, h.recency_days, h.revenue_at_risk "
            "FROM demo_redshift.customer_360.customer_profile p "
            "JOIN demo_redshift.customer_360.customer_health h USING (customer_id) "
            "WHERE p.customer_id = :customer_id",
            [StatementParameterListItem(name="customer_id", value=str(customer_id), type="BIGINT")])
        return rows[0] if rows else None

    def orders(self, customer_id):
        return self.query(
            "SELECT order_id, order_ts, order_date, status, sales_channel, gross_amount, net_amount "
            "FROM demo_redshift.customer_360.order_facts WHERE customer_id = :customer_id "
            "ORDER BY order_ts DESC, order_id DESC LIMIT 10",
            [StatementParameterListItem(name="customer_id", value=str(customer_id), type="BIGINT")])

    def portfolio(self):
        return self.query(
            "SELECT health_segment, MEASURE(customers) AS customers "
            "FROM demo_redshift.customer_360.customer_health_metrics GROUP BY health_segment ORDER BY health_segment")

    def ask(self, question):
        if not question.strip():
            return {"text": "Enter a question to ask Genie.", "queries": []}
        message = self.client.genie.start_conversation_and_wait(
            self.space_id, question.strip(), timeout=timedelta(seconds=180))
        text, queries = [], []
        for attachment in message.attachments or []:
            if attachment.text and attachment.text.content:
                text.append(attachment.text.content)
            if attachment.query:
                result = self.client.genie.get_message_attachment_query_result(
                    self.space_id, message.conversation_id, message.message_id, attachment.attachment_id)
                response = result.statement_response
                if not response or not response.manifest or not response.result:
                    raise RuntimeError("Genie query result is not available")
                columns = [c.name for c in response.manifest.schema.columns]
                queries.append({"sql": attachment.query.query,
                                "description": attachment.query.description,
                                "rows": [dict(zip(columns, row, strict=True))
                                         for row in response.result.data_array or []]})
        answer = "\n\n".join(text)
        if not answer:
            answer = "Genie returned the results below." if queries else "No answer was returned. Try a more specific question."
        return {"text": answer, "queries": queries}
