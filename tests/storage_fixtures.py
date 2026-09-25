"""Shared fixtures for storage-layer aggregation tests: a small dataset, a
reference in-memory backend (inherits the ABC's default `aggregate`), and a
real throwaway `mongod`. A new backend adds itself to `BACKENDS`."""

import copy
import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone

import pytest

from hgai_module_storage.backend import HyperedgeStore, HypernodeStore
from hgai_module_storage.filters import HyperedgeSearchFilters, HypernodeSearchFilters

UTC = timezone.utc
PAST = datetime(2000, 1, 1, tzinfo=UTC)
PIT = datetime(2026, 1, 1, tzinfo=UTC)


def _node(id, type, tags=(), attributes=None, status="active", valid_to=None):
    return {
        "id": id, "hypergraph_id": "g", "type": type, "label": id, "status": status,
        "tags": list(tags), "attributes": attributes or {},
        "valid_from": None, "valid_to": valid_to,
    }


NODES = [
    _node("n1", "person", ["a", "b"], {"dept": "eng", "age": 30, "salary": 100}),
    _node("n2", "person", ["a"], {"dept": "eng", "age": 40, "salary": 200}),
    _node("n3", "person", [], {"dept": "ops", "age": "n/a", "salary": True}),
    _node("n4", "place"),
    _node("n5", "person", ["a"], {"dept": "eng"}, status="archived"),
    _node("n6", "person", ["a"], {"age": 99}, valid_to=PAST),
]


def _edge(id, relation, flavor, weight=None, members=()):
    return {
        "id": id, "hypergraph_id": "g", "relation": relation, "flavor": flavor,
        "status": "active", "tags": [], "attributes": {} if weight is None else {"weight": weight},
        "members": [{"node_id": m, "seq": i} for i, m in enumerate(members)],
        "valid_from": None, "valid_to": None,
    }


EDGES = [
    _edge("e1", "knows", "hub", 1.5, ["n1", "n2"]),
    _edge("e2", "knows", "hub", 2.5, ["n1", "n3"]),
    _edge("e3", "knows", "symmetric", None, ["n2", "n3"]),
    _edge("e4", "likes", "hub", 10, ["n1", "n4"]),
]


# ── Reference backend: inherits the ABC default aggregate() ───────────────────

def _live(doc, pit):
    if pit is None:
        return True
    vf, vt = doc.get("valid_from"), doc.get("valid_to")
    return (vf is None or vf <= pit) and (vt is None or vt >= pit)


def _attrs_match(doc, attributes):
    return all(doc.get("attributes", {}).get(k) == v for k, v in (attributes or {}).items())


def _tags_match(doc, tags):
    return all(t in doc.get("tags", []) for t in (tags or []))


def _member_ids(doc):
    return {m["node_id"] for m in doc.get("members", [])}


class _MemNodes(HypernodeStore):
    def __init__(self, docs):
        self.docs = docs
        self.search_calls = 0

    async def search(self, filters, skip=0, limit=500):
        self.search_calls += 1
        out = [
            copy.deepcopy(d) for d in self.docs
            if d["hypergraph_id"] in filters.hypergraph_ids
            and (not filters.status or d["status"] == filters.status)
            and (not filters.node_type or d["type"] == filters.node_type)
            and (not filters.node_ids_in or d["id"] in filters.node_ids_in)
            and _tags_match(d, filters.tags)
            and _attrs_match(d, filters.attributes)
            and _live(d, filters.pit)
        ]
        return out[skip: skip + limit]

    async def find_by_ids(self, node_ids, hypergraph_ids):
        return [copy.deepcopy(d) for d in self.docs
                if d["id"] in node_ids and d["hypergraph_id"] in hypergraph_ids]


class _MemEdges(HyperedgeStore):
    def __init__(self, docs):
        self.docs = docs
        self.search_calls = 0

    async def search(self, filters, skip=0, limit=500):
        self.search_calls += 1
        extra = filters.extra_filters or {}
        out = [
            copy.deepcopy(d) for d in self.docs
            if d["hypergraph_id"] in filters.hypergraph_ids
            and (not filters.status or d["status"] == filters.status)
            and (not filters.relation or d["relation"] == filters.relation)
            and (not filters.flavor or d["flavor"] == filters.flavor)
            and (not filters.member_node_id or filters.member_node_id in _member_ids(d))
            and (not filters.member_node_ids_all or set(filters.member_node_ids_all) <= _member_ids(d))
            and (not filters.member_node_ids_any or set(filters.member_node_ids_any) & _member_ids(d))
            and ("id" not in extra or d["id"] == extra["id"])
            and _tags_match(d, filters.tags)
            and _attrs_match(d, filters.attributes)
            and _live(d, filters.pit)
        ]
        return out[skip: skip + limit]


for _cls in (_MemNodes, _MemEdges):
    _cls.__abstractmethods__ = frozenset()  # only `search` is exercised


# ── Mongo backend: real mongod ────────────────────────────────────────────────

@pytest.fixture(scope="module")
def mongod(tmp_path_factory):
    exe = shutil.which("mongod")
    if not exe:
        pytest.skip("mongod not installed")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [exe, "--dbpath", str(tmp_path_factory.mktemp("mongo")), "--port", str(port),
         "--bind_ip", "127.0.0.1", "--nounixsocket"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.2)
        else:
            pytest.skip("mongod did not start")
        yield f"mongodb://127.0.0.1:{port}"
    finally:
        proc.terminate()
        proc.wait(timeout=15)


BACKENDS = ["reference", "mongo"]


@pytest.fixture(params=BACKENDS)
async def stores(request):
    """(node_store, edge_store) loaded with NODES / EDGES."""
    if request.param == "reference":
        yield _MemNodes(NODES), _MemEdges(EDGES)
        return

    from hgai_module_storage_mongodb import connection
    from hgai_module_storage_mongodb.stores.hyperedges import MongoHyperedgeStore
    from hgai_module_storage_mongodb.stores.hypernodes import MongoHypernodeStore

    uri = request.getfixturevalue("mongod")
    db = await connection.connect(uri, "hgai_agg_test")
    try:
        await db["hypernodes"].insert_many(copy.deepcopy(NODES))
        await db["hyperedges"].insert_many(copy.deepcopy(EDGES))
        yield MongoHypernodeStore(), MongoHyperedgeStore()
    finally:
        await db.client.drop_database("hgai_agg_test")
        await connection.close()


def nf(**kw):
    return HypernodeSearchFilters(hypergraph_ids=["g"], **kw)


def ef(**kw):
    return HyperedgeSearchFilters(hypergraph_ids=["g"], **kw)


