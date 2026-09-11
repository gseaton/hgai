"""Tests for the HypergraphAI inferencing primitives."""

from types import SimpleNamespace

import pytest
from hgai.core.inference import (
    _atomic_facts,
    _make_inferred_edge,
    _member_ids,
    _other_member,
    atomic_pairs,
)


def _m(node_id, seq):
    return {"node_id": node_id, "seq": seq}


def test_atomic_pairs_hub_fans_out_from_first_member():
    """hub: the seq-0 member is the hub; every other member is a spoke,
    each an independent (hub, spoke) fact."""
    members = [_m("adam", 0), _m("cain", 1), _m("abel", 2), _m("seth", 3)]
    pairs = atomic_pairs(members, "hub")
    assert pairs == [("adam", "cain"), ("adam", "abel"), ("adam", "seth")]


def test_atomic_pairs_hub_uses_seq_not_list_order():
    """Decomposition follows `seq`, not the order members happen to be
    stored/passed in — a shuffled list with correct seq values must
    decompose identically to the sorted version."""
    shuffled = [_m("seth", 3), _m("adam", 0), _m("abel", 2), _m("cain", 1)]
    ordered = [_m("adam", 0), _m("cain", 1), _m("abel", 2), _m("seth", 3)]
    assert atomic_pairs(shuffled, "hub") == atomic_pairs(ordered, "hub")


def test_atomic_pairs_hub_binary():
    """A plain 2-member hub edge decomposes to exactly one directed pair."""
    assert atomic_pairs([_m("rel:parent", 0), _m("rel:father", 1)], "hub") == [
        ("rel:parent", "rel:father")
    ]


def test_atomic_pairs_hub_empty_members():
    assert atomic_pairs([], "hub") == []


def test_atomic_pairs_symmetric_full_directed_clique():
    """symmetric: every member is mutually equivalent to every other —
    every ordered pair among the members, both directions."""
    members = [_m("moe", 0), _m("larry", 1), _m("curly", 2)]
    pairs = set(atomic_pairs(members, "symmetric"))
    assert pairs == {
        ("moe", "larry"), ("larry", "moe"),
        ("moe", "curly"), ("curly", "moe"),
        ("larry", "curly"), ("curly", "larry"),
    }


def test_atomic_pairs_symmetric_binary():
    members = [_m("a", 0), _m("b", 1)]
    assert set(atomic_pairs(members, "symmetric")) == {("a", "b"), ("b", "a")}


def test_atomic_pairs_accepts_member_like_objects_not_just_dicts():
    """Works with anything exposing .node_id/.seq (e.g. EdgeMember
    instances), not only plain dicts — matches the existing
    isinstance(m, dict) pattern used elsewhere in the engine."""
    members = [SimpleNamespace(node_id="adam", seq=0), SimpleNamespace(node_id="cain", seq=1)]
    assert atomic_pairs(members, "hub") == [("adam", "cain")]


def test_atomic_pairs_rejects_unsupported_flavor():
    """EdgeFlavor only ever produces 'hub' or 'symmetric' — anything else
    means a caller passed something that isn't a real hyperedge's flavor,
    which should fail loudly rather than silently decompose wrong."""
    with pytest.raises(ValueError, match="unsupported flavor"):
        atomic_pairs([_m("a", 0), _m("b", 1)], "direct")


# ─── expand_edge helpers ────────────────────────────────────────────────────

def test_member_ids_extracts_in_list_order():
    assert _member_ids({"members": [_m("a", 1), _m("b", 0)]}) == ["a", "b"]


def test_other_member_finds_the_other_endpoint_either_direction():
    """owl:inverse-of is order-irrelevant: the lookup works from either
    endpoint of the same stored axiom edge, no mirrored edge needed."""
    axiom = {"members": [_m("rel:parent", 0), _m("rel:child", 1)]}
    assert _other_member(axiom, "rel:parent") == "rel:child"
    assert _other_member(axiom, "rel:child") == "rel:parent"


def test_other_member_none_when_relation_not_a_member():
    axiom = {"members": [_m("rel:parent", 0), _m("rel:child", 1)]}
    assert _other_member(axiom, "rel:unrelated") is None


def test_make_inferred_edge_shape():
    edge = _make_inferred_edge(
        relation="rel:child", members=[_m("cain", 0), _m("adam", 1)],
        flavor="hub", source_edge="src1", axiom="axiom1",
    )
    assert edge == {
        "relation": "rel:child",
        "flavor": "hub",
        "members": [_m("cain", 0), _m("adam", 1)],
        "_inferred": True,
        "_source_edge": "src1",
        "_axiom": "axiom1",
    }


def test_atomic_facts_ignores_list_order_not_seq():
    """Same seq assignments listed in a different order decompose to the
    same facts — atomic_pairs already sorts by seq internally."""
    a = {"relation": "rel:father", "flavor": "hub", "members": [_m("adam", 0), _m("cain", 1)]}
    b = {"relation": "rel:father", "flavor": "hub", "members": [_m("cain", 1), _m("adam", 0)]}
    assert _atomic_facts(a) == _atomic_facts(b) == {("rel:father", "adam", "cain")}


def test_atomic_facts_distinguishes_different_relations():
    a = {"relation": "rel:father", "flavor": "hub", "members": [_m("adam", 0), _m("cain", 1)]}
    b = {"relation": "rel:parent", "flavor": "hub", "members": [_m("adam", 0), _m("cain", 1)]}
    assert _atomic_facts(a) != _atomic_facts(b)


def test_atomic_facts_recognizes_bundling_shape_does_not_matter():
    """The whole reason dedup must operate on atomic facts, not whole-edge
    identity: the same underlying facts bundled as one 4-member hub edge
    vs. three separate 2-member hub edges must produce the SAME fact set,
    or a closure can re-derive "new" edges that assert nothing new."""
    bundled = {
        "relation": "rel:parent", "flavor": "hub",
        "members": [_m("adam", 0), _m("cain", 1), _m("abel", 2), _m("seth", 3)],
    }
    unbundled = [
        {"relation": "rel:parent", "flavor": "hub", "members": [_m("adam", 0), _m("cain", 1)]},
        {"relation": "rel:parent", "flavor": "hub", "members": [_m("adam", 0), _m("abel", 1)]},
        {"relation": "rel:parent", "flavor": "hub", "members": [_m("adam", 0), _m("seth", 1)]},
    ]
    unbundled_facts = set()
    for e in unbundled:
        unbundled_facts |= _atomic_facts(e)
    assert _atomic_facts(bundled) == unbundled_facts
