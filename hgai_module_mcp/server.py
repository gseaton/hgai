"""HypergraphAI MCP Server.

Exposes HypergraphAI operations as MCP (Model Context Protocol) tools
for use by AI agents (Claude, etc.) via the Anthropic MCP SDK.

MCP tool groups:
  - hgai_hypernode_*  : Hypernode CRUD operations
  - hgai_hyperedge_*  : Hyperedge CRUD operations
  - hgai_hypergraph_* : Hypergraph management
  - hgai_query_*      : HQL query execution
  - hgai_admin_*      : Admin operations (requires admin role)
"""

import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from hgai.core import engine
from hgai_module_hql.engine import execute_hql, HQLError, validate_hql, parse_hql
from hgai_module_shql.engine import execute_shql
from hgai_module_shql.parser import parse_shql, validate_shql, SHQLError

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="hgai",
    instructions=(
        "HypergraphAI MCP Server. Provides tools for managing and querying semantic "
        "hypergraph knowledge stores. Use hgai_query_execute for flexible HQL queries. "
        "Hyperedges are first-class entities and can connect n nodes. "
        "All operations require a valid hypergraph_id context."
    ),
    streamable_http_path="/",
    stateless_http=True,
)


# ─── Hypergraph Tools ─────────────────────────────────────────────────────────

@mcp.tool()
async def hgai_hypergraph_list(status: str = "active") -> str:
    """List all HypergraphAI hypergraphs.

    Args:
        status: Filter by status ('active', 'archived', 'draft', or '' for all)
    """
    total, graphs = await engine.list_hypergraphs(status=status or None, limit=200)
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
        graph = await engine.create_hypergraph(data, created_by="mcp-agent")
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
    """
    from hgai.models.hypernode import HypernodeCreate
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    try:
        attributes = json.loads(attributes_json) if attributes_json else {}
        data = HypernodeCreate(
            id=id, label=label, type=node_type, attributes=attributes,
            tags=tag_list, description=description or None,
        )
        node = await engine.create_hypernode(graph_id, data, created_by="mcp-agent")
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
) -> str:
    """Update a hypernode.

    Args:
        graph_id: The hypergraph identifier
        node_id: The hypernode identifier to update
        label: New label (optional)
        attributes_json: New attributes as JSON string (optional, replaces attributes)
        tags: New comma-separated tags (optional)
        status: New status: 'active', 'draft', 'archived' (optional)
    """
    from hgai.models.hypernode import HypernodeUpdate
    update: dict = {}
    if label:
        update["label"] = label
    if attributes_json:
        update["attributes"] = json.loads(attributes_json)
    if tags is not None:
        update["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    if status:
        update["status"] = status

    try:
        data = HypernodeUpdate(**update)
        node = await engine.update_hypernode(graph_id, node_id, data, updated_by="mcp-agent")
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
) -> str:
    """Create a new hyperedge connecting n hypernodes.

    Args:
        graph_id: Target hypergraph identifier
        relation: Semantic relation type (e.g., 'has-member', 'sibling', 'broader')
        members_json: JSON array of members: [{"node_id": "id", "seq": 0}, ...]
        edge_id: Optional human-readable edge ID (hyperkey auto-generated if omitted)
        label: Optional display label
        flavor: Relationship pattern: 'hub', 'symmetric', 'direct', 'transitive', 'inverse-transitive'
        attributes_json: JSON document of edge attributes
        tags: Comma-separated tags

    Example members_json:
        '[{"node_id": "three-stooges", "seq": 0},
          {"node_id": "moe-howard", "seq": 1}]'
    """
    from hgai.models.hyperedge import HyperedgeCreate, EdgeFlavor, EdgeMember
    try:
        members_data = json.loads(members_json)
        members = [EdgeMember(**m) for m in members_data]
        attributes = json.loads(attributes_json) if attributes_json else {}
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

        data = HyperedgeCreate(
            id=edge_id or None,
            relation=relation,
            label=label or None,
            flavor=EdgeFlavor(flavor),
            members=members,
            attributes=attributes,
            tags=tag_list,
        )
        edge = await engine.create_hyperedge(graph_id, data, created_by="mcp-agent")
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
    deleted = await engine.delete_hyperedge(graph_id, edge_id)
    return json.dumps({"success": deleted, "deleted_id": edge_id})


# ─── Query Tools ──────────────────────────────────────────────────────────────

@mcp.tool()
async def hgai_query_execute(query_yaml: str, use_cache: bool = True) -> str:
    """Execute an HQL or SHQL query against a hypergraph.

    The query language is detected automatically from the top-level key:
    - Top-level 'hql:' key  → HQL  (Hypergraph Query Language, YAML-based declarative)
    - Top-level 'shql:' key → SHQL (Semantic Hypergraph Query Language, SPARQL-inspired)

    Args:
        query_yaml: HQL or SHQL query in YAML format
        use_cache: Whether to use query result cache (default True)

    HQL example:
        hql:
          from: my-graph
          match:
            type: hyperedge
            relation: has-member
          where:
            tags:
              - original
          return:
            - members
            - attributes
          as: result

    HQL point-in-time example:
        hql:
          from: presidents
          at: "1963-11-22T00:00:00Z"
          match:
            type: hyperedge
            relation: holds-office
          return:
            - members

    SHQL example:
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
    """
    import yaml as _yaml
    try:
        data = _yaml.safe_load(query_yaml)
    except Exception as e:
        return json.dumps({"error": f"Failed to parse query YAML: {e}", "type": "ParseError"})

    if not isinstance(data, dict):
        return json.dumps({"error": "Query must be a YAML object with a top-level 'hql' or 'shql' key", "type": "ParseError"})

    if "hql" in data:
        try:
            result = await execute_hql(query_yaml, use_cache=use_cache)
            return json.dumps(result.to_dict(), indent=2, default=str)
        except HQLError as e:
            return json.dumps({"error": str(e), "type": "HQLError"})
        except Exception as e:
            return json.dumps({"error": str(e), "type": "ExecutionError"})

    if "shql" in data:
        try:
            result = await execute_shql(query_yaml, use_cache=use_cache)
            return json.dumps(result.to_dict(), indent=2, default=str)
        except SHQLError as e:
            return json.dumps({"error": str(e), "type": "SHQLError"})
        except Exception as e:
            return json.dumps({"error": str(e), "type": "ExecutionError"})

    return json.dumps({"error": "Query must have a top-level 'hql' or 'shql' key", "type": "ParseError"})


@mcp.tool()
async def hgai_query_validate(query_yaml: str) -> str:
    """Validate an HQL or SHQL query without executing it.

    The query language is detected automatically from the top-level key:
    - Top-level 'hql:' key  → HQL
    - Top-level 'shql:' key → SHQL

    Args:
        query_yaml: HQL or SHQL query in YAML format to validate
    """
    import yaml as _yaml
    try:
        data = _yaml.safe_load(query_yaml)
    except Exception as e:
        return json.dumps({"valid": False, "errors": [f"Failed to parse YAML: {e}"]})

    if not isinstance(data, dict):
        return json.dumps({"valid": False, "errors": ["Query must be a YAML object with a top-level 'hql' or 'shql' key"]})

    if "hql" in data:
        try:
            hql = parse_hql(query_yaml)
            errors = validate_hql(hql)
            return json.dumps({"language": "hql", "valid": len(errors) == 0, "errors": errors, "parsed": hql}, indent=2)
        except HQLError as e:
            return json.dumps({"language": "hql", "valid": False, "errors": [str(e)]})

    if "shql" in data:
        try:
            shql = parse_shql(query_yaml)
            errors = validate_shql(shql)
            return json.dumps({"language": "shql", "valid": len(errors) == 0, "errors": errors, "parsed": shql}, indent=2)
        except SHQLError as e:
            return json.dumps({"language": "shql", "valid": False, "errors": [str(e)]})

    return json.dumps({"valid": False, "errors": ["Query must have a top-level 'hql' or 'shql' key"]})


# ─── Mesh Tools ───────────────────────────────────────────────────────────────

@mcp.tool()
async def hgai_mesh_list() -> str:
    """List all HypergraphAI meshes."""
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
    from hgai_module_mesh.engine import sync_mesh_graphs
    try:
        result = await sync_mesh_graphs(mesh_id)
        return json.dumps(result, indent=2, default=str)
    except ValueError as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def hgai_mesh_query(mesh_id: str, query_yaml: str, use_cache: bool = True) -> str:
    """Execute a federated HQL or SHQL query across all servers in a mesh.

    The query language is detected from the top-level key ('hql:' or 'shql:').
    Results from all servers are merged and tagged with '_mesh_server_id'.

    Args:
        mesh_id: The mesh identifier
        query_yaml: HQL or SHQL query in YAML format
        use_cache: Whether to use query result cache (default True)
    """
    import yaml as _yaml
    from hgai_module_mesh.engine import federated_hql, federated_shql
    try:
        data = _yaml.safe_load(query_yaml)
    except Exception as e:
        return json.dumps({"error": f"Failed to parse query YAML: {e}"})

    if not isinstance(data, dict):
        return json.dumps({"error": "Query must be a YAML object with a top-level 'hql' or 'shql' key"})

    try:
        if "hql" in data:
            result = await federated_hql(mesh_id, query_yaml, use_cache=use_cache)
        elif "shql" in data:
            result = await federated_shql(mesh_id, query_yaml, use_cache=use_cache)
        else:
            return json.dumps({"error": "Query must have a top-level 'hql' or 'shql' key"})
        return json.dumps(result, indent=2, default=str)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": str(e), "type": "ExecutionError"})


# ─── Space Tools ──────────────────────────────────────────────────────────────

@mcp.tool()
async def hgai_space_list() -> str:
    """List all HypergraphAI spaces (tenant namespaces)."""
    from hgai.core.space_engine import list_spaces
    total, spaces = await list_spaces(limit=200)
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
        space = await create_space(data, created_by="mcp-agent")
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
