"""Tests for the HQL query parser and validator."""

import pytest
from hgai_module_hql.engine import parse_hql, validate_hql, HQLError


def test_parse_valid_hql_yaml():
    hql_text = """
hql:
  from: my-graph
  match:
    type: hyperedge
    relation: has-member
  return:
    - members
"""
    hql = parse_hql(hql_text)
    assert hql["from"] == "my-graph"
    assert hql["match"]["type"] == "hyperedge"
    assert "members" in hql["return"]


def test_parse_valid_hql_json():
    hql_text = '{"hql": {"from": "my-graph", "match": {"type": "hypernode"}}}'
    hql = parse_hql(hql_text)
    assert hql["from"] == "my-graph"


def test_parse_missing_hql_key():
    with pytest.raises(HQLError, match="top-level 'hql' key"):
        parse_hql("from: my-graph\nmatch:\n  type: hypernode")


def test_parse_invalid_yaml():
    with pytest.raises(HQLError):
        parse_hql(": invalid: yaml: {{")


def test_validate_missing_from():
    errors = validate_hql({"match": {"type": "hypernode"}})
    assert any("from" in e for e in errors)


def test_validate_invalid_match_type():
    errors = validate_hql({"from": "my-graph", "match": {"type": "invalid-type"}})
    assert any("hypernode" in e or "hyperedge" in e for e in errors)


def test_validate_valid_query():
    errors = validate_hql({
        "from": "my-graph",
        "match": {"type": "hyperedge", "relation": "has-member"},
        "return": ["members"],
    })
    assert errors == []


def test_validate_multi_graph():
    errors = validate_hql({
        "from": ["graph-1", "graph-2"],
        "match": {"type": "hypernode"},
    })
    assert errors == []
