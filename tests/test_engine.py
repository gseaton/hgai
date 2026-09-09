"""Tests for the HypergraphAI core engine."""

from datetime import datetime, timezone

import pytest
from hgai.core.engine import generate_hyperkey


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
