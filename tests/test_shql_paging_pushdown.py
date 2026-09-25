"""SHQL `order_by` / `offset` / `limit` pushdown to the storage layer.

For every query the planner accepts, the storage-sorted page must equal what
the in-memory path returns (planner forced off), on every storage backend.
Queries it cannot prove equivalent must fall back.
See `_plan_paging_pushdown` in hgai_module_shql/engine.py.
"""

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


async def run(query, *, pushdown=True):
    if pushdown:
        return await shql_engine.execute_shql(query, use_cache=False, account=ADMIN)
    with patch.object(shql_engine, "_plan_paging_pushdown", return_value=None):
        return await shql_engine.execute_shql(query, use_cache=False, account=ADMIN)


def q(*, select, where, extra=""):
    sel = ", ".join(f'"{f}"' for f in select)
    return f"shql:\n  from: g\n  select: [{sel}]\n  where:\n    - {where}\n{extra}"


NODE = "node: '?n'"
EDGE = "edge: '?e'"
AGE = ["?n.id", "?n.attributes.age"]

EQUIVALENT = {
    "age ascending": q(select=AGE, where=NODE, extra="  order_by: n.attributes.age\n"),
    "age descending": q(select=AGE, where=NODE, extra="  order_by: '?n.attributes.age desc'\n"),
    "type descending (ties)": q(select=["?n.id", "?n.type"], where=NODE, extra="  order_by: 'n.type desc'\n"),
    "multi key mixed direction": q(
        select=["?n.id", "?n.type", "?n.attributes.age"], where=NODE,
        extra="  order_by: ['n.type', 'n.attributes.age desc']\n"),
    "limit and offset with order": q(select=AGE, where=NODE, extra="  order_by: n.attributes.age\n  limit: 2\n  offset: 1\n"),
    "limit and offset, natural order": q(select=["?n.id"], where=NODE, extra="  limit: 2\n  offset: 1\n"),
    "whole-row select (*)": q(select=["*"], where=NODE, extra="  order_by: n.attributes.age desc\n  limit: 3\n"),
    "whole variable selected": q(select=["?n"], where=NODE, extra="  order_by: n.attributes.age\n"),
    "filtered by type": q(select=AGE, where="node: {bind: '?n', type: person}", extra="  order_by: n.attributes.age desc\n"),
    "point in time": q(select=AGE, where=NODE, extra="  at: '2026-01-01T00:00:00Z'\n  order_by: n.attributes.age\n"),
    "by id": q(select=["?n.id"], where=NODE, extra="  order_by: n.id desc\n"),
    "edges by weight": q(select=["?e.id", "?e.attributes.weight"], where=EDGE,
                         extra="  order_by: e.attributes.weight desc\n  offset: 1\n  limit: 2\n"),
    "edges by relation then id": q(select=["?e.id", "?e.relation"], where=EDGE,
                                   extra="  order_by: ['e.relation desc', 'e.id']\n"),
}


@pytest.mark.parametrize("name", EQUIVALENT)
async def test_pushdown_page_matches_in_memory_page(storage, name):
    pushed = await run(EQUIVALENT[name])
    baseline = await run(EQUIVALENT[name], pushdown=False)
    assert pushed.meta["paging_pushdown"] is True
    assert baseline.meta["paging_pushdown"] is False
    assert pushed.items == baseline.items != []


async def test_known_order(storage):
    r = await run(EQUIVALENT["age ascending"])
    assert [i["n.id"] for i in r.items] == ["n4", "n1", "n2", "n6", "n3"]   # missing, 30, 40, 99, "n/a"


async def test_pages_tile_the_full_result(storage):
    base = "  order_by: n.attributes.age\n  limit: 2\n  offset: {}\n"
    seen = []
    for off in (0, 2, 4, 6):
        r = await run(q(select=AGE, where=NODE, extra=base.format(off)))
        assert r.meta["paging_pushdown"] is True
        seen += [i["n.id"] for i in r.items]
    assert seen == ["n4", "n1", "n2", "n6", "n3"]


async def test_aggregate_and_paging_can_both_be_pushed_down(storage):
    r = await run(q(select=["?n.id", "?n.type"], where=NODE,
                    extra="  order_by: n.id\n  limit: 2\n  aggregate: {count: true, group_by: n.type}\n"))
    assert r.meta["aggregate_pushdown"] and r.meta["paging_pushdown"]
    assert r.meta["count"] == 5 and r.meta["groups"] == {"person": 4, "place": 1}
    assert [i["n.id"] for i in r.items] == ["n1", "n2"]


# ── Exactness past the candidate cap ──────────────────────────────────────────

async def test_pushed_down_page_is_exact_beyond_the_candidate_cap(storage, monkeypatch):
    monkeypatch.setattr(get_settings(), "shql_max_node_candidates", 1)
    query = q(select=AGE, where=NODE, extra="  order_by: '?n.attributes.age desc'\n  limit: 2\n")

    pushed = await run(query)
    assert [i["n.id"] for i in pushed.items] == ["n3", "n6"]
    assert pushed.meta["truncated"] is False

    baseline = await run(query, pushdown=False)      # sorts only the 1 fetched candidate
    assert baseline.meta["truncated"] is True and len(baseline.items) == 1


# ── Fallbacks ─────────────────────────────────────────────────────────────────

FALLBACKS = {
    "order key not projected": q(select=["?n.id"], where=NODE, extra="  order_by: n.type\n"),
    "order by tags": q(select=["?n.tags"], where=NODE, extra="  order_by: n.tags\n"),
    "order by other variable": q(select=["?n.id"], where=NODE, extra="  order_by: m.type\n"),
    "duplicate order keys": q(select=["?n.id", "?n.type"], where=NODE, extra="  order_by: ['n.type', 'n.type desc']\n"),
    "unsupported field": q(select=["?n.members"], where=NODE, extra="  order_by: n.members\n"),
    "two patterns": "shql:\n  from: g\n  select: ['?a.id']\n  where:\n    - node: '?a'\n    - node: '?b'\n",
    "filter pattern": "shql:\n  from: g\n  select: ['?n.id']\n  where:\n    - node: '?n'\n    - filter: \"?n.type == 'person'\"\n",
    "edge members": "shql:\n  from: g\n  select: ['?e.id']\n  where:\n    - edge: {bind: '?e', members: ['?m']}\n",
    "distinct": q(select=["?n.type"], where=NODE, extra="  distinct: true\n"),
    "no bind variable": "shql:\n  from: g\n  where:\n    - node: {type: person}\n",
    "in-memory aggregate needs every row": q(
        select=["?n.id"], where=NODE, extra="  limit: 2\n  aggregate: {sum: n.attributes.age}\n"),
}


@pytest.mark.parametrize("name", FALLBACKS)
async def test_ineligible_queries_fall_back_to_in_memory(storage, name):
    r = await run(FALLBACKS[name])
    assert r.meta["paging_pushdown"] is False


async def test_infer_is_never_paged_in_storage(storage):
    plan = shql_engine._plan_paging_pushdown(
        order_by=None, where_patterns=[{"edge": "?e"}], select_fields=["?e.id"],
        graph_ids=["g"], pit=None, infer=True, distinct=False,
    )
    assert plan is None


# ── In-memory ordering now shares the storage order ───────────────────────────

def test_in_memory_order_by_handles_mixed_types_and_missing_values():
    rows = [{"x": "b"}, {"x": 3}, {}, {"x": None}, {"x": "a"}, {"x": 1}]
    got = shql_engine._apply_order_by(rows, "x")
    assert [r.get("x") for r in got] == [None, None, 1, 3, "a", "b"]   # was a TypeError
    assert [r.get("x") for r in shql_engine._apply_order_by(rows, "x desc")] == ["b", "a", 3, 1, None, None]
