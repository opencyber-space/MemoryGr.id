"""
ContextKVMemory example — connecting to real Redis.

ContextKVMemory is a session-scoped key-value store backed by a Redis Hash.
Each (agent_id, session_id) pair is one hash; all keys for a session share a
single TTL and can be listed, bulk-fetched, snapshotted, or cleared atomically.

Run:
    python examples/example_context_kv.py
"""
import logging

from db_config import make_config

from agentic_memory.backends.redis_client import RedisClient
from agentic_memory.memory_types.context_kv import ContextKVMemory

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main():
    cfg = make_config()
    redis = RedisClient(cfg.redis)

    # Observability hooks — fired on every get/set
    kv = ContextKVMemory(
        redis,
        on_set=lambda aid, sid, k, v: log.debug("SET  %s/%s/%s", aid, sid, k),
        on_get=lambda aid, sid, k, v: log.debug("GET  %s/%s/%s", aid, sid, k),
    )

    agent_id = "planner-agent"
    session_id = "session-99"

    # ── Clear any leftover state from a previous run ────────────────────
    kv.clear(agent_id, session_id)
    print(f"\nCleared session {session_id!r}")

    # ── set / get with TTL ──────────────────────────────────────────────
    print("\n── set / get ──")
    kv.set(agent_id, session_id, "user_prefs", {
        "language": "en",
        "timezone": "UTC+5:30",
        "theme": "dark",
    }, ttl_seconds=600)

    kv.set(agent_id, session_id, "task_state", {
        "current_step": 2,
        "total_steps": 5,
        "last_action": "fetch_data",
        "completed": False,
    })

    prefs = kv.get(agent_id, session_id, "user_prefs")
    print(f"user_prefs: {prefs}")

    missing = kv.get(agent_id, session_id, "nonexistent_key")
    print(f"nonexistent_key -> {missing}")

    # ── exists / keys ────────────────────────────────────────────────────
    print("\n── exists / keys ──")
    print(f"exists('user_prefs'): {kv.exists(agent_id, session_id, 'user_prefs')}")
    print(f"exists('ghost'):      {kv.exists(agent_id, session_id, 'ghost')}")
    print(f"keys: {kv.keys(agent_id, session_id)}")

    # ── bulk get / set ───────────────────────────────────────────────────
    print("\n── set_many / get_many ──")
    kv.set_many(agent_id, session_id, {
        "scratch": {"notes": ["Check quota before retrying"]},
        "tool_calls": {"count": 0, "last": None},
    })

    batch = kv.get_many(agent_id, session_id, ["user_prefs", "scratch", "ghost"])
    for k, v in batch.items():
        print(f"  {k}: {v}")

    # ── get_or_set (atomic init) ─────────────────────────────────────────
    print("\n── get_or_set ──")
    call_count = {"n": 0}

    def make_default():
        call_count["n"] += 1
        return {"initialized": True, "call_count": call_count["n"]}

    # First call: key absent → factory is called, value written via HSETNX
    result1 = kv.get_or_set(agent_id, session_id, "init_flag", make_default)
    print(f"first call:  {result1}  (factory called: {call_count['n']} time(s))")

    # Second call: key present → factory is NOT called
    result2 = kv.get_or_set(agent_id, session_id, "init_flag", make_default)
    print(f"second call: {result2}  (factory called: {call_count['n']} time(s))")

    # ── snapshot: dump / clear / restore ────────────────────────────────
    print("\n── dump / clear / restore ──")
    snapshot = kv.dump(agent_id, session_id)
    print(f"snapshot keys: {list(snapshot.keys())}")

    kv.clear(agent_id, session_id)
    print(f"after clear, keys: {kv.keys(agent_id, session_id)}")

    kv.restore(agent_id, session_id, snapshot, ttl_seconds=300)
    print(f"after restore, keys: {kv.keys(agent_id, session_id)}")

    # ── delete a single key ──────────────────────────────────────────────
    print("\n── delete ──")
    kv.delete(agent_id, session_id, "scratch")
    print(f"after delete('scratch'), keys: {kv.keys(agent_id, session_id)}")

    # ── AgentMemory convenience helpers ─────────────────────────────────
    print("\n── AgentMemory.set_context / get_context ──")
    from agentic_memory import AgentMemory
    with AgentMemory(cfg) as mem:
        mem.set_context("status", {"ready": True}, agent_id=agent_id, session_id=session_id)
        val = mem.get_context("status", agent_id=agent_id, session_id=session_id)
        print(f"get_context('status'): {val}")

        results = mem.recall("step", agent_id=agent_id, session_id=session_id)
        print(f"recall context hits: {results.get('context', [])}")

    redis.close()


if __name__ == "__main__":
    main()
