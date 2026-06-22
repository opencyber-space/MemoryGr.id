"""
Semantic memory example — connecting to real Postgres, Weaviate, and ArangoDB.

Semantic memory stores factual knowledge as subject–predicate–object triples and
builds a knowledge graph in ArangoDB for path-finding between concepts.

Run:
    python examples/example_semantic.py
"""
from db_config import make_config

from agentic_memory.agent_memory import AgentMemory


def main():
    cfg = make_config()

    with AgentMemory(cfg) as mem:
        # ── Store facts as triples ──────────────────────────────────────
        mem.know_fact("Paris",          "is_capital_of",   "France",         confidence=1.0)
        mem.know_fact("France",         "is_member_of",    "European Union", confidence=1.0)
        mem.know_fact("Eiffel Tower",   "is_located_in",   "Paris",          confidence=1.0)
        mem.know_fact("Louvre Museum",  "is_located_in",   "Paris",          confidence=1.0)
        mem.know_fact("Seine",          "flows_through",   "Paris",          confidence=1.0)
        mem.know_fact("Napoleon",       "was_born_in",     "Corsica",        confidence=1.0,
                      source="encyclopedia")
        mem.know_fact("Corsica",        "is_part_of",      "France",         confidence=1.0)
        print("Facts stored.")

        # ── Semantic similarity search ──────────────────────────────────
        print("\n[Semantic search] 'European capital famous landmarks':")
        for fact in mem.semantic.search("European capital famous landmarks", top_k=3):
            print(f"  score={fact.score:.3f}  {fact.subject} {fact.predicate} {fact.object}")

        # ── Triple lookup ────────────────────────────────────────────────
        print("\n[get_by_subject] 'Paris':")
        for fact in mem.semantic.get_by_subject("Paris"):
            print(f"  {fact.subject} {fact.predicate} {fact.object}  (confidence={fact.confidence})")

        # ── Exact triple fetch ───────────────────────────────────────────
        triple = mem.semantic.get_triple("Paris", "is_capital_of")
        if triple:
            print(f"\n[get_triple] Paris is_capital_of → {triple.object}")

        # ── Knowledge-graph neighbours ───────────────────────────────────
        print("\n[KG neighbours of Paris (OUTBOUND)]:")
        for node in mem.semantic.get_neighbors("Paris", direction="OUTBOUND"):
            print(f"  → {node.get('name', node.get('_key'))}")

        # ── Shortest path ─────────────────────────────────────────────────
        print("\n[KG path] Napoleon → European Union:")
        path = mem.semantic.find_path("Napoleon", "European Union")
        for step in path:
            print(f"  {step}")


if __name__ == "__main__":
    main()
