"""Batched evaluation of SHQL patterns against many bindings (joins).

A pattern used to run one storage query per incoming binding. It now fetches
each distinct search key once, many keys per query where the store can filter
by "any of these ids". These tests pin both halves of that contract on every
storage backend: results (and their order, and truncation reporting) do not
depend on `shql_join_batch_size`, and the number of storage queries does.
"""

from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from hgai.config import get_settings
from hgai.models.account import AccountInDB
from hgai_module_shql import engine as shql_engine
from tests.storage_fixtures import mongod, stores  # noqa: F401  (fixtures used by name)

ADMIN = AccountInDB(username="root", email=None, roles=["admin"], password_hash="", status="active")


@pytest.fixture
def storage(stores):  # noqa: F811
    nodes, edges = stores

    class Hypergraphs:
        async def get(self, gid, space_id=None):
            return SimpleNamespace(id=gid, space_id=None, type="instantiated", composition=[]) \
                if gid == "g" else None

    class Meshes:
        async def get(self, mid):
            return None

    s = SimpleNamespace(hypernodes=nodes, hyperedges=edges, hypergraphs=Hypergraphs(), meshes=Meshes())
    with patch.object(shql_engine, "get_storage", return_value=s):
        yield s


@contextmanager
def count_calls(store, method="search"):
    calls = []
    real = getattr(store, method)

    async def spy(*a, **kw):
        calls.append(1)
        return await real(*a, **kw)

    with patch.object(store, method, spy):
        yield calls


async def run(query, *, batch=None):
    settings = get_settings()
    previous = settings.shql_join_batch_size
    if batch is not None:
        settings.shql_join_batch_size = batch
    try:
        return await shql_engine.execute_shql(query, use_cache=False, account=ADMIN)
    finally:
        settings.shql_join_batch_size = previous


def rows(result, *keys):
    return [tuple(item[k] for k in keys) for item in result.items]


# persons: n1 n2 n3 n6.  knows: e1(n1,n2) e2(n1,n3) e3(n2,n3).  likes: e4(n1,n4)
JOIN = """
shql:
  from: g
  select: ["?p.id", "?e.id", "?q.id"]
  where:
    - node: {bind: '?p', type: person}
    - edge: {bind: '?e', relation: knows, members: [{node_id: '?p'}, {node_id: '?q'}]}
"""
JOIN_ROWS = [
    ("n1", "e1", "n2"), ("n1", "e2", "n3"),
    ("n2", "e1", "n1"), ("n2", "e3", "n3"),
    ("n3", "e2", "n1"), ("n3", "e3", "n2"),
]                                   # n6 knows nobody: an inner join drops it, as before


async def test_join_results_and_order_are_independent_of_batch_size(storage):
    for batch in (1, 2, 3, 200):
        r = await run(JOIN, batch=batch)
        assert rows(r, "p.id", "e.id", "q.id") == JOIN_ROWS, f"batch={batch}"
        assert r.meta["truncated"] is False


@pytest.mark.parametrize("batch, expected_queries", [(1, 4), (2, 2), (3, 2), (200, 1)])
async def test_edge_lookups_are_batched(storage, batch, expected_queries):
    with count_calls(storage.hyperedges) as edge_calls, count_calls(storage.hypernodes) as node_calls:
        await run(JOIN, batch=batch)
    assert len(edge_calls) == expected_queries      # was: one per person (4)
    assert len(node_calls) == 1                     # the leading node pattern


async def test_cross_join_fetches_the_second_pattern_once(storage):
    query = """
shql:
  from: g
  select: ["?a.id", "?b.id"]
  where:
    - node: {bind: '?a', type: person}
    - node: {bind: '?b', type: place}
"""
    with count_calls(storage.hypernodes) as calls:
        r = await run(query)
    assert rows(r, "a.id", "b.id") == [("n1", "n4"), ("n2", "n4"), ("n3", "n4"), ("n6", "n4")]
    assert len(calls) == 2                          # was 1 + one per person = 5


LIKES_NODES = """
shql:
  from: g
  select: ["?e.id", "?n.id"]
  where:
    - edge: {bind: '?e', relation: likes, members: ['?m']}
    - node: {bind: '?n', id: '?m'}
"""


@pytest.mark.parametrize("batch, expected_queries", [(1, 2), (200, 1)])
async def test_node_lookups_by_bound_id_are_batched(storage, batch, expected_queries):
    with count_calls(storage.hypernodes) as calls:
        r = await run(LIKES_NODES, batch=batch)
    assert rows(r, "e.id", "n.id") == [("e4", "n1"), ("e4", "n4")]
    assert len(calls) == expected_queries


# ── Candidate caps behave exactly as they did per binding ─────────────────────

CAPPED = """
shql:
  from: g
  select: ["?p.id", "?e.id"]
  where:
    - node: {bind: '?p', type: person, attributes: {dept: eng}}
    - edge: {bind: '?e', members: [{node_id: '?p'}]}
"""


async def test_per_key_cap_is_reported_when_the_batch_was_complete(storage, monkeypatch):
    monkeypatch.setattr(get_settings(), "shql_max_edge_candidates", 2)
    # n1 touches e1,e2,e4 (3 > cap 2); n2 touches e1,e3.  4 edges < batch limit 2*2+1: complete.
    with count_calls(storage.hyperedges) as calls:
        batched = await run(CAPPED, batch=200)
    assert len(calls) == 1
    assert rows(batched, "p.id", "e.id") == [("n1", "e1"), ("n1", "e2"), ("n2", "e1"), ("n2", "e3")]
    assert batched.meta["truncated"] is True

    per_key = await run(CAPPED, batch=1)
    assert rows(per_key, "p.id", "e.id") == rows(batched, "p.id", "e.id")
    assert per_key.meta["truncated_by"] == batched.meta["truncated_by"]


async def test_an_overflowing_batch_falls_back_to_exact_per_key_queries(storage, monkeypatch):
    monkeypatch.setattr(get_settings(), "shql_max_edge_candidates", 1)
    # limit 1*2+1 = 3, but 4 edges touch n1/n2: the batch may have lost rows -> retry per key.
    with count_calls(storage.hyperedges) as calls:
        batched = await run(CAPPED, batch=200)
    assert len(calls) == 3                          # 1 batch attempt + 2 exact queries
    per_key = await run(CAPPED, batch=1)
    assert rows(batched, "p.id", "e.id") == rows(per_key, "p.id", "e.id") == [("n1", "e1"), ("n2", "e1")]
    assert batched.meta["truncated"] is True and per_key.meta["truncated"] is True


# ── Resolving bound variables to documents ────────────────────────────────────

async def test_bound_variable_resolution_is_chunked(storage, monkeypatch):
    monkeypatch.setattr(shql_engine, "_RESOLVE_CHUNK", 2)
    with count_calls(storage.hypernodes, "find_by_ids") as calls:
        r = await run(JOIN)
    assert rows(r, "p.id", "e.id", "q.id") == JOIN_ROWS
    assert len(calls) == 2                          # q ids n1,n2,n3 -> chunks of 2
