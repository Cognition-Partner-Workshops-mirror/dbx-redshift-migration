"""Offline checks for the Statement API helpers (no live writes)."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import reset
import verify
from databricks.sdk.service.sql import StatementState


def response(state, rows=None):
    status = Mock(state=state)
    status.as_dict.return_value = {"state": state.value}
    return SimpleNamespace(
        status=status, statement_id="test",
        manifest=SimpleNamespace(schema=SimpleNamespace(columns=[SimpleNamespace(name="n")])),
        result=SimpleNamespace(data_array=rows),
    )


@pytest.mark.parametrize("rows", [[["1"]], [], None])
def test_query_normal_and_empty(rows):
    client = Mock()
    client.statement_execution.execute_statement.return_value = response(StatementState.SUCCEEDED, rows)
    assert verify.query(client, "SELECT 1") == (rows or [])


def test_query_polls_and_reports_failure():
    client = Mock()
    client.statement_execution.execute_statement.return_value = response(StatementState.PENDING)
    client.statement_execution.get_statement.return_value = response(StatementState.FAILED)
    with patch.object(verify.time, "sleep"), pytest.raises(RuntimeError, match="FAILED"):
        verify.query(client, "SELECT invalid")


def test_reset_only_drops_product_schema():
    client = Mock()
    client.statement_execution.execute_statement.return_value = response(StatementState.SUCCEEDED)
    with patch.object(reset, "WorkspaceClient", return_value=client):
        reset.main()
    assert client.statement_execution.execute_statement.call_args.kwargs == {
        "warehouse_id": "6dc4b80538621b7b",
        "statement": "DROP SCHEMA IF EXISTS demo_redshift.customer_360 CASCADE",
        "wait_timeout": "50s",
    }


def test_reset_reports_failure():
    client = Mock()
    client.statement_execution.execute_statement.return_value = response(StatementState.FAILED)
    with patch.object(reset, "WorkspaceClient", return_value=client), pytest.raises(RuntimeError, match="FAILED"):
        reset.main()
