"""Tests for the SHQL member-pattern matching engine (positional seq support)."""

from hgai_module_shql.engine import _match_members, _match_members_expand


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
