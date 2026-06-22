import json
from typing import Any, Callable, Dict, List, Optional

from ..backends.redis_client import RedisClient


class ContextKVMemory:
    """
    Session-scoped key-value context store backed by Redis Hashes.

    Each (agent_id, session_id) pair maps to one Redis Hash, so all keys
    for a session share a single TTL and can be enumerated or wiped atomically.
    """

    def __init__(
        self,
        redis: RedisClient,
        on_get: Optional[Callable[[str, str, str, Any], None]] = None,
        on_set: Optional[Callable[[str, str, str, Any], None]] = None,
    ):
        self._redis = redis
        self._on_get = on_get
        self._on_set = on_set

    def _hash_key(self, agent_id: str, session_id: str) -> str:
        return f"{agent_id}__{session_id}"

    # ------------------------------------------------------------------
    # Core get / set
    # ------------------------------------------------------------------

    def get(self, agent_id: str, session_id: str, key: str) -> Optional[Dict[str, Any]]:
        raw = self._redis.hget(self._hash_key(agent_id, session_id), key)
        value = json.loads(raw) if raw is not None else None
        if value is not None and self._on_get:
            self._on_get(agent_id, session_id, key, value)
        return value

    def set(
        self,
        agent_id: str,
        session_id: str,
        key: str,
        data: Dict[str, Any],
        *,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        hash_key = self._hash_key(agent_id, session_id)
        self._redis.hset(hash_key, key, json.dumps(data))
        if ttl_seconds is not None:
            self._redis.expire(hash_key, ttl_seconds)
        if self._on_set:
            self._on_set(agent_id, session_id, key, data)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def delete(self, agent_id: str, session_id: str, key: str) -> None:
        """Remove a single key from the session hash."""
        self._redis.hdel(self._hash_key(agent_id, session_id), key)

    def clear(self, agent_id: str, session_id: str) -> None:
        """Delete the entire session hash atomically."""
        self._redis.delete(self._hash_key(agent_id, session_id))

    # ------------------------------------------------------------------
    # Discoverability
    # ------------------------------------------------------------------

    def exists(self, agent_id: str, session_id: str, key: str) -> bool:
        """Return True if the key is present (cheaper than get)."""
        return self._redis.hexists(self._hash_key(agent_id, session_id), key)

    def keys(self, agent_id: str, session_id: str) -> List[str]:
        """List all keys stored for a session."""
        return self._redis.hkeys(self._hash_key(agent_id, session_id))

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def get_many(
        self, agent_id: str, session_id: str, keys: List[str]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Fetch multiple keys in a single round-trip via HMGET."""
        raws = self._redis.hmget(self._hash_key(agent_id, session_id), keys)
        result: Dict[str, Optional[Dict[str, Any]]] = {}
        for k, raw in zip(keys, raws):
            value = json.loads(raw) if raw is not None else None
            result[k] = value
            if value is not None and self._on_get:
                self._on_get(agent_id, session_id, k, value)
        return result

    def set_many(
        self,
        agent_id: str,
        session_id: str,
        mapping: Dict[str, Dict[str, Any]],
        *,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Write multiple keys in a single HSET call."""
        hash_key = self._hash_key(agent_id, session_id)
        self._redis.hmset_dict(hash_key, {k: json.dumps(v) for k, v in mapping.items()})
        if ttl_seconds is not None:
            self._redis.expire(hash_key, ttl_seconds)
        if self._on_set:
            for k, v in mapping.items():
                self._on_set(agent_id, session_id, k, v)

    # ------------------------------------------------------------------
    # Snapshot / restore
    # ------------------------------------------------------------------

    def dump(self, agent_id: str, session_id: str) -> Dict[str, Any]:
        """Export all key-value pairs for a session as a plain dict."""
        return {
            k: json.loads(v)
            for k, v in self._redis.hgetall(self._hash_key(agent_id, session_id)).items()
        }

    def restore(
        self,
        agent_id: str,
        session_id: str,
        snapshot: Dict[str, Any],
        *,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Bulk-write a snapshot dict, optionally with a TTL."""
        self.set_many(agent_id, session_id, snapshot, ttl_seconds=ttl_seconds)

    # ------------------------------------------------------------------
    # Atomicity
    # ------------------------------------------------------------------

    def get_or_set(
        self,
        agent_id: str,
        session_id: str,
        key: str,
        default_factory: Callable[[], Dict[str, Any]],
        *,
        ttl_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Return the stored value for key, or compute and store it atomically.

        Uses HSETNX so only one caller wins the write race. If another writer
        wins, this call fetches and returns their value.
        """
        existing = self.get(agent_id, session_id, key)
        if existing is not None:
            return existing

        value = default_factory()
        hash_key = self._hash_key(agent_id, session_id)
        was_set = self._redis.hsetnx(hash_key, key, json.dumps(value))

        if was_set:
            if ttl_seconds is not None:
                self._redis.expire(hash_key, ttl_seconds)
            if self._on_set:
                self._on_set(agent_id, session_id, key, value)
            return value

        # Another writer won — return what they stored.
        raw = self._redis.hget(hash_key, key)
        return json.loads(raw) if raw is not None else value
