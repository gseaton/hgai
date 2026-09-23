"""Regression test: a hypernode/hyperedge id containing '/' must still route.

RDF import (hgai/core/rdf_import.py) mints hypernode ids and hyperedge relation
values as full, expanded IRIs (e.g. "http://example.com/Adam") — which, unlike
every id this codebase minted before, routinely contains '/'. The Web UI and
`ui/js/api.js` build REST paths by plain string interpolation with no
URL-encoding (`/graphs/${graphId}/nodes/${nodeId}`), exactly like the existing,
already-working `media_id` client calls — so, matching that existing
`{media_id:path}` precedent (hgai/api/routers/media.py), the node/edge id path
parameter must use Starlette's `:path` converter, not the default converter
(which only matches a single path segment and 404s on an embedded '/').

This is pure route-matching — no storage/DB access — mirroring this project's
own convention of verifying storage-backed behavior live rather than through
DB-backed unit tests (see tests/test_notes.py's docstring) while still keeping
a fast, dependency-free regression check on the routing layer itself.
"""

import pytest
from starlette.routing import Match

from hgai.api.routers import hyperedges, hypernodes, spaces

SLASHY_ID = "http://example.com/Adam"
SLASHY_RELATION = "http://xmlns.com/foaf/0.1/knows"


def _match(router, path, method):
    for route in router.routes:
        m, scope = route.matches({"type": "http", "method": method, "path": path})
        if m == Match.FULL:
            return route.endpoint.__name__, scope["path_params"]
    return None, None


@pytest.mark.parametrize("method,expected_endpoint", [
    ("GET", "get_node"), ("PUT", "update_node"), ("DELETE", "delete_node"),
])
def test_unowned_node_route_matches_a_slash_containing_id(method, expected_endpoint):
    name, params = _match(hypernodes.router, f"/graphs/g1/nodes/{SLASHY_ID}", method)
    assert name == expected_endpoint
    assert params == {"graph_id": "g1", "node_id": SLASHY_ID}


@pytest.mark.parametrize("method,expected_endpoint", [
    ("GET", "get_edge"), ("PUT", "update_edge"), ("DELETE", "delete_edge"),
])
def test_unowned_edge_route_matches_a_slash_containing_relation(method, expected_endpoint):
    name, params = _match(hyperedges.router, f"/graphs/g1/edges/{SLASHY_RELATION}", method)
    assert name == expected_endpoint
    assert params == {"graph_id": "g1", "edge_id": SLASHY_RELATION}


@pytest.mark.parametrize("method,expected_endpoint", [
    ("GET", "get_space_node"), ("PUT", "update_space_node"), ("DELETE", "delete_space_node"),
])
def test_space_scoped_node_route_matches_a_slash_containing_id(method, expected_endpoint):
    name, params = _match(spaces.router, f"/spaces/s1/graphs/g1/nodes/{SLASHY_ID}", method)
    assert name == expected_endpoint
    assert params == {"space_id": "s1", "graph_id": "g1", "node_id": SLASHY_ID}


@pytest.mark.parametrize("method,expected_endpoint", [
    ("GET", "get_space_edge"), ("PUT", "update_space_edge"), ("DELETE", "delete_space_edge"),
])
def test_space_scoped_edge_route_matches_a_slash_containing_relation(method, expected_endpoint):
    name, params = _match(spaces.router, f"/spaces/s1/graphs/g1/edges/{SLASHY_RELATION}", method)
    assert name == expected_endpoint
    assert params == {"space_id": "s1", "graph_id": "g1", "edge_id": SLASHY_RELATION}


def test_list_and_create_routes_are_unaffected_by_the_path_converter():
    # ":path" on the id route must not swallow the sibling list/create route
    # (no id segment at all) — those still need their own, separate match.
    for method, expected in [("GET", "list_nodes"), ("POST", "create_node")]:
        name, params = _match(hypernodes.router, "/graphs/g1/nodes", method)
        assert name == expected
        assert params == {"graph_id": "g1"}
    for method, expected in [("GET", "list_edges"), ("POST", "create_edge")]:
        name, params = _match(hyperedges.router, "/graphs/g1/edges", method)
        assert name == expected
        assert params == {"graph_id": "g1"}


def test_plain_sluglike_ids_still_route_exactly_as_before():
    # The overwhelmingly common case (ids with no '/') must be unaffected.
    name, params = _match(hypernodes.router, "/graphs/g1/nodes/person:adam", "GET")
    assert name == "get_node"
    assert params == {"graph_id": "g1", "node_id": "person:adam"}
