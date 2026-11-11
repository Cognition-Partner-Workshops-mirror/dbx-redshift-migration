"""Offline configuration and lifecycle safety contracts."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import manage
import pytest
import verify_space


def page(spaces=(), token=None):
    return SimpleNamespace(spaces=spaces, next_page_token=token)


def space():
    return SimpleNamespace(title=manage.TITLE, space_id="abc123")


def test_serialized_definition():
    config = json.loads((manage.ROOT / "space.json").read_text())
    tables = config["data_sources"]["tables"]
    assert tables == sorted(tables, key=lambda t: t["identifier"])
    assert len(tables) == 5
    assert all(t["identifier"].startswith("demo_redshift.customer_360.") for t in tables)
    entries = config["config"]["sample_questions"]
    assert 6 <= len(entries) <= 8
    entries += config["instructions"]["example_question_sqls"]
    entries += config["instructions"]["text_instructions"]
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids))
    assert all(len(i) == 32 and int(i, 16) for i in ids)
    assert len(config["instructions"]["text_instructions"]) == 1


def test_create_then_update(tmp_path, monkeypatch):
    (tmp_path / "space.json").write_text((manage.ROOT / "space.json").read_text())
    monkeypatch.setattr(manage, "ROOT", tmp_path)
    client = MagicMock()
    client.genie.list_spaces.side_effect = [page(), page([space()])]
    client.genie.create_space.return_value = space()
    client.genie.update_space.return_value = space()
    client.current_user.me.return_value.user_name = "test-user"
    manage.deploy(client)
    manage.deploy(client)
    client.genie.create_space.assert_called_once()
    client.genie.update_space.assert_called_once()
    assert (tmp_path / ".space_id").read_text() == "abc123\n"
    assert client.permissions.update.call_count == 2
    client.workspace.mkdirs.assert_called_once_with("/Workspace/Users/test-user/customer_360")


def test_pagination_and_duplicate_titles():
    client = MagicMock()
    client.genie.list_spaces.side_effect = [page([], "next"), page([space()])]
    assert manage.find_space(client).space_id == "abc123"
    client.genie.list_spaces.assert_called_with(page_token="next")
    client.genie.list_spaces.side_effect = [page([space(), space()])]
    with pytest.raises(RuntimeError, match="Multiple spaces"):
        manage.find_space(client)


def test_delete_existing_and_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(manage, "ROOT", tmp_path)
    (tmp_path / ".space_id").write_text("abc123\n")
    client = MagicMock()
    client.genie.list_spaces.side_effect = [page([space()]), page()]
    manage.delete(client)
    manage.delete(client)
    client.genie.trash_space.assert_called_once_with("abc123")
    assert not (tmp_path / ".space_id").exists()


def test_api_error_propagates():
    client = MagicMock()
    client.genie.list_spaces.side_effect = RuntimeError("permission denied")
    with pytest.raises(RuntimeError, match="permission denied"):
        manage.deploy(client)
    client.genie.create_space.assert_not_called()


def test_conversation_without_sql_fails():
    client = MagicMock()
    client.genie.start_conversation_and_wait.return_value.attachments = []
    with pytest.raises(AssertionError, match="No SQL"):
        verify_space.ask(client, "abc123", "question")


def test_conversation_empty_results_fail():
    client = MagicMock()
    message = client.genie.start_conversation_and_wait.return_value
    message.attachments = [SimpleNamespace(query=True, attachment_id="attachment")]
    result = client.genie.get_message_attachment_query_result.return_value
    result.statement_response.result.data_array = []
    with pytest.raises(AssertionError, match="No result rows"):
        verify_space.ask(client, "abc123", "question")


def test_acceptance_handles_quoted_identifiers():
    evidence = [{"queries": [{"sql": "SELECT * FROM `demo_redshift`.`customer_360`.`customer_health`"}]},
                {"queries": [{"sql": "SELECT * FROM demo_redshift.customer_360.customer_health_metrics",
                              "columns": ["revenue_at_risk"], "rows": [["1327164.70"]]}]},
                {"queries": [{"sql": "SELECT MEASURE(net_revenue) FROM demo_redshift.customer_360.revenue_metrics WHERE fiscal_year=2025 AND fiscal_quarter='Q3'"}]}]
    verify_space.validate(evidence)
    evidence[1]["queries"][0]["rows"] = [["0"]]
    with pytest.raises(AssertionError):
        verify_space.validate(evidence)
