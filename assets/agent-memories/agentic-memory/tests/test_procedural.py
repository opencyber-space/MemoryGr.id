"""Tests for ProceduralMemoryStore."""
from datetime import datetime

import pytest

from agentic_memory.memory_types.procedural import ProceduralMemoryStore
from agentic_memory.models import ProceduralMemory, ProcedureStep


def _procedure_row(overrides=None):
    base = {
        "id": "proc-001",
        "name": "send_email",
        "description": "Sends an email via SMTP",
        "trigger_conditions": ["user requests email"],
        "success_rate": 0.9,
        "use_count": 10,
        "metadata": {},
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
    }
    if overrides:
        base.update(overrides)
    return base


def _step_rows():
    return [
        {"step_order": 0, "action": "connect_smtp", "parameters": {"host": "smtp.example.com"}, "expected_outcome": "connected"},
        {"step_order": 1, "action": "send_message", "parameters": {}, "expected_outcome": "sent"},
    ]


def _memory():
    return ProceduralMemory(
        name="send_email",
        content="Sends an email",
        trigger_conditions=["user requests email"],
        steps=[
            ProcedureStep(step_order=0, action="connect_smtp", parameters={"host": "x"}, expected_outcome="connected"),
            ProcedureStep(step_order=1, action="send_message", parameters={}, expected_outcome="sent"),
        ],
    )


class TestStore:
    def test_embeds_name_description_and_steps(self, store_kwargs, mock_embedder):
        store = ProceduralMemoryStore(**store_kwargs)
        store.store(_memory())
        text = mock_embedder.embed.call_args[0][0]
        assert "send_email" in text
        assert "connect_smtp" in text

    def test_inserts_procedure_row(self, store_kwargs, mock_postgres):
        store = ProceduralMemoryStore(**store_kwargs)
        store.store(_memory())
        calls = [c[0][0] for c in mock_postgres.execute.call_args_list]
        assert any("INSERT INTO procedures" in sql for sql in calls)

    def test_inserts_step_rows(self, store_kwargs, mock_postgres):
        store = ProceduralMemoryStore(**store_kwargs)
        mem = _memory()
        store.store(mem)
        calls = [c[0][0] for c in mock_postgres.execute.call_args_list]
        step_inserts = [sql for sql in calls if "procedure_steps" in sql]
        assert len(step_inserts) == 2

    def test_inserts_weaviate(self, store_kwargs, mock_weaviate):
        store = ProceduralMemoryStore(**store_kwargs)
        mem = _memory()
        store.store(mem)
        mock_weaviate.insert.assert_called_once_with("procedural", mem.id, mem.embedding)

    def test_inserts_arango_node(self, store_kwargs, mock_arango):
        store = ProceduralMemoryStore(**store_kwargs)
        mem = _memory()
        store.store(mem)
        mock_arango.insert_node.assert_called()
        call_args = mock_arango.insert_node.call_args[0]
        assert call_args[0] == "procedural"
        assert call_args[1]["name"] == "send_email"


class TestRetrieve:
    def test_returns_none_when_missing(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = None
        store = ProceduralMemoryStore(**store_kwargs)
        assert store.retrieve("missing") is None

    def test_deserialises_with_steps(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = _procedure_row()
        mock_postgres.execute.return_value = _step_rows()
        store = ProceduralMemoryStore(**store_kwargs)
        mem = store.retrieve("proc-001")
        assert mem.name == "send_email"
        assert mem.success_rate == 0.9
        assert mem.use_count == 10
        assert len(mem.steps) == 2
        assert mem.steps[0].action == "connect_smtp"

    def test_empty_steps_when_none(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = _procedure_row()
        mock_postgres.execute.return_value = []
        store = ProceduralMemoryStore(**store_kwargs)
        mem = store.retrieve("proc-001")
        assert mem.steps == []


class TestSearch:
    def test_returns_scored_results(self, store_kwargs, mock_weaviate, mock_postgres):
        mock_weaviate.search.return_value = [("proc-001", 0.88)]
        mock_postgres.execute_one.return_value = _procedure_row()
        mock_postgres.execute.return_value = _step_rows()
        store = ProceduralMemoryStore(**store_kwargs)
        results = store.search("send email")
        assert results[0].score == 0.88
        assert results[0].name == "send_email"


class TestUpdate:
    def test_replaces_steps(self, store_kwargs, mock_postgres):
        store = ProceduralMemoryStore(**store_kwargs)
        mem = _memory()
        mem.id = "proc-001"
        store.update(mem)
        calls = [c[0][0] for c in mock_postgres.execute.call_args_list]
        assert any("DELETE FROM procedure_steps" in sql for sql in calls)
        assert any("INSERT INTO procedure_steps" in sql for sql in calls)

    def test_updates_weaviate(self, store_kwargs, mock_weaviate):
        store = ProceduralMemoryStore(**store_kwargs)
        mem = _memory()
        mem.id = "proc-001"
        store.update(mem)
        mock_weaviate.update.assert_called_once()

    def test_sets_updated_at(self, store_kwargs):
        store = ProceduralMemoryStore(**store_kwargs)
        mem = _memory()
        assert mem.updated_at is None
        store.update(mem)
        assert mem.updated_at is not None


class TestDelete:
    def test_deletes_all_backends(self, store_kwargs, mock_postgres, mock_weaviate, mock_arango):
        store = ProceduralMemoryStore(**store_kwargs)
        store.delete("proc-001")
        assert "DELETE FROM procedures" in mock_postgres.execute.call_args[0][0]
        mock_weaviate.delete.assert_called_once_with("procedural", "proc-001")
        mock_arango.delete_node.assert_called_once_with("procedural", "proc-001")


class TestExecutionTracking:
    def test_success_increments_rate(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = {"success_rate": 0.5, "use_count": 2}
        store = ProceduralMemoryStore(**store_kwargs)
        store.record_execution("proc-001", success=True)
        update_call = mock_postgres.execute.call_args
        sql, params = update_call[0]
        assert "UPDATE procedures" in sql
        new_rate, new_count = params[0], params[1]
        # (0.5*2 + 1.0) / 3 = 0.666...
        assert abs(new_rate - (2 / 3)) < 1e-9
        assert new_count == 3

    def test_failure_decrements_rate(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = {"success_rate": 1.0, "use_count": 1}
        store = ProceduralMemoryStore(**store_kwargs)
        store.record_execution("proc-001", success=False)
        sql, params = mock_postgres.execute.call_args[0]
        assert params[0] == 0.5  # (1.0*1 + 0.0) / 2

    def test_no_op_when_missing(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = None
        store = ProceduralMemoryStore(**store_kwargs)
        store.record_execution("missing", success=True)
        mock_postgres.execute.assert_not_called()


class TestFilters:
    def test_get_by_name(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = _procedure_row()
        mock_postgres.execute.return_value = []
        store = ProceduralMemoryStore(**store_kwargs)
        mem = store.get_by_name("send_email")
        assert mem is not None
        assert mem.name == "send_email"

    def test_get_top_procedures(self, store_kwargs, mock_postgres):
        mock_postgres.execute.side_effect = [[_procedure_row()], [], []]
        store = ProceduralMemoryStore(**store_kwargs)
        results = store.get_top_procedures(limit=5)
        assert len(results) >= 1
