"""Semantic inferencing for HypergraphAI.

SKOS inferencing via hyperedge hub relations is a planned future implementation.
"""

from typing import Any, Dict, List, Set

from hgai.db.mongodb import col_hyperedges, col_hypernodes


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
