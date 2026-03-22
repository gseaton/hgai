"""SKOS-based semantic inferencing for HypergraphAI.

Supports SKOS relationships: broader, narrower, related, and transitivity.
Used for inferencing across hyperedges and hypernodes.
"""

from typing import Any, Dict, List, Set

from hgai.db.mongodb import col_hyperedges, col_hypernodes


async def get_skos_closure(
    node_id: str,
    graph_ids: List[str],
    relation: str = "broader",
    max_depth: int = 10,
) -> List[str]:
    """Compute transitive SKOS closure (e.g., all broader concepts).

    relation: 'broader', 'narrower', or 'related'
    Returns list of node IDs reachable via the SKOS relation chain.
    """
    visited: Set[str] = set()
    queue = [node_id]
    field_map = {
        "broader": "skos_broader",
        "narrower": "skos_narrower",
        "related": "skos_related",
    }
    field = field_map.get(relation, "skos_broader")

    depth = 0
    while queue and depth < max_depth:
        current_batch = queue[:]
        queue = []
        depth += 1

        cursor = col_hypernodes().find(
            {"id": {"$in": current_batch}, "hypergraph_id": {"$in": graph_ids}},
            {field: 1, "id": 1},
        )
        async for doc in cursor:
            for related_id in doc.get(field, []):
                if related_id not in visited:
                    visited.add(related_id)
                    queue.append(related_id)

    return list(visited)


async def apply_skos_inference(
    items: List[Dict[str, Any]],
    graph_ids: List[str],
) -> List[Dict[str, Any]]:
    """Apply SKOS inferencing to a result set.

    Adds inferred relationships to each item's _inferred field.
    """
    for item in items:
        node_id = item.get("id")
        if not node_id:
            continue

        inferred: Dict[str, List[str]] = {}

        broader = await get_skos_closure(node_id, graph_ids, "broader")
        if broader:
            inferred["broader_closure"] = broader

        narrower = await get_skos_closure(node_id, graph_ids, "narrower")
        if narrower:
            inferred["narrower_closure"] = narrower

        if inferred:
            item["_inferred"] = inferred

    return items


async def infer_inverse_edges(
    graph_id: str,
    edge_docs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Infer inverse hyperedge relationships.

    For hyperedges whose relation node has an 'inverse' attribute,
    generates inverse edge representations.
    """
    inverse_edges = []

    for edge in edge_docs:
        relation = edge.get("relation")
        if not relation:
            continue

        # Look for a relation type node with inverse defined
        rel_node = await col_hypernodes().find_one(
            {
                "id": relation,
                "hypergraph_id": graph_id,
                "type": "RelationType",
            },
            {"attributes.inverse": 1},
        )
        if not rel_node:
            continue

        inverse_rel = rel_node.get("attributes", {}).get("inverse")
        if not inverse_rel:
            continue

        # Build inverse edge
        members = edge.get("members", [])
        inverse_edge = {
            **edge,
            "id": f"{edge.get('id', '')}_inv",
            "relation": inverse_rel,
            "members": list(reversed(members)),
            "_inferred": True,
            "_source_edge": edge.get("id"),
        }
        inverse_edges.append(inverse_edge)

    return inverse_edges


async def check_transitive_relation(
    start_id: str,
    end_id: str,
    relation: str,
    graph_ids: List[str],
    max_depth: int = 10,
) -> bool:
    """Check if a transitive relation exists between two nodes via hyperedges."""
    visited: Set[str] = set([start_id])
    queue = [start_id]

    depth = 0
    while queue and depth < max_depth:
        current_batch = queue[:]
        queue = []
        depth += 1

        # Find all hyperedges where current nodes appear as members with given relation
        cursor = col_hyperedges().find(
            {
                "hypergraph_id": {"$in": graph_ids},
                "relation": relation,
                "members.node_id": {"$in": current_batch},
                "status": "active",
            },
            {"members": 1},
        )
        async for doc in cursor:
            for member in doc.get("members", []):
                mid = member.get("node_id")
                if mid == end_id:
                    return True
                if mid not in visited:
                    visited.add(mid)
                    queue.append(mid)

    return False
