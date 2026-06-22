"""Tests for RewardMemoryStore."""
from datetime import datetime

import pytest

from agentic_memory.memory_types.reward import RewardMemoryStore
from agentic_memory.models import RewardMemory


def _row(overrides=None):
    base = {
        "id": "rw-001",
        "state_description": "battery level is low",
        "action": "recharge",
        "reward": 1.0,
        "outcome": "battery full",
        "policy": "default",
        "context": {"level": 5},
        "metadata": {},
        "created_at": datetime(2026, 1, 1),
    }
    if overrides:
        base.update(overrides)
    return base


def _memory(**kwargs):
    defaults = dict(
        content="battery level is low",
        state_description="battery level is low",
        action="recharge",
        reward=1.0,
        outcome="battery full",
        policy="default",
    )
    defaults.update(kwargs)
    return RewardMemory(**defaults)


class TestStore:
    def test_embeds_state_action_outcome(self, store_kwargs, mock_embedder):
        store = RewardMemoryStore(**store_kwargs)
        store.store(_memory())
        text = mock_embedder.embed.call_args[0][0]
        assert "battery" in text and "recharge" in text

    def test_inserts_postgres(self, store_kwargs, mock_postgres):
        store = RewardMemoryStore(**store_kwargs)
        store.store(_memory())
        sql = mock_postgres.execute.call_args[0][0]
        assert "INSERT INTO reward_memories" in sql

    def test_inserts_weaviate(self, store_kwargs, mock_weaviate):
        store = RewardMemoryStore(**store_kwargs)
        mem = _memory()
        store.store(mem)
        mock_weaviate.insert.assert_called_once_with("reward", mem.id, mem.embedding)

    def test_inserts_arango_node(self, store_kwargs, mock_arango):
        store = RewardMemoryStore(**store_kwargs)
        mem = _memory()
        store.store(mem)
        call_args = mock_arango.insert_node.call_args[0]
        assert call_args[0] == "reward"
        assert call_args[1]["action"] == "recharge"
        assert call_args[1]["reward"] == 1.0


class TestRetrieve:
    def test_returns_none_when_missing(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = None
        store = RewardMemoryStore(**store_kwargs)
        assert store.retrieve("missing") is None

    def test_deserialises_correctly(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = _row()
        store = RewardMemoryStore(**store_kwargs)
        mem = store.retrieve("rw-001")
        assert mem.state_description == "battery level is low"
        assert mem.action == "recharge"
        assert mem.reward == 1.0
        assert mem.policy == "default"
        assert mem.context == {"level": 5}


class TestSearch:
    def test_returns_scored_results(self, store_kwargs, mock_weaviate, mock_postgres):
        mock_weaviate.search.return_value = [("rw-001", 0.93)]
        mock_postgres.execute_one.return_value = _row()
        store = RewardMemoryStore(**store_kwargs)
        results = store.search("low battery")
        assert results[0].score == 0.93
        assert results[0].action == "recharge"


class TestUpdate:
    def test_updates_all_backends(self, store_kwargs, mock_postgres, mock_weaviate, mock_arango):
        store = RewardMemoryStore(**store_kwargs)
        mem = _memory()
        mem.id = "rw-001"
        store.update(mem)
        assert "UPDATE reward_memories" in mock_postgres.execute.call_args[0][0]
        mock_weaviate.update.assert_called_once()
        mock_arango.update_node.assert_called_once()


class TestDelete:
    def test_deletes_all_backends(self, store_kwargs, mock_postgres, mock_weaviate, mock_arango):
        store = RewardMemoryStore(**store_kwargs)
        store.delete("rw-001")
        assert "DELETE FROM reward_memories" in mock_postgres.execute.call_args[0][0]
        mock_weaviate.delete.assert_called_once_with("reward", "rw-001")
        mock_arango.delete_node.assert_called_once_with("reward", "rw-001")


class TestGetBestAction:
    def _setup_search(self, mock_weaviate, mock_postgres, candidates):
        """candidates: list of (id, score, action, reward) tuples"""
        mock_weaviate.search.return_value = [(c[0], c[1]) for c in candidates]
        rows = {c[0]: _row({"id": c[0], "action": c[2], "reward": c[3]}) for c in candidates}
        mock_postgres.execute_one.side_effect = lambda sql, params: rows.get(params[0])

    def test_returns_highest_avg_reward_action(self, store_kwargs, mock_weaviate, mock_postgres):
        self._setup_search(mock_weaviate, mock_postgres, [
            ("rw-001", 0.9, "recharge", 1.0),
            ("rw-002", 0.85, "recharge", 0.8),
            ("rw-003", 0.8, "idle", 0.2),
        ])
        store = RewardMemoryStore(**store_kwargs)
        result = store.get_best_action("battery level is low")
        assert result is not None
        action, avg_reward = result
        assert action == "recharge"
        assert abs(avg_reward - 0.9) < 1e-9

    def test_returns_none_when_no_candidates(self, store_kwargs, mock_weaviate):
        mock_weaviate.search.return_value = []
        store = RewardMemoryStore(**store_kwargs)
        assert store.get_best_action("unknown state") is None

    def test_filters_by_policy(self, store_kwargs, mock_weaviate, mock_postgres):
        mock_weaviate.search.return_value = [("rw-001", 0.9), ("rw-002", 0.85)]
        mock_postgres.execute_one.side_effect = [
            _row({"id": "rw-001", "action": "recharge", "reward": 1.0, "policy": "default"}),
            _row({"id": "rw-002", "action": "idle", "reward": 0.5, "policy": "conservative"}),
        ]
        store = RewardMemoryStore(**store_kwargs)
        action, _ = store.get_best_action("low battery", policy="default")
        assert action == "recharge"


class TestActionStats:
    def test_returns_per_action_stats(self, store_kwargs, mock_postgres):
        mock_postgres.execute.return_value = [
            {"action": "recharge", "count": 5, "avg_reward": 0.9, "max_reward": 1.0, "min_reward": 0.7},
            {"action": "idle", "count": 3, "avg_reward": 0.2, "max_reward": 0.4, "min_reward": 0.0},
        ]
        store = RewardMemoryStore(**store_kwargs)
        stats = store.get_action_stats("default")
        assert "recharge" in stats
        assert stats["recharge"]["avg_reward"] == 0.9
        assert stats["recharge"]["count"] == 5

    def test_policy_summary(self, store_kwargs, mock_postgres):
        mock_postgres.execute_one.return_value = {
            "total": 10, "avg_reward": 0.75, "max_reward": 1.0, "min_reward": 0.0, "unique_actions": 3
        }
        store = RewardMemoryStore(**store_kwargs)
        summary = store.get_policy_summary()
        assert summary["total"] == 10
        assert summary["unique_actions"] == 3


class TestStateTransitionGraph:
    def test_record_transition_creates_edge(self, store_kwargs, mock_arango):
        store = RewardMemoryStore(**store_kwargs)
        store.record_transition("rw-001", "rw-002", "recharge")
        mock_arango.insert_edge.assert_called_once_with(
            "memory_relations", "reward", "rw-001", "reward", "rw-002",
            {"relation": "state_transition", "action": "recharge"},
        )

    def test_get_successor_states(self, store_kwargs, mock_arango):
        mock_arango.get_related.return_value = [{"_key": "rw-002"}]
        store = RewardMemoryStore(**store_kwargs)
        successors = store.get_successor_states("rw-001")
        assert successors == [{"_key": "rw-002"}]
