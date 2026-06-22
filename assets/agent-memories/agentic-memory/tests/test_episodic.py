"""Tests for EpisodicMemoryStore."""
from datetime import datetime
from unittest.mock import call

import pytest

from agentic_memory.memory_types.episodic import EpisodicMemoryStore
from agentic_memory.models import EpisodicMemory, Outcome


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row(overrides=None):
    base = {
        "id": "ep-001",
        "content": "User asked about the weather",
        "session_id": "session-1",
        "agent_id": "agent-A",
        "context": {"location": "NYC"},
        "outcome": "success",
        "importance": 0.8,
        "metadata": {},
        "created_at": datetime(2026, 1, 1, 12, 0),
    }
    if overrides:
        base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# store()
# ---------------------------------------------------------------------------

class TestStore:
    def test_embeds_content(self, store_kwargs, mock_embedder):
        store = EpisodicMemoryStore(**store_kwargs)
        mem = EpisodicMemory(content="hello world", session_id="s1", agent_id="a1")
        store.store(mem)
        mock_embedder.embed.assert_called_once_with("hello world")

    def test_inserts_into_postgres(self, store_kwargs, mock_postgres):
        store = EpisodicMemoryStore(**store_kwargs)
        mem = EpisodicMemory(content="test", session_id="s1", agent_id="a1")
        store.store(mem)
        sql = mock_postgres.execute.call_args[0][0]
        assert "INSERT INTO episodic_memories" in sql

    def test_inserts_into_weaviate(self, store_kwargs, mock_weaviate):
        store = EpisodicMemoryStore(**store_kwargs)
        mem = EpisodicMemory(content="test", session_id="s1")
        store.store(mem)
        mock_weaviate.insert.assert_called_once_with("episodic", mem.id, mem.embedding)

    def test_inserts_node_into_arango(self, store_kwargs, mock_arango):
        store = EpisodicMemoryStore(**store_kwargs)
        mem = EpisodicMemory(content="test", session_id="s1")
        store.store(mem)
        mock_arango.insert_node.assert_called_once()
        args = mock_arango.insert_node.call_args[0]
        assert args[0] == "episodic"
        assert args[1]["_key"] == mem.id

    def test_returns_memory_id(self, store_kwargs):
        store = EpisodicMemoryStore(**store_kwargs)
        mem = EpisodicMemory(content="test")
        result = store.store(mem)
        assert result == mem.id

    def test_embedding_attached_to_memory(self, store_kwargs, mock_embedder):
        mock_embedder.embed.return_value = [0.5] * 1536
        store = EpisodicMemoryStore(**store_kwargs)
        mem = EpisodicMemory(content="test")
        store.store(mem)
        assert mem.embedding == [0.5] * 1536


# ---------------------------------------------------------------------------
# retrieve()
# ---------------------------------------------------------------------------

class TestRetrieve:
    def test_returns_none_when_not_found(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = None
        store = EpisodicMemoryStore(**store_kwargs)
        assert store.retrieve("nonexistent") is None

    def test_deserialises_row_correctly(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = _row()
        store = EpisodicMemoryStore(**store_kwargs)
        mem = store.retrieve("ep-001")
        assert mem.id == "ep-001"
        assert mem.content == "User asked about the weather"
        assert mem.session_id == "session-1"
        assert mem.agent_id == "agent-A"
        assert mem.outcome == Outcome.SUCCESS
        assert mem.importance == 0.8
        assert mem.context == {"location": "NYC"}

    def test_outcome_enum_conversion(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = _row({"outcome": "failure"})
        store = EpisodicMemoryStore(**store_kwargs)
        mem = store.retrieve("ep-001")
        assert mem.outcome == Outcome.FAILURE


# ---------------------------------------------------------------------------
# search()
# ---------------------------------------------------------------------------

class TestSearch:
    def test_empty_when_weaviate_returns_nothing(self, store_kwargs, mock_weaviate, mock_postgres):
        mock_weaviate.search.return_value = []
        store = EpisodicMemoryStore(**store_kwargs)
        results = store.search("weather")
        assert results == []

    def test_attaches_score(self, store_kwargs, mock_weaviate, mock_postgres):
        mock_weaviate.search.return_value = [("ep-001", 0.92)]
        mock_postgres.execute_one.return_value = _row()
        store = EpisodicMemoryStore(**store_kwargs)
        results = store.search("weather")
        assert len(results) == 1
        assert results[0].score == 0.92

    def test_skips_missing_ids(self, store_kwargs, mock_weaviate, mock_postgres):
        mock_weaviate.search.return_value = [("ep-missing", 0.9)]
        mock_postgres.execute_one.return_value = None
        store = EpisodicMemoryStore(**store_kwargs)
        assert store.search("query") == []


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_updates_postgres(self, store_kwargs, mock_postgres):
        store = EpisodicMemoryStore(**store_kwargs)
        mem = EpisodicMemory(id="ep-001", content="updated", session_id="s1")
        store.update(mem)
        sql = mock_postgres.execute.call_args[0][0]
        assert "UPDATE episodic_memories" in sql

    def test_updates_weaviate(self, store_kwargs, mock_weaviate):
        store = EpisodicMemoryStore(**store_kwargs)
        mem = EpisodicMemory(id="ep-001", content="updated")
        store.update(mem)
        mock_weaviate.update.assert_called_once_with("episodic", "ep-001", mem.embedding)

    def test_updates_arango(self, store_kwargs, mock_arango):
        store = EpisodicMemoryStore(**store_kwargs)
        mem = EpisodicMemory(id="ep-001", content="updated", outcome=Outcome.FAILURE)
        store.update(mem)
        mock_arango.update_node.assert_called_once()
        node_doc = mock_arango.update_node.call_args[0][2]
        assert node_doc["outcome"] == "failure"


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------

class TestDelete:
    def test_deletes_from_all_backends(self, store_kwargs, mock_postgres, mock_weaviate, mock_arango):
        store = EpisodicMemoryStore(**store_kwargs)
        store.delete("ep-001")
        assert "DELETE FROM episodic_memories" in mock_postgres.execute.call_args[0][0]
        mock_weaviate.delete.assert_called_once_with("episodic", "ep-001")
        mock_arango.delete_node.assert_called_once_with("episodic", "ep-001")


# ---------------------------------------------------------------------------
# Filtering helpers
# ---------------------------------------------------------------------------

class TestFilters:
    def test_get_by_session(self, store_kwargs, mock_postgres):
        mock_postgres.execute.return_value = [_row()]
        store = EpisodicMemoryStore(**store_kwargs)
        results = store.get_by_session("session-1")
        assert len(results) == 1
        sql = mock_postgres.execute.call_args[0][0]
        assert "session_id" in sql

    def test_get_by_agent(self, store_kwargs, mock_postgres):
        mock_postgres.execute.return_value = [_row()]
        store = EpisodicMemoryStore(**store_kwargs)
        results = store.get_by_agent("agent-A")
        assert len(results) == 1

    def test_get_by_outcome(self, store_kwargs, mock_postgres):
        mock_postgres.execute.return_value = [_row()]
        store = EpisodicMemoryStore(**store_kwargs)
        results = store.get_by_outcome(Outcome.SUCCESS)
        assert len(results) == 1

    def test_get_high_importance(self, store_kwargs, mock_postgres):
        mock_postgres.execute.return_value = [_row()]
        store = EpisodicMemoryStore(**store_kwargs)
        results = store.get_high_importance(0.7)
        assert results[0].importance >= 0.7


# ---------------------------------------------------------------------------
# Graph operations
# ---------------------------------------------------------------------------

class TestGraph:
    def test_link_episodes_creates_edge(self, store_kwargs, mock_arango):
        store = EpisodicMemoryStore(**store_kwargs)
        store.link_episodes("ep-001", "ep-002", "caused")
        mock_arango.insert_edge.assert_called_once_with(
            "memory_relations", "episodic", "ep-001", "episodic", "ep-002",
            {"relation": "caused"},
        )

    def test_get_related_episodes(self, store_kwargs, mock_arango):
        mock_arango.get_related.return_value = [{"_key": "ep-002"}]
        store = EpisodicMemoryStore(**store_kwargs)
        related = store.get_related_episodes("ep-001")
        assert related == [{"_key": "ep-002"}]
