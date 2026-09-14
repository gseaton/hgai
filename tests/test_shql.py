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
