"""Tests for SemanticMemoryStore."""
from datetime import datetime

import pytest

from agentic_memory.memory_types.semantic import SemanticMemoryStore
from agentic_memory.models import SemanticMemory


def _row(overrides=None):
    base = {
        "id": "sem-001",
        "subject": "Paris",
        "predicate": "is_capital_of",
        "object": "France",
        "confidence": 0.99,
        "source": "wikipedia",
        "content": "Paris is_capital_of France",
        "metadata": {},
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
    }
    if overrides:
        base.update(overrides)
    return base


class TestStore:
    def test_embeds_triple_and_content(self, store_kwargs, mock_embedder):
        store = SemanticMemoryStore(**store_kwargs)
        mem = SemanticMemory(subject="Paris", predicate="is_capital_of", object="France", content="Paris is capital of France")
        store.store(mem)
        call_text = mock_embedder.embed.call_args[0][0]
        assert "Paris" in call_text and "is_capital_of" in call_text

    def test_inserts_postgres(self, store_kwargs, mock_postgres):
        store = SemanticMemoryStore(**store_kwargs)
        mem = SemanticMemory(subject="A", predicate="rel", object="B", content="A rel B")
        store.store(mem)
        sql = mock_postgres.execute.call_args[0][0]
        assert "INSERT INTO semantic_memories" in sql

    def test_inserts_weaviate(self, store_kwargs, mock_weaviate):
        store = SemanticMemoryStore(**store_kwargs)
        mem = SemanticMemory(subject="A", predicate="rel", object="B", content="x")
        store.store(mem)
        mock_weaviate.insert.assert_called_once_with("semantic", mem.id, mem.embedding)

    def test_ensures_entity_nodes(self, store_kwargs, mock_arango):
        store = SemanticMemoryStore(**store_kwargs)
        mem = SemanticMemory(subject="Paris", predicate="is_capital_of", object="France", content="x")
        store.store(mem)
        # Two entity nodes should be ensured (Paris, France)
        entity_calls = [c for c in mock_arango.insert_node.call_args_list if c[0][0] == "entity"]
        assert len(entity_calls) == 2

    def test_creates_entity_edge(self, store_kwargs, mock_arango):
        store = SemanticMemoryStore(**store_kwargs)
        mem = SemanticMemory(subject="Paris", predicate="is_capital_of", object="France", content="x")
        store.store(mem)
        mock_arango.insert_edge.assert_called()
        edge_call = mock_arango.insert_edge.call_args[0]
        assert edge_call[0] == "entity_relations"


class TestRetrieve:
    def test_returns_none_when_missing(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = None
        store = SemanticMemoryStore(**store_kwargs)
        assert store.retrieve("missing") is None

    def test_deserialises_correctly(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = _row()
        store = SemanticMemoryStore(**store_kwargs)
        mem = store.retrieve("sem-001")
        assert mem.subject == "Paris"
        assert mem.predicate == "is_capital_of"
        assert mem.object == "France"
        assert mem.confidence == 0.99
        assert mem.source == "wikipedia"


class TestSearch:
    def test_returns_scored_results(self, store_kwargs, mock_weaviate, mock_postgres):
        mock_weaviate.search.return_value = [("sem-001", 0.95)]
        mock_postgres.execute_one.return_value = _row()
        store = SemanticMemoryStore(**store_kwargs)
        results = store.search("capital cities")
        assert results[0].score == 0.95

    def test_skips_missing(self, store_kwargs, mock_weaviate, mock_postgres):
        mock_weaviate.search.return_value = [("missing", 0.9)]
        mock_postgres.execute_one.return_value = None
        store = SemanticMemoryStore(**store_kwargs)
        assert store.search("query") == []


class TestUpdate:
    def test_updates_all_backends(self, store_kwargs, mock_postgres, mock_weaviate, mock_arango):
        store = SemanticMemoryStore(**store_kwargs)
        mem = SemanticMemory(id="sem-001", subject="X", predicate="p", object="Y", content="X p Y")
        store.update(mem)
        assert "UPDATE semantic_memories" in mock_postgres.execute.call_args[0][0]
        mock_weaviate.update.assert_called_once()
        mock_arango.update_node.assert_called_once()

    def test_sets_updated_at(self, store_kwargs):
        store = SemanticMemoryStore(**store_kwargs)
        mem = SemanticMemory(id="sem-001", subject="X", predicate="p", object="Y", content="x")
        assert mem.updated_at is None
        store.update(mem)
        assert mem.updated_at is not None


class TestDelete:
    def test_deletes_all_backends(self, store_kwargs, mock_postgres, mock_weaviate, mock_arango):
        store = SemanticMemoryStore(**store_kwargs)
        store.delete("sem-001")
        assert "DELETE FROM semantic_memories" in mock_postgres.execute.call_args[0][0]
        mock_weaviate.delete.assert_called_once_with("semantic", "sem-001")
        mock_arango.delete_node.assert_called_once_with("semantic", "sem-001")


class TestTripleLookups:
    def test_get_by_subject(self, store_kwargs, mock_postgres):
        mock_postgres.execute.return_value = [_row()]
        store = SemanticMemoryStore(**store_kwargs)
        results = store.get_by_subject("Paris")
        assert len(results) == 1
        assert "subject" in mock_postgres.execute.call_args[0][0]

    def test_get_by_predicate(self, store_kwargs, mock_postgres):
        mock_postgres.execute.return_value = [_row()]
        store = SemanticMemoryStore(**store_kwargs)
        results = store.get_by_predicate("is_capital_of")
        assert len(results) == 1

    def test_get_triple(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = _row()
        store = SemanticMemoryStore(**store_kwargs)
        mem = store.get_triple("Paris", "is_capital_of")
        assert mem is not None
        assert mem.object == "France"

    def test_get_triple_returns_none_when_missing(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = None
        store = SemanticMemoryStore(**store_kwargs)
        assert store.get_triple("Unknown", "rel") is None


class TestKnowledgeGraph:
    def test_find_path_delegates_to_arango(self, store_kwargs, mock_arango):
        mock_arango.find_entity_path.return_value = [{"vertex": "X"}]
        store = SemanticMemoryStore(**store_kwargs)
        path = store.find_path("Paris", "France")
        assert mock_arango.find_entity_path.called

    def test_get_neighbors_delegates_to_arango(self, store_kwargs, mock_arango):
        mock_arango.get_related.return_value = [{"name": "France"}]
        store = SemanticMemoryStore(**store_kwargs)
        neighbors = store.get_neighbors("Paris")
        assert neighbors == [{"name": "France"}]
