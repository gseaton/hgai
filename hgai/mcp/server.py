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
from hgai.core.query import execute_hql, HQLError, validate_hql, parse_hql

logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="hgai",
    instructions=(
        "HypergraphAI MCP Server. Provides tools for managing and querying semantic "
        "hypergraph knowledge stores. Use hgai_query_execute for flexible HQL queries. "
        "Hyperedges are first-class entities and can connect n nodes. "
        "All operations require a valid hypergraph_id context."
    ),
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
                   "members": [{"node_id": m.node_id, "role": m.role} for m in e.members]}
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
        members_json: JSON array of members: [{"node_id": "id", "role": "role", "seq": 0}, ...]
        edge_id: Optional human-readable edge ID (hyperkey auto-generated if omitted)
        label: Optional display label
        flavor: Relationship pattern: 'hub', 'symmetric', 'direct', 'transitive', 'inverse-transitive'
        attributes_json: JSON document of edge attributes
        tags: Comma-separated tags

    Example members_json:
        '[{"node_id": "three-stooges", "role": "group", "seq": 0},
          {"node_id": "moe-howard", "role": "member", "seq": 1}]'
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
async def hgai_query_execute(hql_yaml: str, use_cache: bool = True) -> str:
    """Execute an HQL (Hypergraph Query Language) query.

    HQL is a YAML-based declarative query language for querying hypergraphs.

    Args:
        hql_yaml: HQL query in YAML format
        use_cache: Whether to use query cache (default True)

    Example HQL:
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

    Example with point-in-time:
        hql:
          from: presidents
          at: "1963-11-22T00:00:00Z"
          match:
            type: hyperedge
            relation: holds-office
          return:
            - members

    Example multi-graph:
        hql:
          from:
            - graph-1
            - graph-2
          match:
            type: hypernode
            node_type: Person
          return:
            - id
            - label
            - attributes
    """
    try:
        result = await execute_hql(hql_yaml, use_cache=use_cache)
        return json.dumps(result.to_dict(), indent=2, default=str)
    except HQLError as e:
        return json.dumps({"error": str(e), "type": "HQLError"})
    except Exception as e:
        return json.dumps({"error": str(e), "type": "ExecutionError"})


@mcp.tool()
async def hgai_query_validate(hql_yaml: str) -> str:
    """Validate an HQL query without executing it.

    Args:
        hql_yaml: HQL query in YAML format to validate
    """
    try:
        hql = parse_hql(hql_yaml)
        errors = validate_hql(hql)
        return json.dumps({"valid": len(errors) == 0, "errors": errors, "parsed": hql}, indent=2)
    except HQLError as e:
        return json.dumps({"valid": False, "errors": [str(e)]})


def create_mcp_server():
    """Create and return the MCP ASGI app for mounting in FastAPI."""
    return mcp.streamable_http_app()
