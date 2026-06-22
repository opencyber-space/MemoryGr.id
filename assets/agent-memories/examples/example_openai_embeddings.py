"""
OpenAI embeddings example.

Shows two ways to use OpenAI embeddings with AgentMemory:

  1. Default EmbeddingProvider  — uses OpenAI out of the box
  2. Custom embed_fn callback   — wrap any embedding function you like

Prerequisites:
    pip install openai
    export OPENAI_API_KEY=sk-...

Run:
    python examples/example_openai_embeddings.py
"""
import os

from db_config import make_config

from agentic_memory.agent_memory import AgentMemory
from agentic_memory.embeddings import EmbeddingProvider
from agentic_memory.models import Outcome


# ── Option 1: default EmbeddingProvider (OpenAI) ────────────────────────────

def demo_openai_provider():
    print("=== EmbeddingProvider (OpenAI) ===")
    cfg = make_config()
    embedder = EmbeddingProvider(
        model="text-embedding-3-small",
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    with AgentMemory(cfg, embedder=embedder) as mem:
        mem.remember_episode(
            "User asked for a code review on their Python project.",
            session_id="s-openai-1",
            agent_id="code-agent",
            outcome=Outcome.SUCCESS,
            importance=0.7,
        )
        mem.know_fact("Python", "is_a", "programming language", confidence=1.0)

        results = mem.recall("programming review assistance")
        for kind, items in results.items():
            if items:
                print(f"  [{kind}] top hit: {items[0].content[:60]}")


# ── Option 2: custom embed_fn callback ──────────────────────────────────────

def demo_custom_callback():
    print("\n=== Custom embed_fn callback ===")

    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def my_embed(text: str):
        resp = client.embeddings.create(model="text-embedding-3-small", input=text)
        return resp.data[0].embedding

    cfg = make_config()
    embedder = EmbeddingProvider(embed_fn=my_embed, dim=1536)

    with AgentMemory(cfg, embedder=embedder) as mem:
        mem.reflect(
            content="OpenAI embeddings capture richer semantic relationships.",
            lesson="Use domain-tuned embeddings for specialised agents.",
            confidence=0.85,
        )
        results = mem.reflective.search("embedding model quality", top_k=2)
        for ref in results:
            print(f"  score={ref.score:.3f}  lesson={ref.lesson[:60]}")


if __name__ == "__main__":
    demo_openai_provider()
    demo_custom_callback()
