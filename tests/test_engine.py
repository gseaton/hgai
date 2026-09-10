"""Tests for the HypergraphAI core engine."""

from datetime import datetime, timezone

import pytest
from hgai.core.engine import (
    HYPERNODE_TRACKED_FIELDS,
    _append_mutation,
    _create_delta,
    _update_delta,
    generate_hyperkey,
)


def test_hyperkey_deterministic():
    """Same inputs always produce the same hyperkey."""
    key1 = generate_hyperkey("has-member", ["node-a", "node-b"], "my-graph")
    key2 = generate_hyperkey("has-member", ["node-a", "node-b"], "my-graph")
    assert key1 == key2


def test_hyperkey_member_order_insensitive():
    """Hyperkey is based on sorted member IDs, so order doesn't matter."""
    key1 = generate_hyperkey("has-member", ["node-a", "node-b", "node-c"], "my-graph")
    key2 = generate_hyperkey("has-member", ["node-c", "node-a", "node-b"], "my-graph")
    assert key1 == key2


def test_hyperkey_different_relations():
    """Different relations produce different keys."""
    key1 = generate_hyperkey("has-member", ["node-a", "node-b"], "my-graph")
    key2 = generate_hyperkey("sibling", ["node-a", "node-b"], "my-graph")
    assert key1 != key2


def test_hyperkey_different_graphs():
    """Same edge in different graphs produces different keys."""
    key1 = generate_hyperkey("has-member", ["node-a", "node-b"], "graph-1")
    key2 = generate_hyperkey("has-member", ["node-a", "node-b"], "graph-2")
    assert key1 != key2


def test_hyperkey_length():
    """Hyperkey is 32 hex characters (128 bits of SHA-256)."""
    key = generate_hyperkey("has-member", ["node-a"], "my-graph")
    assert len(key) == 32
    assert all(c in "0123456789abcdef" for c in key)


def test_hyperkey_same_relation_and_members_different_window_differ():
    """Same relation/members/graph but different validity windows produce
    different keys — e.g. the same lineup existing during two eras."""
    era1 = generate_hyperkey(
        "rel:member", ["moe", "larry", "shemp"], "stooges-graph",
        valid_from=datetime(1958, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(1959, 1, 1, tzinfo=timezone.utc),
    )
    era2 = generate_hyperkey(
        "rel:member", ["moe", "larry", "shemp"], "stooges-graph",
        valid_from=datetime(1959, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(1960, 1, 1, tzinfo=timezone.utc),
    )
    assert era1 != era2


def test_hyperkey_same_window_is_still_a_duplicate():
    """Same relation/members/graph AND same validity window still collide —
    hashing only distinguishes windows that actually differ."""
    key1 = generate_hyperkey(
        "rel:member", ["moe", "larry", "shemp"], "stooges-graph",
        valid_from=datetime(1958, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(1959, 1, 1, tzinfo=timezone.utc),
    )
    key2 = generate_hyperkey(
        "rel:member", ["shemp", "moe", "larry"], "stooges-graph",
        valid_from=datetime(1958, 1, 1, tzinfo=timezone.utc),
        valid_to=datetime(1959, 1, 1, tzinfo=timezone.utc),
    )
    assert key1 == key2


def test_hyperkey_unbounded_window_differs_from_bounded():
    """No validity window (None/None) is a distinct identity from any
    explicit bounded window for the same relation/members."""
    unbounded = generate_hyperkey("rel:member", ["moe", "larry", "shemp"], "stooges-graph")
    bounded = generate_hyperkey(
        "rel:member", ["moe", "larry", "shemp"], "stooges-graph",
        valid_from=datetime(1958, 1, 1, tzinfo=timezone.utc),
    )
    assert unbounded != bounded


def test_hyperkey_instant_normalizes_across_timezones():
    """The same instant expressed in different timezones (or naive-but-UTC)
    hashes identically, so equivalent inputs are never treated as distinct."""
    from datetime import timedelta

    utc_dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    offset_dt = utc_dt.astimezone(timezone(timedelta(hours=-5)))
    naive_dt = datetime(2026, 1, 1, 12, 0)  # naive, treated as UTC

    key_utc = generate_hyperkey("rel:member", ["a"], "g", valid_from=utc_dt)
    key_offset = generate_hyperkey("rel:member", ["a"], "g", valid_from=offset_dt)
    key_naive = generate_hyperkey("rel:member", ["a"], "g", valid_from=naive_dt)

    assert key_utc == key_offset == key_naive


# ─── Mutation tracking ────────────────────────────────────────────────────────

def test_create_delta_skips_blank_fields():
    """A create-mutation's delta only lists fields that were actually
    populated, not every default (None/[]/{}) tracked field."""
    doc = {
        "label": "Curly", "type": "Person", "description": None, "tags": [],
        "status": "active", "attributes": {}, "valid_from": None,
        "valid_to": None, "media": [], "default_media_id": None,
    }
    delta = _create_delta(doc, HYPERNODE_TRACKED_FIELDS)
    fields = {d["field"] for d in delta}
    assert fields == {"label", "type", "status"}
    assert all(d["old"] is None for d in delta)


def test_update_delta_only_includes_actual_changes():
    """A field resubmitted with its already-current value produces no delta
    entry for that field — only genuinely-changed fields are included."""
    existing = {"label": "Curly", "status": "active"}
    delta = _update_delta(existing, {"label": "Curly", "status": "draft"}, HYPERNODE_TRACKED_FIELDS)
    assert delta == [{"field": "status", "old": "active", "new": "draft"}]


def test_update_delta_empty_when_nothing_changed():
    existing = {"label": "Curly"}
    delta = _update_delta(existing, {"label": "Curly"}, HYPERNODE_TRACKED_FIELDS)
    assert delta == []


def test_append_mutation_skips_empty_delta():
    """A no-op update (empty delta) never gets persisted as a mutation entry."""
    result = _append_mutation([], "mutate", [], "admin")
    assert result == []


def test_append_mutation_appends_first_entry():
    result = _append_mutation([], "create", [{"field": "label", "old": None, "new": "Curly"}], "admin")
    assert len(result) == 1
    assert result[0]["mutation"] == "create"
    assert result[0]["by"] == "admin"
    assert "ts" in result[0]


def test_append_mutation_suppresses_redundant_sequential_entry():
    """If the candidate mutation (same kind + same delta) matches the most
    recently recorded entry, it is not persisted — the original list is
    returned unchanged (by identity)."""
    delta = [{"field": "label", "old": "A", "new": "B"}]
    history = _append_mutation([], "mutate", delta, "admin")
    result = _append_mutation(history, "mutate", delta, "admin")
    assert result is history  # nothing new persisted


def test_append_mutation_does_not_suppress_non_adjacent_repeat():
    """A candidate that matches an OLDER entry (not the most recent one)
    still gets appended — only back-to-back duplicates are suppressed."""
    forward = [{"field": "label", "old": "A", "new": "B"}]
    backward = [{"field": "label", "old": "B", "new": "A"}]
    history = _append_mutation([], "mutate", forward, "admin")
    history = _append_mutation(history, "mutate", backward, "admin")
    history = _append_mutation(history, "mutate", forward, "admin")  # same as entry[0], not entry[-1]
    assert len(history) == 3


def test_append_mutation_different_kind_same_delta_still_appends():
    """Same delta content but a different mutation kind is not considered
    a redundant repeat."""
    delta = [{"field": "label", "old": None, "new": "Curly"}]
    history = _append_mutation([], "create", delta, "admin")
    history2 = _append_mutation(history, "mutate", delta, "admin")
    assert len(history2) == 2
