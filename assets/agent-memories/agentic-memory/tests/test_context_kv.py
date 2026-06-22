"""Tests for ContextKVMemory — all Redis calls are mocked."""
import json
from unittest.mock import MagicMock, call

import pytest

from agentic_memory.memory_types.context_kv import ContextKVMemory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    r = MagicMock()
    r.hget.return_value = None
    r.hmget.return_value = []
    r.hgetall.return_value = {}
    r.hkeys.return_value = []
    r.hexists.return_value = False
    r.hsetnx.return_value = True
    return r


@pytest.fixture
def store(mock_redis):
    return ContextKVMemory(mock_redis)


AGENT = "agent-1"
SESSION = "session-A"
KEY = "user_prefs"
DATA = {"theme": "dark", "lang": "en"}


# ---------------------------------------------------------------------------
# _hash_key
# ---------------------------------------------------------------------------

class TestHashKey:
    def test_format(self, store):
        assert store._hash_key("a", "s") == "a__s"


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

class TestGet:
    def test_returns_none_when_missing(self, store, mock_redis):
        mock_redis.hget.return_value = None
        assert store.get(AGENT, SESSION, KEY) is None

    def test_deserialises_json(self, store, mock_redis):
        mock_redis.hget.return_value = json.dumps(DATA)
        assert store.get(AGENT, SESSION, KEY) == DATA

    def test_calls_hget_with_correct_args(self, store, mock_redis):
        store.get(AGENT, SESSION, KEY)
        mock_redis.hget.assert_called_once_with(f"{AGENT}__{SESSION}", KEY)

    def test_on_get_hook_called_when_value_exists(self, mock_redis):
        hook = MagicMock()
        s = ContextKVMemory(mock_redis, on_get=hook)
        mock_redis.hget.return_value = json.dumps(DATA)
        s.get(AGENT, SESSION, KEY)
        hook.assert_called_once_with(AGENT, SESSION, KEY, DATA)

    def test_on_get_hook_not_called_when_missing(self, mock_redis):
        hook = MagicMock()
        s = ContextKVMemory(mock_redis, on_get=hook)
        mock_redis.hget.return_value = None
        s.get(AGENT, SESSION, KEY)
        hook.assert_not_called()


# ---------------------------------------------------------------------------
# set
# ---------------------------------------------------------------------------

class TestSet:
    def test_serialises_and_calls_hset(self, store, mock_redis):
        store.set(AGENT, SESSION, KEY, DATA)
        mock_redis.hset.assert_called_once_with(f"{AGENT}__{SESSION}", KEY, json.dumps(DATA))

    def test_sets_ttl_when_provided(self, store, mock_redis):
        store.set(AGENT, SESSION, KEY, DATA, ttl_seconds=60)
        mock_redis.expire.assert_called_once_with(f"{AGENT}__{SESSION}", 60)

    def test_no_expire_call_without_ttl(self, store, mock_redis):
        store.set(AGENT, SESSION, KEY, DATA)
        mock_redis.expire.assert_not_called()

    def test_on_set_hook_called(self, mock_redis):
        hook = MagicMock()
        s = ContextKVMemory(mock_redis, on_set=hook)
        s.set(AGENT, SESSION, KEY, DATA)
        hook.assert_called_once_with(AGENT, SESSION, KEY, DATA)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:
    def test_calls_hdel(self, store, mock_redis):
        store.delete(AGENT, SESSION, KEY)
        mock_redis.hdel.assert_called_once_with(f"{AGENT}__{SESSION}", KEY)


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------

class TestClear:
    def test_calls_delete_on_hash_key(self, store, mock_redis):
        store.clear(AGENT, SESSION)
        mock_redis.delete.assert_called_once_with(f"{AGENT}__{SESSION}")


# ---------------------------------------------------------------------------
# exists
# ---------------------------------------------------------------------------

class TestExists:
    def test_returns_false_when_missing(self, store, mock_redis):
        mock_redis.hexists.return_value = False
        assert store.exists(AGENT, SESSION, KEY) is False

    def test_returns_true_when_present(self, store, mock_redis):
        mock_redis.hexists.return_value = True
        assert store.exists(AGENT, SESSION, KEY) is True

    def test_calls_hexists_with_correct_args(self, store, mock_redis):
        store.exists(AGENT, SESSION, KEY)
        mock_redis.hexists.assert_called_once_with(f"{AGENT}__{SESSION}", KEY)


# ---------------------------------------------------------------------------
# keys
# ---------------------------------------------------------------------------

class TestKeys:
    def test_returns_empty_list_for_unknown_session(self, store, mock_redis):
        mock_redis.hkeys.return_value = []
        assert store.keys(AGENT, SESSION) == []

    def test_returns_field_names(self, store, mock_redis):
        mock_redis.hkeys.return_value = ["k1", "k2"]
        assert store.keys(AGENT, SESSION) == ["k1", "k2"]


# ---------------------------------------------------------------------------
# get_many
# ---------------------------------------------------------------------------

class TestGetMany:
    def test_returns_dict_with_none_for_missing(self, store, mock_redis):
        mock_redis.hmget.return_value = [None, None]
        result = store.get_many(AGENT, SESSION, ["a", "b"])
        assert result == {"a": None, "b": None}

    def test_deserialises_present_values(self, store, mock_redis):
        mock_redis.hmget.return_value = [json.dumps(DATA), None]
        result = store.get_many(AGENT, SESSION, ["k1", "k2"])
        assert result["k1"] == DATA
        assert result["k2"] is None

    def test_on_get_hook_called_for_each_present(self, mock_redis):
        hook = MagicMock()
        s = ContextKVMemory(mock_redis, on_get=hook)
        mock_redis.hmget.return_value = [json.dumps(DATA), None]
        s.get_many(AGENT, SESSION, ["k1", "k2"])
        hook.assert_called_once_with(AGENT, SESSION, "k1", DATA)


# ---------------------------------------------------------------------------
# set_many
# ---------------------------------------------------------------------------

class TestSetMany:
    def test_calls_hmset_dict(self, store, mock_redis):
        mapping = {"k1": {"v": 1}, "k2": {"v": 2}}
        store.set_many(AGENT, SESSION, mapping)
        expected = {k: json.dumps(v) for k, v in mapping.items()}
        mock_redis.hmset_dict.assert_called_once_with(f"{AGENT}__{SESSION}", expected)

    def test_sets_ttl_when_provided(self, store, mock_redis):
        store.set_many(AGENT, SESSION, {"k": {"v": 1}}, ttl_seconds=120)
        mock_redis.expire.assert_called_once_with(f"{AGENT}__{SESSION}", 120)

    def test_on_set_hook_called_for_each(self, mock_redis):
        hook = MagicMock()
        s = ContextKVMemory(mock_redis, on_set=hook)
        mapping = {"k1": {"a": 1}, "k2": {"b": 2}}
        s.set_many(AGENT, SESSION, mapping)
        assert hook.call_count == 2


# ---------------------------------------------------------------------------
# dump / restore
# ---------------------------------------------------------------------------

class TestDump:
    def test_returns_empty_dict_for_unknown_session(self, store, mock_redis):
        mock_redis.hgetall.return_value = {}
        assert store.dump(AGENT, SESSION) == {}

    def test_deserialises_all_fields(self, store, mock_redis):
        mock_redis.hgetall.return_value = {
            "k1": json.dumps({"x": 1}),
            "k2": json.dumps({"y": 2}),
        }
        result = store.dump(AGENT, SESSION)
        assert result == {"k1": {"x": 1}, "k2": {"y": 2}}


class TestRestore:
    def test_delegates_to_set_many(self, store, mock_redis):
        snapshot = {"k1": {"x": 1}}
        store.restore(AGENT, SESSION, snapshot)
        mock_redis.hmset_dict.assert_called_once()

    def test_passes_ttl(self, store, mock_redis):
        store.restore(AGENT, SESSION, {"k": {"v": 1}}, ttl_seconds=300)
        mock_redis.expire.assert_called_once_with(f"{AGENT}__{SESSION}", 300)


# ---------------------------------------------------------------------------
# get_or_set
# ---------------------------------------------------------------------------

class TestGetOrSet:
    def test_returns_existing_value_without_calling_factory(self, mock_redis):
        mock_redis.hget.return_value = json.dumps(DATA)
        factory = MagicMock()
        s = ContextKVMemory(mock_redis)
        result = s.get_or_set(AGENT, SESSION, KEY, factory)
        assert result == DATA
        factory.assert_not_called()

    def test_calls_factory_and_hsetnx_when_missing(self, mock_redis):
        mock_redis.hget.return_value = None
        mock_redis.hsetnx.return_value = True
        factory = MagicMock(return_value=DATA)
        s = ContextKVMemory(mock_redis)
        result = s.get_or_set(AGENT, SESSION, KEY, factory)
        assert result == DATA
        mock_redis.hsetnx.assert_called_once_with(
            f"{AGENT}__{SESSION}", KEY, json.dumps(DATA)
        )

    def test_sets_ttl_on_new_value(self, mock_redis):
        mock_redis.hget.return_value = None
        mock_redis.hsetnx.return_value = True
        s = ContextKVMemory(mock_redis)
        s.get_or_set(AGENT, SESSION, KEY, lambda: DATA, ttl_seconds=60)
        mock_redis.expire.assert_called_once_with(f"{AGENT}__{SESSION}", 60)

    def test_returns_winner_value_when_race_lost(self, mock_redis):
        winner_data = {"winner": True}
        mock_redis.hget.side_effect = [None, json.dumps(winner_data)]
        mock_redis.hsetnx.return_value = False
        s = ContextKVMemory(mock_redis)
        result = s.get_or_set(AGENT, SESSION, KEY, lambda: DATA)
        assert result == winner_data

    def test_on_set_hook_called_only_when_write_wins(self, mock_redis):
        hook = MagicMock()
        mock_redis.hget.return_value = None
        mock_redis.hsetnx.return_value = True
        s = ContextKVMemory(mock_redis, on_set=hook)
        s.get_or_set(AGENT, SESSION, KEY, lambda: DATA)
        hook.assert_called_once_with(AGENT, SESSION, KEY, DATA)
