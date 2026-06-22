"""
Episodic memory example — connecting to real Postgres, Weaviate, and ArangoDB.

Episodic memory stores time-bound experiences tied to a session and agent.
It supports:
  - Semantic similarity search (Weaviate)
  - Filtering by session / agent / outcome / importance (Postgres)
  - Episode graph traversal (ArangoDB)

Run:
    python examples/example_episodic.py
"""
from db_config import make_config

from agentic_memory.agent_memory import AgentMemory
from agentic_memory.models import Outcome


def main():
    cfg = make_config()

    with AgentMemory(cfg) as mem:
        # ── Store a few episodes ────────────────────────────────────────
        e1 = mem.remember_episode(
            "User asked about the weather forecast for Paris this weekend.",
            session_id="session-42",
            agent_id="weather-agent",
            context={"user": "alice", "channel": "chat"},
            outcome=Outcome.SUCCESS,
            importance=0.6,
        )
        e2 = mem.remember_episode(
            "Failed to fetch live traffic data — external API timed out.",
            session_id="session-42",
            agent_id="travel-agent",
            context={"user": "alice", "api": "traffic-v2"},
            outcome=Outcome.FAILURE,
            importance=0.8,
        )
        e3 = mem.remember_episode(
            "User confirmed booking for a Paris hotel on Saturday.",
            session_id="session-42",
            agent_id="booking-agent",
            context={"user": "alice", "hotel_id": "HTL-9821"},
            outcome=Outcome.SUCCESS,
            importance=0.9,
        )
        print(f"Stored episodes: {e1.id}, {e2.id}, {e3.id}")

        # ── Link related episodes in ArangoDB ───────────────────────────
        mem.episodic.link_episodes(e1.id, e3.id, relation="led_to_booking")

        # ── Semantic search ─────────────────────────────────────────────
        print("\n[Semantic search] 'Paris travel plans':")
        for ep in mem.episodic.search("Paris travel plans", top_k=3):
            print(f"  score={ep.score:.3f}  outcome={ep.outcome.value}  {ep.content[:70]}")

        # ── Filter by session ───────────────────────────────────────────
        print(f"\n[By session] session-42:")
        for ep in mem.episodic.get_by_session("session-42"):
            print(f"  [{ep.outcome.value}] {ep.content[:70]}")

        # ── Filter by outcome ───────────────────────────────────────────
        print(f"\n[By outcome] FAILURE:")
        for ep in mem.episodic.get_by_outcome(Outcome.FAILURE):
            print(f"  importance={ep.importance}  {ep.content[:70]}")

        # ── High-importance episodes ─────────────────────────────────────
        print(f"\n[High importance >= 0.8]:")
        for ep in mem.episodic.get_high_importance(threshold=0.8):
            print(f"  importance={ep.importance}  {ep.content[:70]}")

        # ── Graph traversal ─────────────────────────────────────────────
        print(f"\n[Related to e1 via ArangoDB]:")
        for node in mem.episodic.get_related_episodes(e1.id):
            print(f"  {node.get('content', '')[:70]}")


if __name__ == "__main__":
    main()
