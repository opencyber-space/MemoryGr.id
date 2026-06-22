from typing import Dict, List, Optional

import redis

from ..config import RedisConfig


class RedisClient:
    def __init__(self, config: RedisConfig):
        self._client = redis.Redis(
            host=config.host,
            port=config.port,
            password=config.password or None,
            db=config.db,
            decode_responses=True,
        )

    # ------------------------------------------------------------------
    # String ops (kept for backwards compatibility)
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[str]:
        return self._client.get(key)

    def set(self, key: str, value: str) -> None:
        self._client.set(key, value)

    def delete(self, *keys: str) -> None:
        self._client.delete(*keys)

    # ------------------------------------------------------------------
    # Hash ops
    # ------------------------------------------------------------------

    def hget(self, key: str, field: str) -> Optional[str]:
        return self._client.hget(key, field)

    def hset(self, key: str, field: str, value: str) -> None:
        self._client.hset(key, field, value)

    def hmget(self, key: str, fields: List[str]) -> List[Optional[str]]:
        return self._client.hmget(key, fields)

    def hmset_dict(self, key: str, mapping: Dict[str, str]) -> None:
        self._client.hset(key, mapping=mapping)

    def hdel(self, key: str, *fields: str) -> int:
        return self._client.hdel(key, *fields)

    def hgetall(self, key: str) -> Dict[str, str]:
        return self._client.hgetall(key)

    def hkeys(self, key: str) -> List[str]:
        return self._client.hkeys(key)

    def hexists(self, key: str, field: str) -> bool:
        return bool(self._client.hexists(key, field))

    def hsetnx(self, key: str, field: str, value: str) -> bool:
        return bool(self._client.hsetnx(key, field, value))

    def expire(self, key: str, seconds: int) -> None:
        self._client.expire(key, seconds)

    # ------------------------------------------------------------------

    def close(self) -> None:
        self._client.close()
