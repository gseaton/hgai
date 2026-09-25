"""Conformance tests for storage-layer aggregation (HypernodeStore/HyperedgeStore.aggregate).

Every backend must return identical rows for identical data. The same
assertions run against every backend in `tests.storage_fixtures.BACKENDS`
(an in-memory reference using the ABC default, and a real `mongod`, skipped
when none is installed).
"""

import pytest

from hgai_module_storage.aggregate import (
    AggregateSpecError,
    aggregate_via_search,
    normalise_spec,
)
from hgai_module_storage.backend import HyperedgeStore, HypernodeStore
from hgai_module_storage.filters import AggregateMeasure as M, AggregateSpec
from tests.storage_fixtures import (  # noqa: F401  (fixtures are used by name)
    NODES, PIT, _MemNodes, ef, mongod, nf, stores,
)


# ── Semantics ─────────────────────────────────────────────────────────────────

async def test_default_spec_is_a_document_count(stores):
    nodes, _ = stores
    assert await nodes.aggregate(nf(), AggregateSpec()) == [{"count": 5}]
    assert await nodes.count(nf()) == 5


async def test_count_respects_status_and_pit(stores):
    nodes, _ = stores
    assert await nodes.count(nf(status="archived")) == 1
    assert await nodes.count(nf(pit=PIT)) == 4          # n6 expired before PIT
    assert await nodes.count(nf(status=None)) == 6


async def test_group_by_type_ordered_ascending_by_default(stores):
    nodes, _ = stores
    rows = await nodes.aggregate(nf(), AggregateSpec(group_by=["type"]))
    assert rows == [{"type": "person", "count": 4}, {"type": "place", "count": 1}]


async def test_missing_attribute_groups_as_none_and_sorts_first(stores):
    nodes, _ = stores
    rows = await nodes.aggregate(nf(), AggregateSpec(group_by=["attributes.dept"]))
    assert rows == [
        {"attributes.dept": None, "count": 2},   # n4, n6
        {"attributes.dept": "eng", "count": 2},  # n1, n2
        {"attributes.dept": "ops", "count": 1},  # n3
    ]


async def test_tags_are_unwound_and_untagged_docs_form_a_null_group(stores):
    nodes, _ = stores
    rows = await nodes.aggregate(nf(), AggregateSpec(group_by=["tags"]))
    assert rows == [
        {"tags": None, "count": 2},  # n3, n4
        {"tags": "a", "count": 3},   # n1, n2, n6
        {"tags": "b", "count": 1},   # n1
    ]


async def test_numeric_measures_ignore_non_numbers_and_bools(stores):
    nodes, _ = stores
    spec = AggregateSpec(measures=[
        M("count"),
        M("count", "attributes.age"),
        M("sum", "attributes.age"),
        M("avg", "attributes.age"),
        M("sum", "attributes.salary"),
        M("count_distinct", "attributes.dept"),
        M("count_numeric", "attributes.age"),
        M("count_numeric", "attributes.salary"),
    ])
    (row,) = await nodes.aggregate(nf(pit=PIT), spec)
    assert row == {
        "count": 4,
        "count_attributes_age": 3,      # 30, 40, "n/a"  (null is not counted)
        "sum_attributes_age": 70,       # "n/a" ignored
        "avg_attributes_age": 35,       # over the two numbers only
        "sum_attributes_salary": 300,   # True ignored
        "count_distinct_attributes_dept": 2,
        "count_numeric_attributes_age": 2,      # "n/a" is text
        "count_numeric_attributes_salary": 2,   # True is not a number
    }


async def test_min_max_follow_bson_type_order(stores):
    nodes, _ = stores
    spec = AggregateSpec(measures=[M("min", "attributes.age"), M("max", "attributes.age")])
    (row,) = await nodes.aggregate(nf(pit=PIT), spec)
    assert row == {"min_attributes_age": 30, "max_attributes_age": "n/a"}  # numbers < strings


async def test_no_group_by_over_zero_docs_still_yields_one_row(stores):
    nodes, _ = stores
    spec = AggregateSpec(measures=[
        M("count"), M("sum", "attributes.age"), M("avg", "attributes.age"),
        M("min", "attributes.age"), M("count_distinct", "attributes.dept"),
    ])
    rows = await nodes.aggregate(nf(node_type="nothing"), spec)
    assert rows == [{
        "count": 0, "sum_attributes_age": 0, "avg_attributes_age": None,
        "min_attributes_age": None, "count_distinct_attributes_dept": 0,
    }]


async def test_group_by_over_zero_docs_is_empty(stores):
    nodes, _ = stores
    assert await nodes.aggregate(nf(node_type="nothing"), AggregateSpec(group_by=["type"])) == []


async def test_order_by_measure_descending_with_limit(stores):
    nodes, _ = stores
    spec = AggregateSpec(group_by=["type"], order_by=[("count", True)], limit=1)
    assert await nodes.aggregate(nf(), spec) == [{"type": "person", "count": 4}]


async def test_aliases_and_multi_key_grouping(stores):
    nodes, _ = stores
    spec = AggregateSpec(
        group_by=["type", "attributes.dept"],
        measures=[M("sum", "attributes.salary", alias="pay")],
    )
    rows = await nodes.aggregate(nf(), spec)
    assert rows == [
        {"type": "person", "attributes.dept": None, "pay": 0},
        {"type": "person", "attributes.dept": "eng", "pay": 300},
        {"type": "person", "attributes.dept": "ops", "pay": 0},
        {"type": "place", "attributes.dept": None, "pay": 0},
    ]


async def test_edges_group_by_relation(stores):
    _, edges = stores
    spec = AggregateSpec(
        group_by=["relation"],
        measures=[M("count"), M("sum", "attributes.weight"), M("max", "attributes.weight")],
    )
    assert await edges.aggregate(ef(), spec) == [
        {"relation": "knows", "count": 3, "sum_attributes_weight": 4.0, "max_attributes_weight": 2.5},
        {"relation": "likes", "count": 1, "sum_attributes_weight": 10, "max_attributes_weight": 10},
    ]
    assert await edges.count(ef(relation="knows")) == 3
    assert await edges.aggregate(ef(), AggregateSpec(group_by=["flavor"])) == [
        {"flavor": "hub", "count": 3}, {"flavor": "symmetric", "count": 1},
    ]


# ── Spec validation (backend-independent) ─────────────────────────────────────

@pytest.mark.parametrize("spec", [
    AggregateSpec(group_by=["$where"]),
    AggregateSpec(group_by=["attributes"]),
    AggregateSpec(group_by=["attributes.a.$b"]),
    AggregateSpec(group_by=["members.node_id"]),
    AggregateSpec(group_by=["type", "type"]),
    AggregateSpec(measures=[M("median", "attributes.x")]),
    AggregateSpec(measures=[M("sum")]),
    AggregateSpec(measures=[M("count", alias="not valid")]),
    AggregateSpec(measures=[M("count"), M("count")]),
    AggregateSpec(measures=[]),
    AggregateSpec(order_by=[("nope", False)]),
    AggregateSpec(limit=-1),
])
def test_invalid_specs_are_rejected(spec):
    with pytest.raises(AggregateSpecError):
        normalise_spec(spec)


async def test_invalid_spec_is_rejected_by_every_backend(stores):
    nodes, _ = stores
    with pytest.raises(AggregateSpecError):
        await nodes.aggregate(nf(), AggregateSpec(group_by=["$where"]))


# ── Default implementation specifics ──────────────────────────────────────────

async def test_default_pages_through_search_in_small_batches():
    store = _MemNodes(NODES)
    spec = AggregateSpec(group_by=["type"], measures=[M("count"), M("sum", "attributes.age")])
    paged = await aggregate_via_search(store.search, nf(), spec, batch_size=2)
    assert paged == await store.aggregate(nf(), spec)


def test_pushdown_flags():
    assert HypernodeStore.supports_aggregate_pushdown is False
    assert HyperedgeStore.supports_aggregate_pushdown is False
    from hgai_module_storage_mongodb.stores.hyperedges import MongoHyperedgeStore
    from hgai_module_storage_mongodb.stores.hypernodes import MongoHypernodeStore
    assert MongoHypernodeStore.supports_aggregate_pushdown is True
    assert MongoHyperedgeStore.supports_aggregate_pushdown is True


@pytest.mark.parametrize("fn", ["count", "count_distinct", "count_numeric", "sum", "avg", "min", "max"])
@pytest.mark.parametrize("values", [
    [], [None], [1, 2, 3], [1.5, 2.5], [1, "a", True, None, 2], ["b", "a"], [3, 3, 3], [[1], [2]],
])
def test_reduce_values_agrees_with_the_streaming_accumulator(fn, values):
    from hgai_module_storage.aggregate import Accumulator, reduce_values
    acc = Accumulator(AggregateSpec(measures=[M(fn, "attributes.x", alias="r")]))
    for v in values:
        acc.add({"attributes": {} if v is None else {"x": v}})
    assert reduce_values(fn, values) == acc.rows()[0]["r"]
