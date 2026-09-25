"""Tests for the SHQL member-pattern matching engine (positional seq support)."""

from unittest.mock import AsyncMock, patch

import pytest

from hgai_module_shql.engine import (
    _apply_order_by,
    _eval_edge_pattern,
    _match_members,
    _match_members_expand,
    _parse_order_by,
)


def _members(*node_ids):
    return [{"node_id": nid, "seq": i} for i, nid in enumerate(node_ids)]


def test_seq_matches_only_the_correct_position():
    edge_members = _members("group:three-stooges", "person:moe")
    result = _match_members(edge_members, [{"id": "group:three-stooges", "seq": 0}], {})
    assert result is not None


def test_seq_rejects_id_present_but_wrong_position():
    edge_members = _members("person:moe", "group:three-stooges")
    result = _match_members(edge_members, [{"id": "group:three-stooges", "seq": 0}], {})
    assert result is None


def test_seq_only_binds_the_member_at_that_position():
    edge_members = _members("person:moe", "person:larry")
    result = _match_members(edge_members, [{"bind": "?first", "seq": 0}], {})
    assert result == {"?first": "person:moe"}


def test_match_members_expand_respects_seq_for_bound_anchor():
    """Regression: a member pattern that references an already-bound variable
    together with seq must be treated as an anchor (matched deterministically),
    not misclassified as an unconstrained wildcard that overwrites the binding."""
    edge_members = _members("group:three-stooges", "person:moe")
    binding = {"?group": {"id": "group:three-stooges"}}
    result = _match_members_expand(edge_members, [{"bind": "?group", "seq": 0}], binding)
    assert len(result) == 1
    assert result[0]["?group"] == {"id": "group:three-stooges"}


def test_match_members_expand_seq_anchor_plus_wildcard():
    """seq: 0 anchors the first member; a plain wildcard pattern enumerates the rest."""
    edge_members = _members("person:president", "nation:usa")
    result = _match_members_expand(
        edge_members,
        [{"bind": "?president_id", "seq": 0}, {"bind": "?other"}],
        {},
    )
    assert len(result) == 1
    assert result[0]["?president_id"] == "person:president"
    assert result[0]["?other"] == "nation:usa"


def test_match_members_expand_seq_anchor_rejects_wrong_position():
    """id + seq together must bind to the same element: person:president is
    present but at seq 1, not seq 0, so the anchor must not match."""
    edge_members = _members("nation:usa", "person:president")
    result = _match_members_expand(
        edge_members,
        [{"id": "person:president", "seq": 0}],
        {},
    )
    assert result == []


# ── infer: true + relation: filter interaction ─────────────────────────────
#
# Regression coverage for a bug where querying `relation: rel:member-of`
# (a relation that only ever exists as something inferred via an
# `owl:inverse-of` axiom on `rel:member`) returned nothing, even with
# `infer: true` — the literal storage search filtered by `rel:member-of`
# *before* expansion ran, so expand_edge_closure was always handed an empty
# candidate set to expand from. See engine.py's `_eval_edge_pattern`.

_MEMBER_EDGE = {
    "id": "edge:rat-pack-member",
    "relation": "rel:member",
    "flavor": "hub",
    "members": [
        {"node_id": "group:rat-pack", "seq": 0},
        {"node_id": "person:frank", "seq": 1},
    ],
}

_INVERSE_OF_AXIOM = {
    "id": "edge:member-inverse-of-member-of",
    "relation": "owl:inverse-of",
    "flavor": "hub",
    "members": [
        {"node_id": "rel:member", "seq": 0},
        {"node_id": "rel:member-of", "seq": 1},
    ],
}


class _FakeHyperedgeStore:
    """Minimal stand-in for the storage layer's hyperedges collection.

    `search` returns the literal `rel:member` edge regardless of the
    requested relation, mirroring the fix's expectation that the literal
    fetch stays relation-agnostic when inferring. `find_for_transitive`
    (used by `hgai.core.inference.get_axiom_edges`) returns the inverse-of
    axiom only for axiom lookups that actually mention one of the two
    member/member-of relations, same as a real query would.
    """

    def __init__(self):
        self.search_relations_seen = []

    async def search(self, filters, skip=0, limit=2000):
        self.search_relations_seen.append(filters.relation)
        if filters.relation not in (None, "rel:member"):
            return []
        return [dict(_MEMBER_EDGE)]

    async def find_for_transitive(self, tsf):
        if tsf.relation == "owl:inverse-of" and (
            "rel:member" in tsf.member_node_ids or "rel:member-of" in tsf.member_node_ids
        ):
            return [dict(_INVERSE_OF_AXIOM)]
        return []


class _FakeStorage:
    def __init__(self, hyperedges):
        self.hyperedges = hyperedges


@pytest.mark.asyncio
async def test_infer_true_finds_inferred_relation_via_axiom():
    """Querying the inferred-only relation directly must still find the
    edges derived from its literal counterpart via owl:inverse-of."""
    fake_hyperedges = _FakeHyperedgeStore()
    fake_storage = _FakeStorage(fake_hyperedges)

    with patch("hgai_module_shql.engine.get_storage", return_value=fake_storage), \
         patch("hgai.core.inference.get_storage", return_value=fake_storage):
        result = await _eval_edge_pattern(
            {"bind": "?e", "relation": "rel:member-of"},
            graph_ids=["hello-world"],
            pit=None,
            bindings=[{}],
            infer=True,
        )

    assert len(result) == 1
    edge = result[0]["?e"]
    assert edge["relation"] == "rel:member-of"
    assert edge["_inferred"] is True
    assert edge["members"] == [
        {"node_id": "person:frank", "seq": 0},
        {"node_id": "group:rat-pack", "seq": 1},
    ]
    # The literal fetch must not have been pre-filtered to "rel:member-of"
    # (which would have starved expansion of anything to derive from).
    assert None in fake_hyperedges.search_relations_seen


@pytest.mark.asyncio
async def test_infer_true_excludes_other_relations_after_expansion():
    """A relation filter must still exclude edges of unrelated relations
    that happened to expand from the same literal candidate set."""
    fake_hyperedges = _FakeHyperedgeStore()
    fake_storage = _FakeStorage(fake_hyperedges)

    with patch("hgai_module_shql.engine.get_storage", return_value=fake_storage), \
         patch("hgai.core.inference.get_storage", return_value=fake_storage):
        result = await _eval_edge_pattern(
            {"bind": "?e", "relation": "rel:member-of"},
            graph_ids=["hello-world"],
            pit=None,
            bindings=[{}],
            infer=True,
        )

    assert all(binding["?e"]["relation"] == "rel:member-of" for binding in result)


# ── infer: true + owl:transitive, open-ended (Visualize-shaped) query ──────
#
# Visualize's "show inferred" fetch (ui/js/app.js:fetchInferredEdges) runs
# exactly this pattern — a bare `edge: ?edge`, no relation/members filter —
# because it wants every inferred edge in the graph, not a targeted
# start/end pair. Regression coverage for the fix that lets owl:transitive
# participate in that same general expansion (previously only owl:
# inverse-of/symmetric/broaderTransitive did; transitive closure only fired
# for a fully-bound 2-endpoint pattern, so a whole-graph query like this
# one, or Visualize, never saw a transitively-derived edge at all).

_PARENT_EDGE_AB = {
    "id": "edge-ab", "relation": "rel:parent", "flavor": "hub",
    "members": [{"node_id": "andy-1", "seq": 0}, {"node_id": "andy-2", "seq": 1}],
}
_PARENT_EDGE_BC = {
    "id": "edge-bc", "relation": "rel:parent", "flavor": "hub",
    "members": [{"node_id": "andy-2", "seq": 0}, {"node_id": "andy-3", "seq": 1}],
}
_TRANSITIVE_AXIOM = {
    "id": "axiom-transitive-parent", "relation": "owl:transitive", "flavor": "hub",
    "members": [{"node_id": "rel:parent", "seq": 0}],
}


class _FakeTransitiveStore:
    """Fake storage backing a 2-hop rel:parent chain (andy-1->andy-2->andy-3)
    declared owl:transitive, for exercising the open-ended (no bound
    endpoints) `infer: true` path end to end."""

    async def search(self, filters, skip=0, limit=2000):
        if filters.relation in (None, "rel:parent"):
            return [dict(_PARENT_EDGE_AB), dict(_PARENT_EDGE_BC)]
        return []

    async def find_for_transitive(self, tsf):
        if tsf.relation == "owl:transitive" and "rel:parent" in tsf.member_node_ids:
            return [dict(_TRANSITIVE_AXIOM)]
        if tsf.relation == "rel:parent":
            edges = [_PARENT_EDGE_AB, _PARENT_EDGE_BC]
            return [dict(e) for e in edges if any(m["node_id"] in tsf.member_node_ids for m in e["members"])]
        return []


@pytest.mark.asyncio
async def test_infer_true_open_ended_query_surfaces_transitive_edge():
    """The exact pattern shape Visualize's whole-graph inferred-edge fetch
    uses (`edge: ?edge`, no relation/members filter) must include the
    transitively-derived andy-1 -> andy-3 edge, not just literal ones."""
    fake_storage = _FakeStorage(_FakeTransitiveStore())

    with patch("hgai_module_shql.engine.get_storage", return_value=fake_storage), \
         patch("hgai.core.inference.get_storage", return_value=fake_storage):
        result = await _eval_edge_pattern(
            {"bind": "?edge"},
            graph_ids=["test-ordering"],
            pit=None,
            bindings=[{}],
            infer=True,
        )

    transitive = [
        b["?edge"] for b in result
        if b["?edge"].get("relation") == "rel:parent" and b["?edge"].get("_inferred")
    ]
    assert len(transitive) == 1
    edge = transitive[0]
    assert edge["members"] == [
        {"node_id": "andy-1", "seq": 0},
        {"node_id": "andy-3", "seq": 1},
    ]
    assert edge["_transitive"] is True
    assert edge["_transitive_path"] == ["edge-ab", "edge-bc"]


# ── order_by: descending + multi-field sort ─────────────────────────────────

def test_parse_order_by_single_field_defaults_ascending():
    assert _parse_order_by("?e.relation") == [("e.relation", False)]


def test_parse_order_by_desc_suffix_is_case_insensitive():
    assert _parse_order_by("?e.relation DESC") == [("e.relation", True)]
    assert _parse_order_by("?e.relation desc") == [("e.relation", True)]
    assert _parse_order_by("?e.relation asc") == [("e.relation", False)]


def test_parse_order_by_list_preserves_priority_order():
    assert _parse_order_by(["?e.relation desc", "?e.label"]) == [
        ("e.relation", True),
        ("e.label", False),
    ]


def test_apply_order_by_single_field_descending():
    rows = [{"e.label": "a"}, {"e.label": "c"}, {"e.label": "b"}]
    result = _apply_order_by(rows, "?e.label desc")
    assert [r["e.label"] for r in result] == ["c", "b", "a"]


def test_apply_order_by_multi_field_mixed_directions():
    """Primary key ascending, secondary key descending — the classic case a
    single-field sort can't express."""
    rows = [
        {"e.relation": "b", "e.label": "y"},
        {"e.relation": "a", "e.label": "z"},
        {"e.relation": "a", "e.label": "x"},
        {"e.relation": "b", "e.label": "w"},
    ]
    result = _apply_order_by(rows, ["?e.relation", "?e.label desc"])
    assert [(r["e.relation"], r["e.label"]) for r in result] == [
        ("a", "z"),
        ("a", "x"),
        ("b", "y"),
        ("b", "w"),
    ]


# ── Candidate caps / truncated flag ───────────────────────────────────────────

class _CountingNodeStore:
    def __init__(self, n):
        self.docs = [{"id": f"n{i}"} for i in range(n)]
        self.limits_seen = []

    async def search(self, filters, skip=0, limit=50):
        self.limits_seen.append(limit)
        return [dict(d) for d in self.docs[skip: skip + limit]]


@pytest.mark.asyncio
@pytest.mark.parametrize("n, expect_truncated", [(3, False), (4, True)])
async def test_node_pattern_cap_sets_truncated(n, expect_truncated, monkeypatch):
    from hgai.config import get_settings
    from hgai.core.inference import truncation_sink
    from hgai_module_shql.engine import _eval_node_pattern

    monkeypatch.setattr(get_settings(), "shql_max_node_candidates", 3)
    store = _CountingNodeStore(n)
    sink = []
    token = truncation_sink.set(sink)
    try:
        with patch("hgai_module_shql.engine.get_storage",
                   return_value=type("S", (), {"hypernodes": store})()):
            result = await _eval_node_pattern(
                {"bind": "?n"}, graph_ids=["g"], pit=None, bindings=[{}],
            )
    finally:
        truncation_sink.reset(token)

    assert len(result) == min(n, 3)
    assert store.limits_seen == [4]          # cap + 1 probe
    assert bool(sink) is expect_truncated
