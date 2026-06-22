"""Tests for ReflectiveMemoryStore."""
from datetime import datetime

import pytest

from agentic_memory.memory_types.reflective import ReflectiveMemoryStore
from agentic_memory.models import ReflectiveMemory


def _row(overrides=None):
    base = {
        "id": "ref-001",
        "source_episode_id": "ep-001",
        "content": "I should ask for clarification before acting",
        "lesson": "Always clarify ambiguous requests",
        "improvement_suggestion": "Add a clarification step to all procedures",
        "confidence": 0.9,
        "applied_count": 3,
        "metadata": {},
        "created_at": datetime(2026, 1, 1),
    }
    if overrides:
        base.update(overrides)
    return base


def _memory(**kwargs):
    defaults = dict(
        content="I should ask for clarification",
        lesson="Clarify before acting",
        improvement_suggestion="Add clarification step",
        source_episode_id="ep-001",
        confidence=0.9,
    )
    defaults.update(kwargs)
    return ReflectiveMemory(**defaults)


class TestStore:
    def test_embeds_content_lesson_suggestion(self, store_kwargs, mock_embedder):
        store = ReflectiveMemoryStore(**store_kwargs)
        store.store(_memory())
        text = mock_embedder.embed.call_args[0][0]
        assert "clarification" in text.lower()

    def test_inserts_postgres(self, store_kwargs, mock_postgres):
        store = ReflectiveMemoryStore(**store_kwargs)
        store.store(_memory())
        sql = mock_postgres.execute.call_args[0][0]
        assert "INSERT INTO reflective_memories" in sql

    def test_inserts_weaviate(self, store_kwargs, mock_weaviate):
        store = ReflectiveMemoryStore(**store_kwargs)
        mem = _memory()
        store.store(mem)
        mock_weaviate.insert.assert_called_once_with("reflective", mem.id, mem.embedding)

    def test_inserts_arango_node(self, store_kwargs, mock_arango):
        store = ReflectiveMemoryStore(**store_kwargs)
        mem = _memory()
        store.store(mem)
        call_args = mock_arango.insert_node.call_args[0]
        assert call_args[0] == "reflective"
        assert call_args[1]["_key"] == mem.id

    def test_creates_episode_reflection_edge_when_source_provided(self, store_kwargs, mock_arango):
        store = ReflectiveMemoryStore(**store_kwargs)
        mem = _memory(source_episode_id="ep-001")
        store.store(mem)
        mock_arango.insert_edge.assert_called_once()
        edge_args = mock_arango.insert_edge.call_args[0]
        assert edge_args[0] == "episode_reflection"
        assert edge_args[2] == "ep-001"

    def test_no_edge_when_no_source(self, store_kwargs, mock_arango):
        store = ReflectiveMemoryStore(**store_kwargs)
        mem = _memory(source_episode_id=None)
        store.store(mem)
        mock_arango.insert_edge.assert_not_called()


class TestRetrieve:
    def test_returns_none_when_missing(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = None
        store = ReflectiveMemoryStore(**store_kwargs)
        assert store.retrieve("missing") is None

    def test_deserialises_correctly(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = _row()
        store = ReflectiveMemoryStore(**store_kwargs)
        mem = store.retrieve("ref-001")
        assert mem.id == "ref-001"
        assert mem.lesson == "Always clarify ambiguous requests"
        assert mem.confidence == 0.9
        assert mem.applied_count == 3
        assert mem.source_episode_id == "ep-001"


class TestSearch:
    def test_returns_scored_results(self, store_kwargs, mock_weaviate, mock_postgres):
        mock_weaviate.search.return_value = [("ref-001", 0.87)]
        mock_postgres.execute_one.return_value = _row()
        store = ReflectiveMemoryStore(**store_kwargs)
        results = store.search("ask for clarification")
        assert results[0].score == 0.87

    def test_empty_on_no_hits(self, store_kwargs, mock_weaviate):
        mock_weaviate.search.return_value = []
        store = ReflectiveMemoryStore(**store_kwargs)
        assert store.search("anything") == []


class TestUpdate:
    def test_updates_all_backends(self, store_kwargs, mock_postgres, mock_weaviate, mock_arango):
        store = ReflectiveMemoryStore(**store_kwargs)
        mem = _memory()
        mem.id = "ref-001"
        store.update(mem)
        assert "UPDATE reflective_memories" in mock_postgres.execute.call_args[0][0]
        mock_weaviate.update.assert_called_once()
        mock_arango.update_node.assert_called_once()


class TestDelete:
    def test_deletes_all_backends(self, store_kwargs, mock_postgres, mock_weaviate, mock_arango):
        store = ReflectiveMemoryStore(**store_kwargs)
        store.delete("ref-001")
        assert "DELETE FROM reflective_memories" in mock_postgres.execute.call_args[0][0]
        mock_weaviate.delete.assert_called_once_with("reflective", "ref-001")
        mock_arango.delete_node.assert_called_once_with("reflective", "ref-001")


class TestMarkApplied:
    def test_increments_counter_in_postgres(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = {"applied_count": 4}
        store = ReflectiveMemoryStore(**store_kwargs)
        store.mark_applied("ref-001")
        sql = mock_postgres.execute.call_args[0][0]
        assert "applied_count" in sql and "reflective_memories" in sql

    def test_syncs_arango_node(self, store_kwargs, mock_postgres, mock_arango):
        mock_postgres.execute_one.return_value = {"applied_count": 5}
        store = ReflectiveMemoryStore(**store_kwargs)
        store.mark_applied("ref-001")
        mock_arango.update_node.assert_called_once_with("reflective", "ref-001", {"applied_count": 5})


class TestFilters:
    def test_get_from_episode(self, store_kwargs, mock_postgres):
        mock_postgres.execute.return_value = [_row()]
        store = ReflectiveMemoryStore(**store_kwargs)
        results = store.get_from_episode("ep-001")
        assert len(results) == 1
        sql = mock_postgres.execute.call_args[0][0]
        assert "source_episode_id" in sql

    def test_get_most_applied(self, store_kwargs, mock_postgres):
        mock_postgres.execute.return_value = [_row({"applied_count": 10})]
        store = ReflectiveMemoryStore(**store_kwargs)
        results = store.get_most_applied(limit=5)
        assert results[0].applied_count == 10

    def test_get_above_confidence(self, store_kwargs, mock_postgres):
        mock_postgres.execute.return_value = [_row({"confidence": 0.95})]
        store = ReflectiveMemoryStore(**store_kwargs)
        results = store.get_above_confidence(0.8)
        assert results[0].confidence == 0.95

    def test_get_reflections_for_episode(self, store_kwargs, mock_arango):
        mock_arango.get_related.return_value = [{"_key": "ref-001"}]
        store = ReflectiveMemoryStore(**store_kwargs)
        results = store.get_reflections_for_episode("ep-001")
        assert results == [{"_key": "ref-001"}]
        mock_arango.get_related.assert_called_with("episodic", "ep-001", "episode_reflection")
