"""Tests for per-account AI Agent Chat prompt history
(hgai_module_agentchat/prompt_history.py).

Near-identical structure to tests/test_shql_history.py, since
prompt_history.py deliberately mirrors hgai_module_shql/history.py's own
dedup/eviction/scoping semantics. Uses a small in-memory fake Motor-like
collection rather than mocking individual cursor/query calls — closer to a
real collection's behavior for this module's find/insert_one/delete_many
usage, so the tests exercise the actual logic rather than a mocked call
sequence.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from hgai_module_agentchat.prompt_history import (
    HISTORY_MAX_PER_ACCOUNT,
    add_history_entry,
    clear_history,
    list_history,
)


class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for d in self._docs:
            yield d


class _FakeCollection:
    """In-memory stand-in for the `agent_chat_prompt_history` Motor collection."""

    def __init__(self):
        self.docs = []
        self._next_id = 0

    def _matches(self, doc, query):
        return all(doc.get(k) == v for k, v in query.items())

    def find(self, query, sort=None, skip=0, limit=None, projection=None):
        results = [d for d in self.docs if self._matches(d, query)]
        if sort:
            for field, direction in reversed(sort):
                results.sort(key=lambda d: d[field], reverse=(direction < 0))
        if skip:
            results = results[skip:]
        if limit:
            results = results[:limit]
        if projection:
            if projection == {"_id": 0}:
                results = [{k: v for k, v in d.items() if k != "_id"} for d in results]
            elif projection == {"_id": 1}:
                results = [{"_id": d["_id"]} for d in results]
        return _FakeCursor(results)

    async def insert_one(self, doc):
        doc = dict(doc)
        doc["_id"] = self._next_id
        self._next_id += 1
        self.docs.append(doc)

    async def delete_many(self, query):
        if "_id" in query and isinstance(query["_id"], dict) and "$in" in query["_id"]:
            ids = set(query["_id"]["$in"])
            before = len(self.docs)
            self.docs = [d for d in self.docs if d["_id"] not in ids]
            return SimpleNamespace(deleted_count=before - len(self.docs))
        before = len(self.docs)
        self.docs = [d for d in self.docs if not self._matches(d, query)]
        return SimpleNamespace(deleted_count=before - len(self.docs))


@pytest.fixture
def fake_collection():
    coll = _FakeCollection()
    with patch("hgai_module_agentchat.prompt_history._collection", return_value=coll):
        yield coll


@pytest.mark.asyncio
async def test_add_and_list_roundtrip(fake_collection):
    await add_history_entry("alice", "What hypergraphs exist?")
    items = await list_history("alice")
    assert len(items) == 1
    assert items[0]["prompt"] == "What hypergraphs exist?"
    assert items[0]["username"] == "alice"
    assert "created_at" in items[0]
    assert "_id" not in items[0]


@pytest.mark.asyncio
async def test_list_history_newest_first(fake_collection):
    await add_history_entry("alice", "prompt-1")
    await add_history_entry("alice", "prompt-2")
    await add_history_entry("alice", "prompt-3")
    items = await list_history("alice")
    assert [i["prompt"] for i in items] == ["prompt-3", "prompt-2", "prompt-1"]


@pytest.mark.asyncio
async def test_resubmitting_identical_prompt_moves_to_top_not_duplicated(fake_collection):
    await add_history_entry("alice", "prompt-a")
    await add_history_entry("alice", "prompt-b")
    await add_history_entry("alice", "prompt-a")
    items = await list_history("alice")
    assert [i["prompt"] for i in items] == ["prompt-a", "prompt-b"]


@pytest.mark.asyncio
async def test_blank_prompt_is_not_recorded(fake_collection):
    await add_history_entry("alice", "   ")
    await add_history_entry("alice", "")
    assert await list_history("alice") == []


@pytest.mark.asyncio
async def test_history_caps_at_max_per_account(fake_collection):
    for i in range(HISTORY_MAX_PER_ACCOUNT + 5):
        await add_history_entry("alice", f"prompt-{i}")
    items = await list_history("alice", limit=1000)
    assert len(items) == HISTORY_MAX_PER_ACCOUNT
    prompts = {i["prompt"] for i in items}
    assert "prompt-0" not in prompts
    assert f"prompt-{HISTORY_MAX_PER_ACCOUNT + 4}" in prompts


@pytest.mark.asyncio
async def test_history_scoped_per_account(fake_collection):
    await add_history_entry("alice", "alice-prompt")
    await add_history_entry("bob", "bob-prompt")
    assert [i["prompt"] for i in await list_history("alice")] == ["alice-prompt"]
    assert [i["prompt"] for i in await list_history("bob")] == ["bob-prompt"]


@pytest.mark.asyncio
async def test_clear_history_only_affects_that_account(fake_collection):
    await add_history_entry("alice", "alice-prompt")
    await add_history_entry("bob", "bob-prompt")
    deleted = await clear_history("alice")
    assert deleted == 1
    assert await list_history("alice") == []
    assert [i["prompt"] for i in await list_history("bob")] == ["bob-prompt"]
