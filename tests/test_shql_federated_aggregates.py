"""Federated SHQL aggregates: per-server partials merged exactly.

Each mesh server aggregates its own graphs and returns `meta`; the caller merges
those partials with its own. The oracle for every case is the in-memory
aggregate over the union of all servers' rows — so a merge that, say, averaged
the averages would fail. Remote servers are real `execute_shql` runs against
their own storage, reached through a fake HTTP client.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from hgai.models.account import AccountInDB
from hgai_module_mesh import engine as mesh_engine
from hgai_module_shql import engine as shql_engine
from hgai_module_shql.aggregate_merge import merge_aggregate_meta, partial_aggregate
from tests.storage_fixtures import NODES, _MemEdges, _MemNodes, _node, mongod, stores  # noqa: F401

ADMIN = AccountInDB(username="root", email=None, roles=["admin"], password_hash="", status="active")

# Local server = the parametrized backend's NODES (active: n1 n2 n3 n4 n6).
B_NODES = [
    _node("b1", "person", [], {"dept": "eng", "age": 10}),
    _node("b2", "person", [], {"dept": "ops", "age": 20}),
    _node("b3", "place"),
]
C_NODES = [
    _node("c1", "person", [], {"dept": "eng", "age": "x"}),
    _node("c2", "person", [], {"dept": "eng", "age": 5}),
]
REMOTES = {"http://host-b:8357": B_NODES, "http://host-c:8357": C_NODES}


def graph_store(nodes):
    class Hypergraphs:
        async def get(self, gid, space_id=None):
            return SimpleNamespace(id=gid, space_id=None, type="instantiated", composition=[]) \
                if gid == "g" else None

    class Meshes:
        async def get(self, mid):
            return None

    return SimpleNamespace(hypernodes=_MemNodes(nodes), hyperedges=_MemEdges([]),
                           hypergraphs=Hypergraphs(), meshes=Meshes())


MESH = {"id": "mesh1", "servers": [
    {"server_id": "s1", "server_name": "B", "url": "http://host-b:8357", "graphs": ["g"]},
    {"server_id": "s2", "server_name": "C", "url": "http://host-c:8357", "graphs": ["g"]},
]}


@pytest.fixture
def federation(stores):  # noqa: F811
    nodes, edges = stores
    lock = asyncio.Lock()      # remote runs swap the module's storage; never interleave them
    behaviour = {"fail": set(), "strip_meta": set()}

    class Meshes:
        async def get(self, mid):
            return MESH if mid == "mesh1" else None

    class Hypergraphs:
        async def get(self, gid, space_id=None):
            return SimpleNamespace(id=gid, space_id=None, type="instantiated", composition=[]) \
                if gid == "g" else None

    local = SimpleNamespace(hypernodes=nodes, hyperedges=edges, hypergraphs=Hypergraphs(), meshes=Meshes())
    bodies = []

    async def post(url, headers=None, json=None):
        base = url.split("/api/")[0]
        bodies.append(json)
        if base in behaviour["fail"]:
            raise RuntimeError("connection refused")
        async with lock:
            with patch.object(shql_engine, "get_storage", return_value=graph_store(REMOTES[base])):
                result = await shql_engine.execute_shql(json["shql"], use_cache=False, account=ADMIN)
        payload = result.to_dict()
        if base in behaviour["strip_meta"]:
            payload["meta"] = {}
        response = MagicMock()
        response.raise_for_status = lambda: None
        response.json = lambda: payload
        return response

    client = SimpleNamespace(post=post)
    with patch.object(shql_engine, "get_storage", return_value=local), \
         patch.object(mesh_engine, "get_storage", return_value=local), \
         patch.object(mesh_engine, "get_http_client", return_value=client):
        yield SimpleNamespace(behaviour=behaviour, bodies=bodies)


def query(aggregate, *, limit0=True, distinct=False):
    return (
        "shql:\n  from: [g, mesh1]\n"
        '  select: ["?n.type", "?n.attributes.age", "?n.attributes.dept"]\n'
        "  where:\n    - node: '?n'\n"
        + ("  limit: 0\n" if limit0 else "")
        + ("  distinct: true\n" if distinct else "")
        + f"  aggregate: {aggregate}\n"
    )


def rows_of(docs):
    return [{"n.type": d["type"], "n.attributes.age": d["attributes"].get("age"),
             "n.attributes.dept": d["attributes"].get("dept")} for d in docs]


def active_local():
    return [d for d in NODES if d["status"] == "active"]


def oracle(aggregate, *server_docs):
    docs = [d for group in server_docs for d in group]
    return shql_engine._aggregate_in_memory(rows_of(docs), aggregate)


async def run(text):
    return await shql_engine.execute_shql(text, use_cache=False, account=ADMIN)


AGG_KEYS = ("count", "groups", "sum", "avg", "min", "max", "count_numeric", "group_measures")


def agg(meta):
    return {k: meta[k] for k in AGG_KEYS if k in meta}


AGGREGATES = {
    "count": {"count": True},
    "count by type": {"count": True, "group_by": "n.type"},
    "sum avg min max": {"sum": "n.attributes.age", "avg": "n.attributes.age",
                        "min": "n.attributes.age", "max": "n.attributes.age"},
    "count_numeric": {"count_numeric": "n.attributes.age"},
    "grouped measures": {"count": True, "group_by": "n.attributes.dept",
                         "sum": "n.attributes.age", "avg": "n.attributes.age", "max": "n.attributes.age"},
}


@pytest.mark.parametrize("name", AGGREGATES)
async def test_federated_aggregate_equals_the_union(federation, name):
    aggregate = AGGREGATES[name]
    r = await run(query(aggregate))
    expected = oracle(aggregate, active_local(), B_NODES, C_NODES)
    assert agg(r.meta) == expected
    fed = r.meta["federation"]
    assert fed == {"servers": ["s1", "s2"], "errors": [], "aggregate_merged": True}
    assert r.meta["aggregate_pushdown"] is True          # local and both remotes used storage
    assert r.items == []                                  # limit: 0 fetched no rows anywhere


async def test_avg_is_not_the_average_of_the_averages(federation):
    r = await run(query({"avg": "n.attributes.age"}))
    # numeric ages: local 30 40 99 (n3 "n/a" is text) + 10 20 + 5  -> 204 / 6
    assert r.meta["avg"] == {"n.attributes.age": 34.0}
    assert set(r.meta) & {"sum", "count_numeric"} == set()


async def test_remote_queries_are_widened_with_the_avg_partials(federation):
    await run(query({"avg": "n.attributes.age"}))
    remote_aggregate = [b["shql"] for b in federation.bodies]
    assert len(remote_aggregate) == 2
    assert all("sum:" in text and "count_numeric:" in text for text in remote_aggregate)


async def test_rows_are_still_merged_and_counted_exactly(federation):
    r = await run(query({"count": True}, limit0=False))
    assert r.meta["count"] == 5 + 3 + 2
    assert len(r.items) == 10
    assert {i.get("_mesh_server_id") for i in r.items} == {None, "s1", "s2"}


async def test_a_failed_server_is_reported_and_left_out_of_the_aggregate(federation):
    federation.behaviour["fail"].add("http://host-c:8357")
    aggregate = {"count": True, "group_by": "n.type"}
    r = await run(query(aggregate))
    assert agg(r.meta) == oracle(aggregate, active_local(), B_NODES)
    fed = r.meta["federation"]
    assert fed["servers"] == ["s1"] and fed["aggregate_merged"] is True
    assert [e["server_id"] for e in fed["errors"]] == ["s2"]


async def test_a_server_without_partials_falls_back_to_the_merged_rows(federation):
    federation.behaviour["strip_meta"].add("http://host-b:8357")     # e.g. an older server
    aggregate = {"count": True, "avg": "n.attributes.age"}
    r = await run(query(aggregate, limit0=False))
    assert agg(r.meta) == oracle(aggregate, active_local(), B_NODES, C_NODES)
    assert r.meta["federation"]["aggregate_merged"] is False


async def test_distinct_keeps_the_row_based_aggregate(federation):
    aggregate = {"count": True}
    r = await run(query(aggregate, limit0=False, distinct=True))
    assert r.meta["federation"]["aggregate_merged"] is False
    assert r.meta["count"] == len({tuple(sorted(i.items(), key=str)) for i in r.items}) == 10


# ── Canned remotes: truncation, pure-remote queries, the direct API ───────────

def canned_client(metas, bodies=None):
    async def post(url, headers=None, json=None):
        if bodies is not None:
            bodies.append(json)
        response = MagicMock()
        response.raise_for_status = lambda: None
        response.json = lambda: {"items": [], "meta": metas[url.split("/api/")[0]]}
        return response
    return SimpleNamespace(post=post)


class _NoLocalGraphs:
    class hypergraphs:
        @staticmethod
        async def get(gid, space_id=None):
            return None

    class meshes:
        @staticmethod
        async def get(mid):
            return MESH if mid == "mesh1" else None


async def test_pure_remote_query_merges_and_propagates_truncation():
    metas = {
        "http://host-b:8357": {"count": 3, "truncated_by": ["node pattern candidates (cap 2)"],
                               "aggregate_pushdown": False},
        "http://host-c:8357": {"count": 4, "truncated_by": [], "aggregate_pushdown": True},
    }
    with patch.object(shql_engine, "get_storage", return_value=_NoLocalGraphs), \
         patch.object(mesh_engine, "get_storage", return_value=_NoLocalGraphs), \
         patch.object(mesh_engine, "get_http_client", return_value=canned_client(metas)):
        r = await run("shql:\n  from: mesh1\n  limit: 0\n  where:\n    - node: '?n'\n  aggregate: {count: true}\n")
    assert r.meta["count"] == 7
    assert r.meta["truncated"] is True
    assert r.meta["truncated_by"] == ["s1: node pattern candidates (cap 2)"]
    assert r.meta["aggregate_pushdown"] is False         # one remote was aggregated in memory


async def test_federated_shql_api_returns_the_merged_aggregate():
    k = "n.age"
    metas = {
        "http://host-b:8357": {"avg": {k: 5}, "sum": {k: 10}, "count_numeric": {k: 2}},
        "http://host-c:8357": {"avg": {k: 10}, "sum": {k: 30}, "count_numeric": {k: 3}},
    }
    bodies = []
    with patch.object(mesh_engine, "get_storage", return_value=_NoLocalGraphs), \
         patch.object(mesh_engine, "get_http_client", return_value=canned_client(metas, bodies)):
        result = await mesh_engine.federated_shql(
            "mesh1", "shql:\n  from: mesh1\n  aggregate:\n    avg: n.age\n", account=ADMIN)
    assert result["aggregate"] == {"avg": {k: 8.0}}        # 40 / 5, not (5 + 10) / 2
    assert all("count_numeric" in b["shql"] for b in bodies)


# ── merge_aggregate_meta / partial_aggregate ──────────────────────────────────

def test_partial_aggregate_adds_only_what_avg_needs():
    assert partial_aggregate({"count": True, "sum": "a"}) == {"count": True, "sum": "a"}
    widened = partial_aggregate({"avg": ["a", "b"], "sum": "a"})
    assert widened["sum"] == ["a", "b"] and widened["count_numeric"] == ["a", "b"]
    assert partial_aggregate(widened) == widened


def test_merge_groups_take_the_union_and_merge_per_group():
    a = {"sum": {"v": 11}, "count_numeric": {"v": 3}, "max": {"v": 7}, "avg": {"v": 11 / 3},
         "groups": {"x": 2, "y": 1}, "group_measures": {
        "x": {"sum": {"v": 10}, "count_numeric": {"v": 2}, "max": {"v": 7}},
        "y": {"sum": {"v": 1}, "count_numeric": {"v": 1}, "max": {"v": 1}}}}
    b = {"sum": {"v": 5}, "count_numeric": {"v": 1}, "max": {"v": "text"}, "avg": {"v": 5.0},
         "groups": {"x": 1, "z": 4}, "group_measures": {
        "x": {"sum": {"v": 5}, "count_numeric": {"v": 1}, "max": {"v": "text"}},
        "z": {"sum": {"v": 0}, "count_numeric": {"v": 0}, "max": {"v": None}}}}
    aggregate = {"group_by": "g", "avg": "v", "max": "v"}
    merged = merge_aggregate_meta([a, b], aggregate | {"sum": "v", "count_numeric": "v"})
    assert merged["groups"] == {"x": 3, "y": 1, "z": 4}
    assert merged["group_measures"]["x"]["avg"] == {"v": 5.0}          # 15 / 3
    assert merged["group_measures"]["x"]["max"] == {"v": "text"}       # text sorts after numbers
    assert merged["group_measures"]["z"]["avg"] == {"v": None}         # nothing numeric
    assert merged["group_measures"]["z"]["max"] == {"v": None}


def test_merge_returns_none_when_a_part_lacks_what_is_needed():
    ok = {"count": 1, "sum": {"v": 1}, "count_numeric": {"v": 1}}
    assert merge_aggregate_meta([ok, {"count": 1}], {"count": True, "avg": "v"}) is None
    assert merge_aggregate_meta([ok, {}], {"count": True}) is None
    assert merge_aggregate_meta([ok], {"count": True, "avg": "v"}) == {"count": 1, "avg": {"v": 1.0}}
