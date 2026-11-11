"""App backend normal, empty and failure paths, independent of Streamlit."""
from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import pytest
from app.backend import Backend
from app.presentation import literal_dollars
from databricks.sdk.service.sql import StatementState
from deploy_app import grant_access


def test_genie_answer_dollar_amounts_are_literal():
    answer = "Revenue at risk: SOTH $292,691.46 and SW $115,725.36."
    assert literal_dollars(answer) == r"Revenue at risk: SOTH \$292,691.46 and SW \$115,725.36."


@pytest.mark.parametrize("value", ["", "No results", r"Already escaped \$12.00", None, 42])
def test_literal_dollars_preserves_other_values(value):
    assert literal_dollars(value) == value


def response(rows=(), columns=("customer_id",), state=StatementState.SUCCEEDED):
    return NS(status=NS(state=state), statement_id="statement",
              manifest=NS(schema=NS(columns=[NS(name=c) for c in columns])),
              result=NS(data_array=rows))


def backend(result=None):
    client = MagicMock()
    client.statement_execution.execute_statement.return_value = result or response()
    return Backend("warehouse", "space", client), client


def test_search_is_bound_and_empty_search_does_not_query():
    service, client = backend(response([["342"]]))
    assert service.search("   ") == []
    client.statement_execution.execute_statement.assert_not_called()
    term = "Emerson Silva' OR 1=1 --"
    assert service.search(term) == [{"customer_id": "342"}]
    args = client.statement_execution.execute_statement.call_args.kwargs
    assert term not in args["statement"]
    assert args["parameters"][0].value == term
    assert "lower(:term)" in args["statement"]


def test_customer_card_and_order_queries():
    service, client = backend(response([["342", "Emerson Silva", "At risk", "7867.09"]],
                                       ("customer_id", "name", "health_segment", "net_ltv")))
    assert service.customer(342)["name"] == "Emerson Silva"
    assert client.statement_execution.execute_statement.call_args.kwargs["parameters"][0].value == "342"
    service.orders(342)
    sql = client.statement_execution.execute_statement.call_args.kwargs["statement"]
    assert "LIMIT 10" in sql and "gross_amount, net_amount" in sql
    assert "order_ts" in sql and "ORDER BY order_ts DESC, order_id DESC" in sql
    client.statement_execution.execute_statement.return_value = response()
    assert service.customer(9999) is None
    assert service.orders(9999) == []


def test_portfolio_and_query_polling():
    service, client = backend(response(state=StatementState.PENDING))
    client.statement_execution.get_statement.return_value = response([["At risk", "248"]],
                                                                     ("health_segment", "customers"))
    assert service.portfolio()[0]["customers"] == "248"
    assert "MEASURE(customers)" in client.statement_execution.execute_statement.call_args.kwargs["statement"]


def test_sql_failure_and_api_errors():
    service, client = backend(response(state=StatementState.FAILED))
    with pytest.raises(RuntimeError, match="SQL query failed"):
        service.search("Emerson")
    client.statement_execution.execute_statement.side_effect = RuntimeError("unavailable")
    with pytest.raises(RuntimeError, match="unavailable"):
        service.customer(342)


def test_genie_text_sql_and_result_table():
    service, client = backend()
    client.genie.start_conversation_and_wait.return_value = NS(
        conversation_id="conversation", message_id="message", attachments=[NS(
            attachment_id="attachment", text=NS(content="Certified result"),
            query=NS(query="SELECT MEASURE(revenue_at_risk)", description="Risk"))])
    client.genie.get_message_attachment_query_result.return_value = NS(
        statement_response=response([["1327164.70"]], ("revenue_at_risk",)))
    answer = service.ask("How much revenue is at risk?")
    assert answer["text"] == "Certified result"
    assert answer["queries"][0]["rows"] == [{"revenue_at_risk": "1327164.70"}]
    client.genie.get_message_attachment_query_result.assert_called_once_with(
        "space", "conversation", "message", "attachment")


def test_genie_empty_and_error_states():
    service, client = backend()
    assert service.ask(" ")["queries"] == []
    client.genie.start_conversation_and_wait.assert_not_called()
    client.genie.start_conversation_and_wait.return_value = NS(attachments=[])
    assert "No answer" in service.ask("question")["text"]
    client.genie.start_conversation_and_wait.side_effect = TimeoutError("timed out")
    with pytest.raises(TimeoutError):
        service.ask("question")


def test_grants_are_schema_scoped_and_principal_escaped():
    _, client = backend()
    grant_access(client, "app`principal")
    calls = client.statement_execution.execute_statement.call_args_list
    assert len(calls) == 3
    assert "GRANT SELECT ON SCHEMA demo_redshift.customer_360 TO `app``principal`" == calls[2].kwargs["statement"]
    with pytest.raises(RuntimeError, match="not available"):
        grant_access(client, "")
