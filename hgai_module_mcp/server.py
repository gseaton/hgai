"""HypergraphAI MCP Server.

Exposes HypergraphAI operations as MCP (Model Context Protocol) tools
for use by AI agents (Claude, etc.) via the Anthropic MCP SDK.

MCP tool groups:
  - hgai_hypernode_*  : Hypernode CRUD operations
  - hgai_hyperedge_*  : Hyperedge CRUD operations
  - hgai_hypergraph_* : Hypergraph management
  - hgai_query_*      : SHQL query execution
  - hgai_infer_*      : Semantic inferencing (transitive closure, inverse-of/symmetric/superproperty expansion)
  - hgai_mesh_*       : Mesh federation operations
  - hgai_media_*      : Media (binary file attachment) upload/download/delete
  - hgai_space_*      : Space (tenant namespace) management
  - hgai_admin_*      : Admin operations (requires admin role)

Authorization: every tool runs as the authenticated caller and is checked with
the same rules as the REST API — graph tools need the matching operation
(read/write/delete) on the graph, hgai_query_execute needs `query` on every
graph in `from:`, space tools need the matching space role, and mesh tools need
the admin role. Denials come back as {"error": ..., "type": "PermissionDenied"}.
"""

import json
import logging
from contextvars import ContextVar, Token
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from hgai.core import engine
from hgai.core.auth import (
    PermissionDeniedError,
    check_graph_permission,
    check_space_role,
    filter_accessible_graphs,
    require_admin_role,
)
from hgai.models.account import AccountInDB
from hgai_module_shql.engine import execute_shql
from hgai_module_shql.parser import parse_shql, validate_shql, SHQLError, SHQLPermissionError

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="hgai",
    instructions=(
        "HypergraphAI MCP Server. Provides tools for managing and querying semantic "
        "hypergraph knowledge stores. Use hgai_query_execute for flexible SHQL queries. "
        "Hyperedges are first-class entities and can connect n nodes. "
        "All operations require a valid hypergraph_id context. Every call runs with the "
        "permissions of the authenticated account; a call outside them returns a PermissionDenied error."
    ),
    streamable_http_path="/",
    stateless_http=True,
)


# ─── Caller identity and authorization ────────────────────────────────────────
# The ASGI middleware in module.py authenticates the bearer credential and
# publishes the resulting account here for the duration of the request; every
# tool authorizes against it with the same rules the REST API uses
# (hgai.core.auth). A tool that finds no caller refuses to run.

_current_account: ContextVar[Optional[AccountInDB]] = ContextVar("hgai_mcp_account", default=None)


def set_caller(account: AccountInDB) -> Token:
    return _current_account.set(account)


def reset_caller(token: Token) -> None:
    _current_account.reset(token)


def _caller() -> AccountInDB:
    account = _current_account.get()
    if account is None:
        raise PermissionDeniedError("No authenticated caller")
    return account


def _denied(e: PermissionDeniedError) -> str:
    return json.dumps({"error": str(e), "type": "PermissionDenied"})


async def _guard_graph(graph_id: str, operation: str) -> Optional[str]:
    """None when the caller may `operation` the graph, else the JSON error to return.

    MCP graph tools address unowned graphs (space-owned graphs are reached
    through hgai_query_execute with a 'space_id/graph_id' reference).
    """
    try:
        await check_graph_permission(_caller(), graph_id, operation, unowned=True)
    except PermissionDeniedError as e:
        return _denied(e)
    return None


def _guard_admin(what: str) -> Optional[str]:
    try:
        require_admin_role(_caller(), what)
    except PermissionDeniedError as e:
        return _denied(e)
    return None


async def _guard_space(space_id: str, minimum_role: str) -> Optional[str]:
    try:
        await check_space_role(_caller(), space_id, minimum_role)
    except PermissionDeniedError as e:
        return _denied(e)
    return None


# ─── Hypergraph Tools ─────────────────────────────────────────────────────────

@mcp.tool()
async def hgai_hypergraph_list(status: str = "active") -> str:
    """List all HypergraphAI hypergraphs.

    Args:
        status: Filter by status ('active', 'archived', 'draft', or '' for all)
    """
    graphs = []
    skip = 0
    while True:
        total, page = await engine.list_hypergraphs(status=status or None, skip=skip, limit=500)
        graphs.extend(page)
        skip += 500
        if skip >= total or not page:
            break
    graphs = await filter_accessible_graphs(_caller(), graphs)
    total, graphs = len(graphs), graphs[:200]
    return json.dumps({
        "total": total,
        "graphs": [{"id": g.id, "label": g.label, "type": g.type, "status": g.status,
                    "node_count": g.node_count, "edge_count": g.edge_count} for g in graphs]
    }, indent=2, default=str)


@mcp.tool()
async def hgai_hypergraph_get(graph_id: str) -> str:
    """Get a hypergraph by ID.

    Args:
        graph_id: The hypergraph identifier
    """
    if denied := await _guard_graph(graph_id, "read"):
        return denied
    graph = await engine.get_hypergraph(graph_id)
    if not graph:
        return json.dumps({"error": f"Hypergraph '{graph_id}' not found"})
    return json.dumps(graph.model_dump(), indent=2, default=str)


@mcp.tool()
async def hgai_hypergraph_stats(graph_id: str) -> str:
    """Get statistics for a hypergraph.

    Args:
        graph_id: The hypergraph identifier
    """
    if denied := await _guard_graph(graph_id, "read"):
        return denied
    stats = await engine.get_hypergraph_stats(graph_id)
    return json.dumps(stats, indent=2, default=str)


@mcp.tool()
async def hgai_hypergraph_create(
    id: str,
    label: str,
    description: str = "",
    graph_type: str = "instantiated",
    tags: str = "",
) -> str:
    """Create a new hypergraph.

    Args:
        id: Unique hypergraph identifier (slug format recommended)
        label: Human-readable display label
        description: Optional description
        graph_type: 'instantiated' (physical) or 'logical' (composed)
        tags: Comma-separated tags
    """
    from hgai.models.hypergraph import HypergraphCreate, GraphType
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    try:
        data = HypergraphCreate(
            id=id, label=label, description=description or None,
            type=GraphType(graph_type), tags=tag_list,
        )
        graph = await engine.create_hypergraph(data, created_by=_caller().username)
        return json.dumps({"success": True, "graph": graph.model_dump()}, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─── Hypernode Tools ──────────────────────────────────────────────────────────

@mcp.tool()
async def hgai_hypernode_list(
    graph_id: str,
    node_type: str = "",
    tags: str = "",
    skip: int = 0,
    limit: int = 50,
) -> str:
    """List hypernodes in a hypergraph.

    Args:
        graph_id: The hypergraph identifier
        node_type: Filter by entity type (e.g., 'Person', 'Organization')
        tags: Comma-separated tag filters
        skip: Pagination offset
        limit: Maximum results (max 500)
    """
    if denied := await _guard_graph(graph_id, "read"):
        return denied
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    total, nodes = await engine.list_hypernodes(
        graph_id, node_type=node_type or None, tags=tag_list, skip=skip, limit=limit
    )
    return json.dumps({
        "total": total,
        "nodes": [{"id": n.id, "label": n.label, "type": n.type,
                   "tags": n.tags, "status": n.status} for n in nodes]
    }, indent=2, default=str)


@mcp.tool()
async def hgai_hypernode_get(graph_id: str, node_id: str) -> str:
    """Get a hypernode by ID.

    Args:
        graph_id: The hypergraph identifier
        node_id: The hypernode identifier
    """
    if denied := await _guard_graph(graph_id, "read"):
        return denied
    node = await engine.get_hypernode(graph_id, node_id)
    if not node:
        return json.dumps({"error": f"Node '{node_id}' not found in graph '{graph_id}'"})
    return json.dumps(node.model_dump(), indent=2, default=str)


@mcp.tool()
async def hgai_hypernode_create(
    graph_id: str,
    id: str,
    label: str,
    node_type: str = "Entity",
    attributes_json: str = "{}",
    tags: str = "",
    description: str = "",
    media_json: str = "",
) -> str:
    """Create a new hypernode in a hypergraph.

    Args:
        graph_id: Target hypergraph identifier
        id: Unique node identifier within the hypergraph
        label: Human-readable display label
        node_type: Entity type (e.g., 'Person', 'Organization', 'Concept', 'RelationType')
        attributes_json: JSON string of document attributes (e.g., '{"city": "Paris"}')
        tags: Comma-separated tags
        description: Optional description
        media_json: Optional JSON array of media refs to attach, each with a
            media_id from hgai_media_upload, e.g.
            '[{"media_id": "abc123", "role": "profile-photo"}]'
    """
    if denied := await _guard_graph(graph_id, "write"):
        return denied
    from hgai.models.hypernode import HypernodeCreate
    from hgai.models.media import MediaRef
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    try:
        attributes = json.loads(attributes_json) if attributes_json else {}
        media = [MediaRef(**m) for m in json.loads(media_json)] if media_json else []
        data = HypernodeCreate(
            id=id, label=label, type=node_type, attributes=attributes,
            tags=tag_list, description=description or None, media=media,
        )
        node = await engine.create_hypernode(graph_id, data, created_by=_caller().username)
        return json.dumps({"success": True, "node": node.model_dump()}, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def hgai_hypernode_update(
    graph_id: str,
    node_id: str,
    label: str = None,
    attributes_json: str = None,
    tags: str = None,
    status: str = None,
    media_json: str = None,
) -> str:
    """Update a hypernode.

    Args:
        graph_id: The hypergraph identifier
        node_id: The hypernode identifier to update
        label: New label (optional)
        attributes_json: New attributes as JSON string (optional, replaces attributes)
        tags: New comma-separated tags (optional)
        status: New status: 'active', 'draft', 'archived' (optional)
        media_json: New media refs as a JSON array (optional, REPLACES the
            entire media list — include existing refs you want to keep, e.g.
            '[{"media_id": "abc123", "role": "profile-photo"}]'). Omit this
            argument entirely to leave existing media attachments untouched.
    """
    if denied := await _guard_graph(graph_id, "write"):
        return denied
    from hgai.models.hypernode import HypernodeUpdate
    from hgai.models.media import MediaRef
    update: dict = {}
    if label:
        update["label"] = label
    if attributes_json:
        update["attributes"] = json.loads(attributes_json)
    if tags is not None:
        update["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    if status:
        update["status"] = status
    if media_json is not None:
        update["media"] = [MediaRef(**m) for m in json.loads(media_json)]

    try:
        data = HypernodeUpdate(**update)
        node = await engine.update_hypernode(graph_id, node_id, data, updated_by=_caller().username)
        if not node:
            return json.dumps({"error": f"Node '{node_id}' not found"})
        return json.dumps({"success": True, "node": node.model_dump()}, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def hgai_hypernode_delete(graph_id: str, node_id: str) -> str:
    """Delete a hypernode.

    Args:
        graph_id: The hypergraph identifier
        node_id: The hypernode identifier to delete
    """
    if denied := await _guard_graph(graph_id, "delete"):
        return denied
    deleted = await engine.delete_hypernode(graph_id, node_id)
    return json.dumps({"success": deleted, "deleted_id": node_id})


# ─── Hyperedge Tools ──────────────────────────────────────────────────────────

@mcp.tool()
async def hgai_hyperedge_list(
    graph_id: str,
    relation: str = "",
    node_id: str = "",
    skip: int = 0,
    limit: int = 50,
) -> str:
    """List hyperedges in a hypergraph.

    Args:
        graph_id: The hypergraph identifier
        relation: Filter by relation type (e.g., 'has-member', 'sibling')
        node_id: Filter edges containing this node ID
        skip: Pagination offset
        limit: Maximum results
    """
    if denied := await _guard_graph(graph_id, "read"):
        return denied
    total, edges = await engine.list_hyperedges(
        graph_id,
        relation=relation or None,
        node_id=node_id or None,
        skip=skip,
        limit=limit,
    )
    return json.dumps({
        "total": total,
        "edges": [{"id": e.id, "relation": e.relation, "flavor": e.flavor,
                   "member_count": len(e.members), "tags": e.tags,
                   "members": [{"node_id": m.node_id, "seq": m.seq} for m in e.members]}
                  for e in edges]
    }, indent=2, default=str)


@mcp.tool()
async def hgai_hyperedge_get(graph_id: str, edge_id: str) -> str:
    """Get a hyperedge by ID.

    Args:
        graph_id: The hypergraph identifier
        edge_id: The hyperedge identifier (or hyperkey)
    """
    if denied := await _guard_graph(graph_id, "read"):
        return denied
    edge = await engine.get_hyperedge(graph_id, edge_id)
    if not edge:
        return json.dumps({"error": f"Edge '{edge_id}' not found in graph '{graph_id}'"})
    return json.dumps(edge.model_dump(), indent=2, default=str)


@mcp.tool()
async def hgai_hyperedge_create(
    graph_id: str,
    relation: str,
    members_json: str,
    edge_id: str = "",
    label: str = "",
    flavor: str = "hub",
    attributes_json: str = "{}",
    tags: str = "",
    media_json: str = "",
) -> str:
    """Create a new hyperedge connecting n hypernodes.

    Args:
        graph_id: Target hypergraph identifier
        relation: Semantic relation type (e.g., 'has-member', 'sibling', 'broader')
        members_json: JSON array of members: [{"node_id": "id", "seq": 0}, ...]
        edge_id: Optional human-readable edge ID (hyperkey auto-generated if omitted)
        label: Optional display label
        flavor: Relationship pattern: 'hub' (one member connects to the rest), 'symmetric' (all members equivalent)
        attributes_json: JSON document of edge attributes
        tags: Comma-separated tags
        media_json: Optional JSON array of media refs to attach, each with a
            media_id from hgai_media_upload, e.g.
            '[{"media_id": "abc123", "role": "diagram"}]'

    Example members_json:
        '[{"node_id": "three-stooges", "seq": 0},
          {"node_id": "moe-howard", "seq": 1}]'
    """
    if denied := await _guard_graph(graph_id, "write"):
        return denied
    from hgai.models.hyperedge import HyperedgeCreate, EdgeFlavor, EdgeMember
    from hgai.models.media import MediaRef
    try:
        members_data = json.loads(members_json)
        members = [EdgeMember(**m) for m in members_data]
        attributes = json.loads(attributes_json) if attributes_json else {}
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        media = [MediaRef(**m) for m in json.loads(media_json)] if media_json else []

        data = HyperedgeCreate(
            id=edge_id or None,
            relation=relation,
            label=label or None,
            flavor=EdgeFlavor(flavor),
            members=members,
            attributes=attributes,
            tags=tag_list,
            media=media,
        )
        edge = await engine.create_hyperedge(graph_id, data, created_by=_caller().username)
        return json.dumps({"success": True, "edge": edge.model_dump()}, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def hgai_hyperedge_delete(graph_id: str, edge_id: str) -> str:
    """Delete a hyperedge.

    Args:
        graph_id: The hypergraph identifier
        edge_id: The hyperedge identifier to delete
    """
    if denied := await _guard_graph(graph_id, "delete"):
        return denied
    deleted = await engine.delete_hyperedge(graph_id, edge_id)
    return json.dumps({"success": deleted, "deleted_id": edge_id})


# ─── Query Tools ──────────────────────────────────────────────────────────────

@mcp.tool()
async def hgai_query_execute(query_yaml: str, use_cache: bool = True) -> str:
    """Execute an SHQL query against a hypergraph.

    SHQL (Semantic Hypergraph Query Language) is a SPARQL-inspired,
    YAML-based pattern-matching language: `?var` bindings, implicit joins
    across shared variables, multi-hop traversal, OPTIONAL/UNION, and
    aggregation (`aggregate: {count, group_by}`). The query text must have
    a top-level 'shql:' key.

    Args:
        query_yaml: SHQL query in YAML format
        use_cache: Whether to use query result cache (default True)

    Example:
        shql:
          from: my-graph
          where:
            - node: "?person"
              node_type: Person
            - edge: "?e"
              relation: has-member
              members:
                - "?person"
          select:
            - "?person.label"
            - "?person.attributes"
          limit: 50

    Point-in-time example:
        shql:
          from: presidents
          at: "1963-11-22T00:00:00Z"
          where:
            - edge: "?e"
              relation: holds-office
          select:
            - "?e.members"

    Aggregation example:
        shql:
          from: my-graph
          where:
            - edge: "?e"
          select:
            - "?e.relation"
          aggregate:
            count: true
            group_by: e.relation

    Inferencing example (axiom expansion — see hgai_infer_* tools for more):
        shql:
          from: my-graph
          infer: true
          where:
            - edge: "?e"
              relation: has-member
          select:
            - "?e.relation"
            - "?e.members"
            - "?e._inferred"
            - "?e._source_edge"
            - "?e._axiom"
    """
    import yaml as _yaml
    try:
        data = _yaml.safe_load(query_yaml)
    except Exception as e:
        return json.dumps({"error": f"Failed to parse query YAML: {e}", "type": "ParseError"})

    if not isinstance(data, dict) or "shql" not in data:
        return json.dumps({"error": "Query must be a YAML object with a top-level 'shql' key", "type": "ParseError"})

    try:
        result = await execute_shql(query_yaml, use_cache=use_cache, account=_caller())
        return json.dumps(result.to_dict(), indent=2, default=str)
    except SHQLPermissionError as e:
        return json.dumps({"error": str(e), "type": "PermissionDenied"})
    except SHQLError as e:
        return json.dumps({"error": str(e), "type": "SHQLError"})
    except Exception as e:
        return json.dumps({"error": str(e), "type": "ExecutionError"})


@mcp.tool()
async def hgai_query_validate(query_yaml: str) -> str:
    """Validate an SHQL query without executing it.

    The query text must have a top-level 'shql:' key.

    Args:
        query_yaml: SHQL query in YAML format to validate
    """
    import yaml as _yaml
    try:
        data = _yaml.safe_load(query_yaml)
    except Exception as e:
        return json.dumps({"valid": False, "errors": [f"Failed to parse YAML: {e}"]})

    if not isinstance(data, dict) or "shql" not in data:
        return json.dumps({"valid": False, "errors": ["Query must be a YAML object with a top-level 'shql' key"]})

    try:
        shql = parse_shql(query_yaml)
        errors = validate_shql(shql)
        return json.dumps({"language": "shql", "valid": len(errors) == 0, "errors": errors, "parsed": shql}, indent=2)
    except SHQLError as e:
        return json.dumps({"language": "shql", "valid": False, "errors": [str(e)]})


# ─── Inference Tools ────────────────────────────────────────────────────────────
# Relation semantics (which relations are transitive, symmetric, each other's
# inverse, or broader/narrower) are never hardcoded — they're declared as
# ordinary hyperedges asserting control-vocabulary relations (owl:transitive,
# owl:symmetric, owl:inverse-of, skos:narrowerTransitive/broaderTransitive)
# between relation-hypernodes. See hgai/core/inference.py.

@mcp.tool()
async def hgai_infer_expand_edge(graph_id: str, edge_id: str) -> str:
    """Expand one hyperedge via inverse-of/symmetric/superproperty axioms.

    Synthesizes every fact implied by the given edge's relation's declared
    axioms (owl:inverse-of, owl:symmetric, skos:narrowerTransitive/
    broaderTransitive), applied as a fixed-point closure — a fact projected
    onto a broader relation is itself re-checked against further axioms, so
    a multi-hop relation hierarchy or a round-trip through an inverse
    relation is fully resolved, not just one axiom deep.

    Computed live, at read time — nothing here is persisted. Each result
    carries `_source_edge` (the original edge, or the intermediate
    synthesized edge that produced it) and `_axiom` (the specific axiom
    hyperedge that licensed that hop), so the derivation is traceable.

    Args:
        graph_id: The hypergraph identifier
        edge_id: The hyperedge to expand (id or hyperkey)
    """
    if denied := await _guard_graph(graph_id, "read"):
        return denied
    from hgai.core.inference import expand_edge_closure
    edge = await engine.get_hyperedge(graph_id, edge_id)
    if not edge:
        return json.dumps({"error": f"Edge '{edge_id}' not found in graph '{graph_id}'"})
    inferred = await expand_edge_closure([edge.model_dump()], [graph_id])
    return json.dumps({"source_edge": edge_id, "inferred": inferred}, indent=2, default=str)


@mcp.tool()
async def hgai_infer_check_transitive(
    graph_id: str,
    relation: str,
    start_id: str,
    end_id: str = "",
    mode: str = "bool",
) -> str:
    """Transitive-closure reachability over hyperedges of one relation.

    Self-verifies `relation` actually carries an `owl:transitive` axiom
    hyperedge before walking anything — calling this on a relation nobody
    declared transitive always safely reports "not reachable" rather than
    treating an incidental relation-name match as if it chains.

    Args:
        graph_id: The hypergraph identifier
        relation: The relation to walk (must have an owl:transitive axiom
            hyperedge asserted for it, e.g. relation="owl:transitive",
            members=[<relation-node>])
        start_id: The node (or relation, for axiom-graph walks) to start from
        end_id: Required for mode="bool"/"path"; ignored for mode="closure"
        mode: "bool" (is end_id reachable?), "closure" (every node
            transitively reachable from start_id), or "path" (the ordered
            chain of hyperedge ids connecting start_id to end_id, so each
            hop can be hydrated the same way as any other edge)
    """
    if denied := await _guard_graph(graph_id, "read"):
        return denied
    from hgai.core.inference import check_transitive
    try:
        result = await check_transitive(
            relation, [graph_id], start_id, end_id=end_id or None, mode=mode,
        )
    except ValueError as e:
        return json.dumps({"error": str(e)})
    return json.dumps({"relation": relation, "start_id": start_id, "end_id": end_id or None,
                        "mode": mode, "result": result}, indent=2, default=str)


# ─── Mesh Tools ───────────────────────────────────────────────────────────────

@mcp.tool()
async def hgai_mesh_list() -> str:
    """List all HypergraphAI meshes."""
    if denied := _guard_admin("mesh operations"):
        return denied
    from hgai.db.storage import get_storage
    from hgai_module_storage.filters import MeshFilters
    _, docs = await get_storage().meshes.list(MeshFilters(), skip=0, limit=200)
    result = []
    for doc in docs:
        result.append({
            "id": doc.get("id"),
            "label": doc.get("label"),
            "description": doc.get("description"),
            "server_count": len(doc.get("servers", [])),
            "status": doc.get("status"),
        })
    return json.dumps({"total": len(result), "meshes": result}, indent=2, default=str)


@mcp.tool()
async def hgai_mesh_get(mesh_id: str) -> str:
    """Get a mesh by ID, including its server list.

    Args:
        mesh_id: The mesh identifier
    """
    if denied := _guard_admin("mesh operations"):
        return denied
    from hgai.db.storage import get_storage
    doc = await get_storage().meshes.get(mesh_id)
    if not doc:
        return json.dumps({"error": f"Mesh '{mesh_id}' not found"})
    return json.dumps(doc, indent=2, default=str)


@mcp.tool()
async def hgai_mesh_ping(mesh_id: str) -> str:
    """Health-check all servers in a mesh.

    Args:
        mesh_id: The mesh identifier
    """
    if denied := _guard_admin("mesh operations"):
        return denied
    from hgai_module_mesh.engine import ping_mesh
    try:
        results = await ping_mesh(mesh_id)
        reachable = sum(1 for r in results if r.get("reachable"))
        return json.dumps({
            "mesh_id": mesh_id,
            "reachable": reachable,
            "total": len(results),
            "results": results,
        }, indent=2, default=str)
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def hgai_mesh_sync(mesh_id: str) -> str:
    """Refresh the graph list on each server in a mesh from the live remotes.

    Args:
        mesh_id: The mesh identifier
    """
    if denied := _guard_admin("mesh operations"):
        return denied
    from hgai_module_mesh.engine import sync_mesh_graphs
    try:
        result = await sync_mesh_graphs(mesh_id)
        return json.dumps(result, indent=2, default=str)
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def hgai_mesh_query(mesh_id: str, query_yaml: str, use_cache: bool = True) -> str:
    """Execute a federated SHQL query across all servers in a mesh.

    Query text must have a top-level 'shql:' key.
    Results from all servers are merged and tagged with '_mesh_server_id'.

    Args:
        mesh_id: The mesh identifier
        query_yaml: SHQL query in YAML format
        use_cache: Whether to use query result cache (default True)
    """
    if denied := _guard_admin("federated (mesh) queries"):
        return denied
    import yaml as _yaml
    from hgai_module_mesh.engine import federated_shql
    try:
        data = _yaml.safe_load(query_yaml)
    except Exception as e:
        return json.dumps({"error": f"Failed to parse query YAML: {e}"})

    if not isinstance(data, dict) or "shql" not in data:
        return json.dumps({"error": "Query must be a YAML object with a top-level 'shql' key"})

    try:
        result = await federated_shql(mesh_id, query_yaml, use_cache=use_cache, account=_caller())
        return json.dumps(result, indent=2, default=str)
    except SHQLPermissionError as e:
        return json.dumps({"error": str(e), "type": "PermissionDenied"})
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e), "type": "ExecutionError"})


# ─── Media Tools ──────────────────────────────────────────────────────────────

class _BytesReader:
    """Wraps an in-memory bytes payload with the async .read(n) interface that
    the media store's put() expects (matching FastAPI's UploadFile.read())."""

    def __init__(self, data: bytes):
        self._data = data
        self._pos = 0

    async def read(self, n: int) -> bytes:
        chunk = self._data[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk


@mcp.tool()
async def hgai_media_upload(
    content_base64: str,
    filename: str = "",
    content_type: str = "application/octet-stream",
) -> str:
    """Upload a binary file as base64-encoded content and get back a media_id.

    Attach the returned media_id to a hypernode or hyperedge via the
    media_json argument of hgai_hypernode_create/update or
    hgai_hyperedge_create. Content is decoded and checksummed server-side —
    identical content already uploaded elsewhere is deduplicated automatically.

    Args:
        content_base64: The file content, base64-encoded
        filename: Original filename (optional, shown to users in the UI)
        content_type: MIME type, e.g. 'image/png', 'application/pdf'
    """
    import base64
    import uuid
    from hgai.db.storage import get_storage

    try:
        data = base64.b64decode(content_base64)
    except Exception as e:
        return json.dumps({"error": f"Invalid base64 content: {e}"})

    try:
        media_id = uuid.uuid4().hex
        media = await get_storage().media.put(
            media_id, _BytesReader(data), content_type=content_type,
            filename=filename or None, uploaded_by=_caller().username,
        )
        return json.dumps({"success": True, "media": media.model_dump()}, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def hgai_media_download(media_id: str) -> str:
    """Download a media attachment's content as base64, with its metadata.

    Accepts both local media_ids and mesh-qualified ones ("<server_id>/<id>",
    as returned in the media field of a federated query result) — mesh
    resolution is proxied the same way the REST /media endpoint does it.

    Args:
        media_id: The media identifier (local or mesh-qualified)
    """
    import base64
    from hgai.core.media import parse_media_id
    from hgai.db.storage import get_storage

    server_id, local_id = parse_media_id(media_id)

    if server_id is None:
        result = await get_storage().media.get_stream(local_id)
        if not result:
            return json.dumps({"error": f"Media '{media_id}' not found"})
        metadata, chunks = result
        body = b"".join([chunk async for chunk in chunks])
        return json.dumps({
            "media_id": metadata.id,
            "content_type": metadata.content_type,
            "filename": metadata.filename,
            "size_bytes": metadata.size_bytes,
            "content_base64": base64.b64encode(body).decode("ascii"),
        }, indent=2, default=str)

    try:
        from hgai_module_mesh.engine import find_server_by_id, get_http_client, _headers
    except ImportError:
        return json.dumps({"error": "Mesh module is not available on this server"})

    server = await find_server_by_id(server_id)
    if not server:
        return json.dumps({"error": f"Mesh server '{server_id}' is not registered in any mesh on this server"})

    try:
        resp = await get_http_client().get(
            f"{server.url.rstrip('/')}/api/v1/media/{local_id}", headers=_headers(server)
        )
        resp.raise_for_status()
    except Exception as e:
        return json.dumps({"error": f"Failed to fetch media from mesh server '{server_id}': {e}"})

    return json.dumps({
        "media_id": media_id,
        "content_type": resp.headers.get("content-type", "application/octet-stream"),
        "size_bytes": len(resp.content),
        "content_base64": base64.b64encode(resp.content).decode("ascii"),
    }, indent=2, default=str)


@mcp.tool()
async def hgai_media_delete(media_id: str) -> str:
    """Delete a media attachment. Fails if it's still referenced by any
    hypernode/hyperedge (detach it from every entity first) or if it's owned
    by another mesh server.

    Args:
        media_id: The local media identifier to delete
    """
    from hgai.core.media import delete_media_checked
    deleted, _reason, message = await delete_media_checked(media_id)
    if not deleted:
        return json.dumps({"error": message})
    return json.dumps({"success": True, "deleted_id": media_id})


# ─── Space Tools ──────────────────────────────────────────────────────────────

@mcp.tool()
async def hgai_space_list() -> str:
    """List all HypergraphAI spaces (tenant namespaces)."""
    from hgai.core.space_engine import list_spaces
    caller = _caller()
    total, spaces = await list_spaces(username=None if "admin" in caller.roles else caller.username, limit=200)
    return json.dumps({
        "total": total,
        "spaces": [
            {
                "id": s.id,
                "label": s.label,
                "description": s.description,
                "member_count": len(s.members),
                "status": s.status,
            }
            for s in spaces
        ],
    }, indent=2, default=str)


@mcp.tool()
async def hgai_space_get(space_id: str) -> str:
    """Get a space by ID, including its members.

    Args:
        space_id: The space identifier
    """
    if denied := await _guard_space(space_id, "viewer"):
        return denied
    from hgai.core.space_engine import get_space
    space = await get_space(space_id)
    if not space:
        return json.dumps({"error": f"Space '{space_id}' not found"})
    return json.dumps(space.model_dump(), indent=2, default=str)


@mcp.tool()
async def hgai_space_create(
    id: str,
    label: str,
    description: str = "",
) -> str:
    """Create a new space (tenant namespace) for organizing hypergraphs.

    Args:
        id: Unique space identifier (no dots allowed)
        label: Human-readable display label
        description: Optional description
    """
    from hgai.core.space_engine import create_space, get_space
    from hgai.models.space import SpaceCreate
    try:
        existing = await get_space(id)
        if existing:
            return json.dumps({"error": f"Space '{id}' already exists"})
        data = SpaceCreate(id=id, label=label, description=description or None)
        space = await create_space(data, created_by=_caller().username)
        return json.dumps({"success": True, "space": space.model_dump()}, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def hgai_space_add_member(space_id: str, username: str, role: str = "member") -> str:
    """Add or update a member in a space.

    Args:
        space_id: The space identifier
        username: Account username to add
        role: Space role — 'owner', 'admin', 'member', or 'viewer' (default: 'member')
    """
    if denied := await _guard_space(space_id, "admin"):
        return denied
    from hgai.core.space_engine import add_member
    try:
        space = await add_member(space_id, username, role)
        if not space:
            return json.dumps({"error": f"Space '{space_id}' not found"})
        return json.dumps({"success": True, "space": space.model_dump()}, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def hgai_space_list_graphs(space_id: str, limit: int = 100) -> str:
    """List all hypergraphs belonging to a space.

    Args:
        space_id: The space identifier
        limit: Maximum number of graphs to return (default 100)
    """
    if denied := await _guard_space(space_id, "viewer"):
        return denied
    from hgai.core.space_engine import list_space_graphs
    try:
        total, graphs = await list_space_graphs(space_id, limit=limit)
        return json.dumps({
            "total": total,
            "graphs": [
                {"id": g.id, "label": g.label, "type": g.type,
                 "node_count": g.node_count, "edge_count": g.edge_count}
                for g in graphs
            ],
        }, indent=2, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


def create_mcp_server():
    """Create and return the MCP ASGI app for mounting in FastAPI."""
    return mcp.streamable_http_app()
