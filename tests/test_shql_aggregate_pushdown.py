"""SHQL `aggregate:` pushdown to the storage layer.

For every query the planner accepts, the storage-computed `count`/`groups`
must equal what the in-memory path computes (the planner is forced off to get
that baseline), on every storage backend. Queries it cannot prove equivalent
must fall back. See `_plan_aggregate_pushdown` in hgai_module_shql/engine.py.
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
    with patch.object(shql_engine, "_plan_aggregate_pushdown", return_value=None):
        return await shql_engine.execute_shql(query, use_cache=False, account=ADMIN)


AGG_KEYS = ("count", "groups", "sum", "avg", "min", "max", "group_measures")


def agg(meta):
    return {k: meta[k] for k in AGG_KEYS if k in meta}


EQUIVALENT = {
    "node count": """
shql:
  from: g
  where:
    - node: ?n
  select: ["?n.id"]
  aggregate: {count: true}
""",
    "node typed count": """
shql:
  from: g
  where:
    - node: ?n
      type: person
  select: ["?n.id"]
  aggregate: {count: true}
""",
    "group by type": """
shql:
  from: g
  where:
    - node: ?n
  select: ["?n.type"]
  aggregate: {group_by: n.type}
""",
    "count and group by attribute (missing -> 'None')": """
shql:
  from: g
  where:
    - node: {bind: '?n', type: person}
  select: ["?n.id", "?n.attributes.dept"]
  aggregate: {count: true, group_by: n.attributes.dept}
""",
    "attribute filter": """
shql:
  from: g
  where:
    - node: {bind: '?n', attributes: {dept: eng}}
  select: ["?n.type"]
  aggregate: {count: true, group_by: n.type}
""",
    "point in time": """
shql:
  from: g
  at: "2026-01-01T00:00:00Z"
  where:
    - node: ?n
  select: ["?n.type"]
  aggregate: {count: true, group_by: n.type}
""",
    "archived status": """
shql:
  from: g
  where:
    - node: {bind: '?n', status: archived}
  select: ["?n.id"]
  aggregate: {count: true}
""",
    "edge group by relation": """
shql:
  from: g
  where:
    - edge: ?e
  select: ["?e.relation"]
  aggregate: {count: true, group_by: e.relation}
""",
    "edge flavor filter": """
shql:
  from: g
  where:
    - edge: {bind: '?e', relation: knows}
  select: ["?e.flavor"]
  aggregate: {group_by: e.flavor}
""",
    "single node by id": """
shql:
  from: g
  where:
    - node: {bind: '?n', id: n1}
  select: ["?n.id"]
  aggregate: {count: true}
""",
}

EQUIVALENT.update({
    "global sum/avg/min/max": """
shql:
  from: g
  where:
    - node: {bind: '?n', type: person}
  select: ["?n.attributes.age"]
  aggregate:
    sum: n.attributes.age
    avg: n.attributes.age
    min: n.attributes.age
    max: n.attributes.age
""",
    "several fields, list form, with count": """
shql:
  from: g
  where:
    - node: {bind: '?n', type: person}
  select: ["?n.attributes.age", "?n.attributes.salary"]
  aggregate:
    count: true
    sum: [n.attributes.age, n.attributes.salary]
    max: [n.attributes.salary]
""",
    "grouped measures": """
shql:
  from: g
  where:
    - node: {bind: '?n', type: person}
  select: ["?n.attributes.dept", "?n.attributes.age"]
  aggregate:
    count: true
    group_by: n.attributes.dept
    sum: n.attributes.age
    avg: n.attributes.age
    min: n.attributes.age
""",
    "measures over an empty match": """
shql:
  from: g
  where:
    - node: {bind: '?n', type: nothing}
  select: ["?n.attributes.age"]
  aggregate:
    count: true
    sum: n.attributes.age
    avg: n.attributes.age
    min: n.attributes.age
""",
    "edge weights by relation": """
shql:
  from: g
  where:
    - edge: '?e'
  select: ["?e.relation", "?e.attributes.weight"]
  aggregate:
    group_by: e.relation
    sum: e.attributes.weight
    max: e.attributes.weight
""",
})


@pytest.mark.parametrize("name", EQUIVALENT)
async def test_pushdown_matches_in_memory_result(storage, name):
    pushed = await run(EQUIVALENT[name])
    baseline = await run(EQUIVALENT[name], pushdown=False)
    assert pushed.meta["aggregate_pushdown"] is True
    assert baseline.meta["aggregate_pushdown"] is False
    assert agg(pushed.meta) == agg(baseline.meta) != {}


async def test_count_only_query_has_no_groups_key(storage):
    r = await run(EQUIVALENT["node count"])
    assert r.meta["count"] == 5 and "groups" not in r.meta


async def test_group_by_only_query_has_no_count_key(storage):
    r = await run(EQUIVALENT["edge flavor filter"])
    assert "count" not in r.meta and r.meta["groups"] == {"hub": 2, "symmetric": 1}


FALLBACKS = {
    "measure key not projected": "shql:\n  from: g\n  where:\n    - node: '?n'\n  select: ['?n.id']\n  aggregate: {sum: n.attributes.age}\n",
    "measure over tags": "shql:\n  from: g\n  where:\n    - node: '?n'\n  select: ['?n.tags']\n  aggregate: {max: n.tags}\n",
    "measure on another variable": "shql:\n  from: g\n  where:\n    - node: '?n'\n  select: ['?m.attributes.age']\n  aggregate: {sum: m.attributes.age}\n",
    "distinct": "shql:\n  from: g\n  distinct: true\n  where:\n    - node: ?n\n  select: ['?n.type']\n  aggregate: {count: true}\n",
    "two patterns": "shql:\n  from: g\n  where:\n    - node: ?a\n    - node: ?b\n  select: ['?a.id']\n  aggregate: {count: true}\n",
    "filter pattern": "shql:\n  from: g\n  where:\n    - node: ?n\n    - filter: \"?n.type == 'person'\"\n  select: ['?n.id']\n  aggregate: {count: true}\n",
    "edge members": "shql:\n  from: g\n  where:\n    - edge: {bind: '?e', members: ['?m']}\n  select: ['?e.id']\n  aggregate: {count: true}\n",
    "variable id": "shql:\n  from: g\n  where:\n    - node: {bind: '?n', id: '?x'}\n  select: ['?n.id']\n  aggregate: {count: true}\n",
    "group_by not projected": "shql:\n  from: g\n  where:\n    - node: ?n\n  select: ['?n.id']\n  aggregate: {group_by: n.type}\n",
    "group_by whole row": "shql:\n  from: g\n  where:\n    - node: ?n\n  aggregate: {group_by: n}\n",
    "group_by tags (arrays)": "shql:\n  from: g\n  where:\n    - node: ?n\n  select: ['?n.tags']\n  aggregate: {group_by: n.tags}\n",
    "group_by unsupported field": "shql:\n  from: g\n  where:\n    - node: ?n\n  select: ['?n.members']\n  aggregate: {group_by: n.members}\n",
    "no aggregate": "shql:\n  from: g\n  where:\n    - node: ?n\n  select: ['?n.id']\n",
    "unknown aggregate keys only": "shql:\n  from: g\n  where:\n    - node: ?n\n  select: ['?n.id']\n  aggregate: {sum: n.x}\n",
}


@pytest.mark.parametrize("name", FALLBACKS)
async def test_ineligible_queries_fall_back_to_in_memory(storage, name):
    r = await run(FALLBACKS[name])
    assert r.meta["aggregate_pushdown"] is False


# ── Exactness past the candidate cap ──────────────────────────────────────────

async def test_pushed_down_aggregate_is_exact_beyond_the_candidate_cap(storage, monkeypatch):
    monkeypatch.setattr(get_settings(), "shql_max_node_candidates", 2)
    q = EQUIVALENT["group by type"]

    pushed = await run(q.replace("aggregate:", "limit: 0\n  aggregate:"))
    assert pushed.meta["groups"] == {"person": 4, "place": 1}
    assert pushed.meta["truncated"] is False and pushed.items == []

    # In-memory baseline silently undercounts — exactly what pushdown fixes.
    baseline = await run(q, pushdown=False)
    assert baseline.meta["truncated"] is True
    assert sum(baseline.meta["groups"].values()) == 2


async def test_paged_items_are_exact_too_when_paging_is_pushed_down(storage, monkeypatch):
    monkeypatch.setattr(get_settings(), "shql_max_node_candidates", 2)
    r = await run(EQUIVALENT["node count"])
    assert r.meta["count"] == 5 and r.meta["aggregate_pushdown"] is True
    assert r.meta["paging_pushdown"] is True
    assert r.meta["truncated"] is False and len(r.items) == 5      # not limited by the cap


async def test_items_report_truncation_when_only_the_aggregate_is_pushed_down(storage, monkeypatch):
    monkeypatch.setattr(get_settings(), "shql_max_node_candidates", 2)
    # order_by names a key `select:` does not project, so rows stay on the capped in-memory path
    q = EQUIVALENT["node count"].replace("aggregate:", "order_by: n.type\n  aggregate:")
    r = await run(q)
    assert r.meta["count"] == 5                      # exact, from storage
    assert r.meta["aggregate_pushdown"] is True and r.meta["paging_pushdown"] is False
    assert r.meta["truncated"] is True and len(r.items) == 2


async def test_limit_zero_pushdown_fetches_no_rows(storage):
    calls = []
    real_search = storage.hypernodes.search

    async def spy(*a, **kw):
        calls.append(1)
        return await real_search(*a, **kw)

    with patch.object(storage.hypernodes, "search", spy):
        r = await run(EQUIVALENT["node count"].replace("aggregate:", "limit: 0\n  aggregate:"))
    assert r.meta["count"] == 5 and r.items == []
    if not type(storage.hypernodes).supports_aggregate_pushdown:
        return   # the default implementation legitimately pages through search()
    assert calls == []


async def test_limit_zero_is_only_valid_with_aggregate(storage):
    from hgai_module_shql.parser import SHQLError
    with pytest.raises(SHQLError, match="limit"):
        await run("shql:\n  from: g\n  limit: 0\n  where:\n    - node: '?n'\n")


async def test_infer_is_never_pushed_down(storage):
    # Inferred edges are synthesized at query time; storage cannot count them.
    plan = shql_engine._plan_aggregate_pushdown(
        aggregate={"count": True}, where_patterns=[{"edge": "?e"}], select_fields=["?e.id"],
        graph_ids=["g"], pit=None, infer=True, distinct=False,
    )
    assert plan is None


async def test_measure_values_are_correct(storage):
    r = await run(EQUIVALENT["grouped measures"])
    assert r.meta["sum"] == {"n.attributes.age": 169}       # "n/a" ignored
    assert r.meta["group_measures"]["eng"] == {
        "sum": {"n.attributes.age": 70}, "avg": {"n.attributes.age": 35}, "min": {"n.attributes.age": 30},
    }
    assert r.meta["group_measures"]["None"]["sum"] == {"n.attributes.age": 99}   # n6, no dept


async def test_empty_match_yields_neutral_measure_values(storage):
    r = await run(EQUIVALENT["measures over an empty match"])
    assert r.meta["count"] == 0
    assert r.meta["sum"] == {"n.attributes.age": 0}
    assert r.meta["avg"] == {"n.attributes.age": None}
    assert r.meta["min"] == {"n.attributes.age": None}


async def test_measures_beyond_the_cap_are_exact_only_when_pushed_down(storage, monkeypatch):
    monkeypatch.setattr(get_settings(), "shql_max_node_candidates", 1)
    q = EQUIVALENT["global sum/avg/min/max"].replace("aggregate:", "limit: 0\n  aggregate:")
    assert (await run(q)).meta["sum"] == {"n.attributes.age": 169}
    assert (await run(q, pushdown=False)).meta["sum"] != {"n.attributes.age": 169}


class _RowsStore:
    def __init__(self, rows):
        self.rows = rows

    async def aggregate(self, filters, spec):
        return self.rows if spec.group_by else [{"count": 2, "m0": 3}]


async def test_str_key_collisions_merge_counts_but_bail_out_when_measures_are_requested():
    rows = [{"x": 1, "count": 1, "m0": 1}, {"x": "1", "count": 2, "m0": 2}]
    plan = shql_engine._AggregatePlan(_RowsStore(rows), None, "x", [])
    assert (await shql_engine._run_aggregate_pushdown(plan, {"group_by": "n.x"}))["groups"] == {"1": 3}
    plan = shql_engine._AggregatePlan(_RowsStore(rows), None, "x", [("sum", "n.y", "y")])
    assert await shql_engine._run_aggregate_pushdown(plan, {"group_by": "n.x", "sum": "n.y"}) is None


@pytest.mark.parametrize("aggregate, message", [
    ("{sum: 5}", "aggregate.sum"),
    ("{avg: []}", "aggregate.avg"),
    ("{min: [a, 3]}", "aggregate.min"),
    ("{max: '?n.age'}", "leading '?'"),
    ("[count]", "must be a mapping"),
])
def test_aggregate_block_validation(aggregate, message):
    from hgai_module_shql.parser import parse_shql, validate_shql
    shql = parse_shql(f"shql:\n  from: g\n  aggregate: {aggregate}\n")
    assert any(message in e for e in validate_shql(shql))
