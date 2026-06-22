"""Tests for the AgentMemory façade."""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from agentic_memory.agent_memory import AgentMemory
from agentic_memory.config import MemoryConfig
from agentic_memory.models import (
    EpisodicMemory,
    Outcome,
    ProceduralMemory,
    ReflectiveMemory,
    RewardMemory,
    SemanticMemory,
)


# ---------------------------------------------------------------------------
# Fixture: AgentMemory with all backends mocked out
# ---------------------------------------------------------------------------

@pytest.fixture
def agent(mock_weaviate, mock_arango, mock_postgres, mock_embedder):
    cfg = MemoryConfig()
    with patch("agentic_memory.agent_memory.WeaviateClient", return_value=mock_weaviate), \
         patch("agentic_memory.agent_memory.ArangoBackend", return_value=mock_arango), \
         patch("agentic_memory.agent_memory.PostgresClient", return_value=mock_postgres), \
         patch("agentic_memory.agent_memory.EmbeddingProvider", return_value=mock_embedder):
        mem = AgentMemory(cfg)
    return mem


# ---------------------------------------------------------------------------
# remember_episode()
# ---------------------------------------------------------------------------

class TestRememberEpisode:
    def test_returns_episodic_memory(self, agent, mock_postgres):
        ep = agent.remember_episode("User asked about weather", session_id="s1", agent_id="a1")
        assert isinstance(ep, EpisodicMemory)
        assert ep.content == "User asked about weather"
        assert ep.session_id == "s1"
        assert ep.agent_id == "a1"

    def test_default_outcome_is_unknown(self, agent, mock_postgres):
        ep = agent.remember_episode("something happened")
        assert ep.outcome == Outcome.UNKNOWN

    def test_custom_outcome_and_importance(self, agent, mock_postgres):
        ep = agent.remember_episode("task done", outcome=Outcome.SUCCESS, importance=0.9)
        assert ep.outcome == Outcome.SUCCESS
        assert ep.importance == 0.9

    def test_persists_to_postgres(self, agent, mock_postgres):
        agent.remember_episode("test")
        calls = [c[0][0] for c in mock_postgres.execute.call_args_list]
        assert any("episodic_memories" in sql for sql in calls)


# ---------------------------------------------------------------------------
# know_fact()
# ---------------------------------------------------------------------------

class TestKnowFact:
    def test_returns_semantic_memory(self, agent, mock_postgres, mock_arango):
        fact = agent.know_fact("Paris", "is_capital_of", "France")
        assert isinstance(fact, SemanticMemory)
        assert fact.subject == "Paris"
        assert fact.predicate == "is_capital_of"
        assert fact.object == "France"

    def test_auto_generates_content(self, agent, mock_postgres, mock_arango):
        fact = agent.know_fact("Sun", "is_a", "star")
        assert fact.content == "Sun is_a star"

    def test_explicit_content_overrides_default(self, agent, mock_postgres, mock_arango):
        fact = agent.know_fact("Sun", "is_a", "star", content="The Sun is a star")
        assert fact.content == "The Sun is a star"

    def test_confidence_default_is_one(self, agent, mock_postgres, mock_arango):
        fact = agent.know_fact("A", "rel", "B")
        assert fact.confidence == 1.0

    def test_persists_to_postgres(self, agent, mock_postgres, mock_arango):
        agent.know_fact("A", "rel", "B")
        calls = [c[0][0] for c in mock_postgres.execute.call_args_list]
        assert any("semantic_memories" in sql for sql in calls)


# ---------------------------------------------------------------------------
# learn_procedure()
# ---------------------------------------------------------------------------

class TestLearnProcedure:
    def test_returns_procedural_memory(self, agent, mock_postgres):
        proc = agent.learn_procedure("send_email", [
            {"action": "connect", "parameters": {}, "expected_outcome": "connected"},
            {"action": "send", "parameters": {}, "expected_outcome": "sent"},
        ])
        assert isinstance(proc, ProceduralMemory)
        assert proc.name == "send_email"
        assert len(proc.steps) == 2

    def test_steps_ordered_correctly(self, agent, mock_postgres):
        proc = agent.learn_procedure("two_step", [
            {"action": "first"},
            {"action": "second"},
        ])
        assert proc.steps[0].action == "first"
        assert proc.steps[0].step_order == 0
        assert proc.steps[1].step_order == 1

    def test_trigger_conditions_stored(self, agent, mock_postgres):
        proc = agent.learn_procedure("task", [], trigger_conditions=["when X"])
        assert proc.trigger_conditions == ["when X"]


# ---------------------------------------------------------------------------
# reflect()
# ---------------------------------------------------------------------------

class TestReflect:
    def test_returns_reflective_memory(self, agent, mock_postgres, mock_arango):
        ref = agent.reflect("I should clarify first", "Ask before acting")
        assert isinstance(ref, ReflectiveMemory)
        assert ref.lesson == "Ask before acting"

    def test_links_to_episode(self, agent, mock_postgres, mock_arango):
        ref = agent.reflect("lesson", "learn", source_episode_id="ep-001")
        assert ref.source_episode_id == "ep-001"

    def test_no_episode_link_by_default(self, agent, mock_postgres, mock_arango):
        ref = agent.reflect("lesson", "learn")
        assert ref.source_episode_id is None

    def test_persists_to_postgres(self, agent, mock_postgres, mock_arango):
        agent.reflect("lesson", "learn")
        calls = [c[0][0] for c in mock_postgres.execute.call_args_list]
        assert any("reflective_memories" in sql for sql in calls)


# ---------------------------------------------------------------------------
# record_reward()
# ---------------------------------------------------------------------------

class TestRecordReward:
    def test_returns_reward_memory(self, agent, mock_postgres):
        rw = agent.record_reward("battery low", "recharge", 1.0)
        assert isinstance(rw, RewardMemory)
        assert rw.state_description == "battery low"
        assert rw.action == "recharge"
        assert rw.reward == 1.0

    def test_default_policy(self, agent, mock_postgres):
        rw = agent.record_reward("state", "action", 0.5)
        assert rw.policy == "default"

    def test_custom_policy(self, agent, mock_postgres):
        rw = agent.record_reward("state", "action", 0.5, policy="greedy")
        assert rw.policy == "greedy"

    def test_negative_reward_stored(self, agent, mock_postgres):
        rw = agent.record_reward("state", "bad_action", -1.0)
        assert rw.reward == -1.0


# ---------------------------------------------------------------------------
# recall() — cross-type search
# ---------------------------------------------------------------------------

class TestRecall:
    def test_returns_dict_with_all_five_types(self, agent, mock_weaviate, mock_postgres):
        mock_weaviate.search.return_value = []
        results = agent.recall("something")
        assert set(results.keys()) == {"episodic", "semantic", "procedural", "reflective", "reward"}

    def test_all_values_are_lists(self, agent, mock_weaviate, mock_postgres):
        mock_weaviate.search.return_value = []
        results = agent.recall("query")
        for v in results.values():
            assert isinstance(v, list)

    def test_weaviate_queried_five_times(self, agent, mock_weaviate, mock_postgres):
        mock_weaviate.search.return_value = []
        agent.recall("query", top_k=3)
        assert mock_weaviate.search.call_count == 5
        for call in mock_weaviate.search.call_args_list:
            assert call[0][2] == 3


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------

class TestContextManager:
    def test_close_called_on_exit(self, agent, mock_postgres, mock_weaviate):
        with agent:
            pass
        mock_postgres.close.assert_called_once()
        mock_weaviate.disconnect.assert_called_once()
