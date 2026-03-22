"""Tests for the HypergraphAI core engine."""

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
