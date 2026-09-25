"""Conformance tests for storage-layer ordered paging (`search_ordered`).

Same idea as test_storage_aggregate.py: identical assertions on every backend
in `tests.storage_fixtures.BACKENDS`.
"""

import pytest

from hgai_module_storage.aggregate import AggregateSpecError
from hgai_module_storage.ordering import normalise_order, search_ordered_via_search
from tests.storage_fixtures import NODES, _MemNodes, ef, mongod, nf, stores  # noqa: F401


def ids(docs):
    return [d["id"] for d in docs]


# active nodes: n1 person age30, n2 person age40, n3 person age"n/a", n4 place (no age), n6 person age99


async def test_ascending_puts_missing_first_and_numbers_before_strings(stores):
    nodes, _ = stores
    got = await nodes.search_ordered(nf(), [("attributes.age", False)])
    assert ids(got) == ["n4", "n1", "n2", "n6", "n3"]


async def test_descending_is_the_exact_reverse(stores):
    nodes, _ = stores
    got = await nodes.search_ordered(nf(), [("attributes.age", True)])
    assert ids(got) == ["n3", "n6", "n2", "n1", "n4"]


async def test_ties_break_by_id_ascending_in_both_directions(stores):
    nodes, _ = stores
    assert ids(await nodes.search_ordered(nf(), [("type", False)])) == ["n1", "n2", "n3", "n6", "n4"]
    assert ids(await nodes.search_ordered(nf(), [("type", True)])) == ["n4", "n1", "n2", "n3", "n6"]


async def test_mixed_direction_multi_key(stores):
    nodes, _ = stores
    got = await nodes.search_ordered(nf(), [("type", False), ("attributes.age", True)])
    assert ids(got) == ["n3", "n6", "n2", "n1", "n4"]


async def test_skip_and_limit_page_without_gaps_or_overlap(stores):
    nodes, _ = stores
    order = [("attributes.age", False)]
    full = ids(await nodes.search_ordered(nf(), order))
    pages = [ids(await nodes.search_ordered(nf(), order, skip=s, limit=2)) for s in (0, 2, 4)]
    assert pages == [full[0:2], full[2:4], full[4:6]]
    assert await nodes.search_ordered(nf(), order, skip=50, limit=2) == []
    assert await nodes.search_ordered(nf(), order, limit=0) == []


async def test_filters_apply_before_ordering(stores):
    nodes, _ = stores
    got = await nodes.search_ordered(nf(node_type="person"), [("attributes.age", True)], limit=2)
    assert ids(got) == ["n3", "n6"]


async def test_edges(stores):
    _, edges = stores
    got = await edges.search_ordered(ef(), [("attributes.weight", True)])
    assert ids(got) == ["e4", "e2", "e1", "e3"]
    assert ids(await edges.search_ordered(ef(), [("relation", True), ("id", True)])) == ["e4", "e3", "e2", "e1"]


@pytest.mark.parametrize("order", [
    [("$where", False)],
    [("members.node_id", False)],
    [("type", False), ("type", True)],
])
async def test_invalid_order_is_rejected_by_every_backend(stores, order):
    nodes, _ = stores
    with pytest.raises(AggregateSpecError):
        await nodes.search_ordered(nf(), order)


def test_tie_breakers_are_appended_once():
    assert normalise_order([("type", False)]) == [("type", False), ("id", False), ("hypergraph_id", False)]
    assert normalise_order([("id", True)]) == [("id", True), ("hypergraph_id", False)]


async def test_result_does_not_depend_on_insertion_order():
    forward = _MemNodes(list(NODES))
    backward = _MemNodes(list(reversed(NODES)))
    for order in ([("type", False)], [("type", True)], [("attributes.age", False)]):
        assert ids(await forward.search_ordered(nf(), order)) == ids(await backward.search_ordered(nf(), order))


async def test_default_implementation_streams_in_tiny_batches():
    store = _MemNodes(NODES)
    order = [("attributes.age", True)]
    for skip, limit in ((0, 2), (1, 3), (3, 10)):
        expected = ids(await store.search_ordered(nf(), order, skip=skip, limit=limit))
        streamed = await search_ordered_via_search(store.search, nf(), order, skip, limit, batch_size=1)
        assert ids(streamed) == expected


def test_capability_flags():
    from hgai_module_storage.backend import HyperedgeStore, HypernodeStore
    from hgai_module_storage_mongodb.stores.hyperedges import MongoHyperedgeStore
    from hgai_module_storage_mongodb.stores.hypernodes import MongoHypernodeStore
    assert not HypernodeStore.supports_ordered_search and not HyperedgeStore.supports_ordered_search
    assert MongoHypernodeStore.supports_ordered_search and MongoHyperedgeStore.supports_ordered_search
