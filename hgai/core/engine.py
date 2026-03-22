"""HypergraphAI core hypergraph engine.

Provides CRUD operations for hypergraphs, hypernodes, and hyperedges,
including hyperkey generation, temporal support, and versioning.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from hgai.db.mongodb import (
    col_hyperedges,
    col_hypergraphs,
    col_hypernodes,
)
from hgai.models.common import Status, now_utc
from hgai.models.hyperedge import HyperedgeCreate, HyperedgeInDB, HyperedgeUpdate
from hgai.models.hypergraph import HypergraphCreate, HypergraphInDB, HypergraphUpdate
from hgai.models.hypernode import HypernodeCreate, HypernodeInDB, HypernodeUpdate


# ─── Hyperkey Generation ──────────────────────────────────────────────────────

def generate_hyperkey(relation: str, member_node_ids: List[str], hypergraph_id: str) -> str:
    """Generate a deterministic SHA-256 hyperkey for a hyperedge.

    The key is based on: normalized relation + sorted member node IDs + hypergraph ID.
    """
    normalized = {
        "relation": relation.lower().strip(),
        "graph": hypergraph_id,
        "members": sorted(member_node_ids),
    }
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


# ─── Hypergraph Engine ────────────────────────────────────────────────────────

async def create_hypergraph(data: HypergraphCreate, created_by: str) -> HypergraphInDB:
    now = now_utc()
    doc = data.model_dump()
    doc.update(
        system_created=now,
        system_updated=now,
        created_by=created_by,
        version=1,
        node_count=0,
        edge_count=0,
    )
    await col_hypergraphs().insert_one(doc)
    return HypergraphInDB(**doc)


async def get_hypergraph(graph_id: str) -> Optional[HypergraphInDB]:
    doc = await col_hypergraphs().find_one({"id": graph_id})
    if not doc:
        return None
    doc.pop("_id", None)
    return HypergraphInDB(**doc)


async def list_hypergraphs(
    status: Optional[str] = "active",
    tags: Optional[List[str]] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[int, List[HypergraphInDB]]:
    query: Dict[str, Any] = {}
    if status:
        query["status"] = status
    if tags:
        query["tags"] = {"$all": tags}

    total = await col_hypergraphs().count_documents(query)
    cursor = col_hypergraphs().find(query).skip(skip).limit(limit).sort("system_created", -1)
    docs = await cursor.to_list(length=limit)
    graphs = []
    for doc in docs:
        doc.pop("_id", None)
        graphs.append(HypergraphInDB(**doc))
    return total, graphs


async def update_hypergraph(
    graph_id: str, data: HypergraphUpdate, updated_by: str
) -> Optional[HypergraphInDB]:
    update_fields = {k: v for k, v in data.model_dump(exclude_none=True).items() if k != "version"}
    update_fields["system_updated"] = now_utc()
    update_fields["updated_by"] = updated_by

    result = await col_hypergraphs().find_one_and_update(
        {"id": graph_id},
        {"$set": update_fields, "$inc": {"version": 1}},
        return_document=True,
    )
    if not result:
        return None
    result.pop("_id", None)
    return HypergraphInDB(**result)


async def delete_hypergraph(graph_id: str) -> bool:
    result = await col_hypergraphs().delete_one({"id": graph_id})
    if result.deleted_count:
        await col_hypernodes().delete_many({"hypergraph_id": graph_id})
        await col_hyperedges().delete_many({"hypergraph_id": graph_id})
        return True
    return False


async def get_hypergraph_stats(graph_id: str) -> Dict[str, Any]:
    node_count = await col_hypernodes().count_documents({"hypergraph_id": graph_id, "status": "active"})
    edge_count = await col_hyperedges().count_documents({"hypergraph_id": graph_id, "status": "active"})

    rel_types = await col_hyperedges().distinct("relation", {"hypergraph_id": graph_id})
    node_types = await col_hypernodes().distinct("type", {"hypergraph_id": graph_id})

    return {
        "graph_id": graph_id,
        "node_count": node_count,
        "edge_count": edge_count,
        "relation_types": sorted(rel_types),
        "node_types": sorted(node_types),
    }


# ─── Hypernode Engine ─────────────────────────────────────────────────────────

async def create_hypernode(
    graph_id: str, data: HypernodeCreate, created_by: str
) -> HypernodeInDB:
    now = now_utc()
    doc = data.model_dump()
    doc.update(
        hypergraph_id=graph_id,
        system_created=now,
        system_updated=now,
        created_by=created_by,
        version=1,
    )
    await col_hypernodes().insert_one(doc)
    await col_hypergraphs().update_one(
        {"id": graph_id}, {"$inc": {"node_count": 1}}
    )
    doc.pop("_id", None)
    return HypernodeInDB(**doc)


async def get_hypernode(graph_id: str, node_id: str) -> Optional[HypernodeInDB]:
    doc = await col_hypernodes().find_one({"id": node_id, "hypergraph_id": graph_id})
    if not doc:
        return None
    doc.pop("_id", None)
    return HypernodeInDB(**doc)


async def list_hypernodes(
    graph_id: str,
    node_type: Optional[str] = None,
    status: Optional[str] = "active",
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    pit: Optional[datetime] = None,
) -> Tuple[int, List[HypernodeInDB]]:
    query: Dict[str, Any] = {"hypergraph_id": graph_id}
    if status:
        query["status"] = status
    if node_type:
        query["type"] = node_type
    if tags:
        query["tags"] = {"$all": tags}
    if search:
        query["$text"] = {"$search": search}
    if pit:
        query["$and"] = [
            {"$or": [{"valid_from": None}, {"valid_from": {"$lte": pit}}]},
            {"$or": [{"valid_to": None}, {"valid_to": {"$gte": pit}}]},
        ]

    total = await col_hypernodes().count_documents(query)
    cursor = col_hypernodes().find(query).skip(skip).limit(limit).sort("system_created", -1)
    docs = await cursor.to_list(length=limit)
    nodes = []
    for doc in docs:
        doc.pop("_id", None)
        nodes.append(HypernodeInDB(**doc))
    return total, nodes


async def update_hypernode(
    graph_id: str, node_id: str, data: HypernodeUpdate, updated_by: str
) -> Optional[HypernodeInDB]:
    update_fields = {k: v for k, v in data.model_dump(exclude_none=True).items() if k != "version"}
    update_fields["system_updated"] = now_utc()
    update_fields["updated_by"] = updated_by

    result = await col_hypernodes().find_one_and_update(
        {"id": node_id, "hypergraph_id": graph_id},
        {"$set": update_fields, "$inc": {"version": 1}},
        return_document=True,
    )
    if not result:
        return None
    result.pop("_id", None)
    return HypernodeInDB(**result)


async def delete_hypernode(graph_id: str, node_id: str) -> bool:
    result = await col_hypernodes().delete_one({"id": node_id, "hypergraph_id": graph_id})
    if result.deleted_count:
        await col_hypergraphs().update_one({"id": graph_id}, {"$inc": {"node_count": -1}})
        return True
    return False


# ─── Hyperedge Engine ─────────────────────────────────────────────────────────

async def create_hyperedge(
    graph_id: str, data: HyperedgeCreate, created_by: str
) -> HyperedgeInDB:
    now = now_utc()
    doc = data.model_dump()

    member_ids = [m["node_id"] for m in doc.get("members", [])]
    hyperkey = generate_hyperkey(doc["relation"], member_ids, graph_id)

    if not doc.get("id"):
        doc["id"] = hyperkey

    doc.update(
        hypergraph_id=graph_id,
        hyperkey=hyperkey,
        system_created=now,
        system_updated=now,
        created_by=created_by,
        version=1,
    )
    await col_hyperedges().insert_one(doc)
    await col_hypergraphs().update_one({"id": graph_id}, {"$inc": {"edge_count": 1}})
    doc.pop("_id", None)
    return HyperedgeInDB(**doc)


async def get_hyperedge(graph_id: str, edge_id: str) -> Optional[HyperedgeInDB]:
    doc = await col_hyperedges().find_one(
        {"$or": [{"id": edge_id}, {"hyperkey": edge_id}], "hypergraph_id": graph_id}
    )
    if not doc:
        return None
    doc.pop("_id", None)
    return HyperedgeInDB(**doc)


async def list_hyperedges(
    graph_id: str,
    relation: Optional[str] = None,
    flavor: Optional[str] = None,
    status: Optional[str] = "active",
    tags: Optional[List[str]] = None,
    node_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    pit: Optional[datetime] = None,
) -> Tuple[int, List[HyperedgeInDB]]:
    query: Dict[str, Any] = {"hypergraph_id": graph_id}
    if status:
        query["status"] = status
    if relation:
        query["relation"] = relation
    if flavor:
        query["flavor"] = flavor
    if tags:
        query["tags"] = {"$all": tags}
    if node_id:
        query["members.node_id"] = node_id
    if pit:
        query["$and"] = [
            {"$or": [{"valid_from": None}, {"valid_from": {"$lte": pit}}]},
            {"$or": [{"valid_to": None}, {"valid_to": {"$gte": pit}}]},
        ]

    total = await col_hyperedges().count_documents(query)
    cursor = col_hyperedges().find(query).skip(skip).limit(limit).sort("system_created", -1)
    docs = await cursor.to_list(length=limit)
    edges = []
    for doc in docs:
        doc.pop("_id", None)
        edges.append(HyperedgeInDB(**doc))
    return total, edges


async def update_hyperedge(
    graph_id: str, edge_id: str, data: HyperedgeUpdate, updated_by: str
) -> Optional[HyperedgeInDB]:
    update_fields = {k: v for k, v in data.model_dump(exclude_none=True).items() if k != "version"}
    update_fields["system_updated"] = now_utc()
    update_fields["updated_by"] = updated_by

    # Regenerate hyperkey if members or relation changed
    existing = await get_hyperedge(graph_id, edge_id)
    if existing:
        relation = update_fields.get("relation", existing.relation)
        members = update_fields.get("members", [m.model_dump() for m in existing.members])
        member_ids = [m["node_id"] if isinstance(m, dict) else m.node_id for m in members]
        update_fields["hyperkey"] = generate_hyperkey(relation, member_ids, graph_id)

    result = await col_hyperedges().find_one_and_update(
        {"$or": [{"id": edge_id}, {"hyperkey": edge_id}], "hypergraph_id": graph_id},
        {"$set": update_fields, "$inc": {"version": 1}},
        return_document=True,
    )
    if not result:
        return None
    result.pop("_id", None)
    return HyperedgeInDB(**result)


async def delete_hyperedge(graph_id: str, edge_id: str) -> bool:
    result = await col_hyperedges().delete_one(
        {"$or": [{"id": edge_id}, {"hyperkey": edge_id}], "hypergraph_id": graph_id}
    )
    if result.deleted_count:
        await col_hypergraphs().update_one({"id": graph_id}, {"$inc": {"edge_count": -1}})
        return True
    return False


# ─── Import / Export ──────────────────────────────────────────────────────────

async def export_hypergraph(graph_id: str) -> Dict[str, Any]:
    """Export all nodes and edges of a hypergraph."""
    graph = await get_hypergraph(graph_id)
    if not graph:
        return {}

    _, nodes = await list_hypernodes(graph_id, status=None, limit=10000)
    _, edges = await list_hyperedges(graph_id, status=None, limit=10000)

    return {
        "hgai_export": "1.0",
        "graph": graph.model_dump(),
        "nodes": [n.model_dump() for n in nodes],
        "edges": [e.model_dump() for e in edges],
    }


async def import_hypergraph_data(
    graph_id: str, data: Dict[str, Any], created_by: str
) -> Dict[str, int]:
    """Import nodes and edges into a hypergraph. Returns counts."""
    imported = {"nodes": 0, "edges": 0, "errors": 0}

    for node_data in data.get("nodes", []):
        try:
            node_data.pop("hypergraph_id", None)
            node_data.pop("system_created", None)
            node_data.pop("system_updated", None)
            node_create = HypernodeCreate(**node_data)
            await create_hypernode(graph_id, node_create, created_by)
            imported["nodes"] += 1
        except Exception:
            imported["errors"] += 1

    for edge_data in data.get("edges", []):
        try:
            edge_data.pop("hypergraph_id", None)
            edge_data.pop("system_created", None)
            edge_data.pop("system_updated", None)
            edge_data.pop("hyperkey", None)
            edge_create = HyperedgeCreate(**edge_data)
            await create_hyperedge(graph_id, edge_create, created_by)
            imported["edges"] += 1
        except Exception:
            imported["errors"] += 1

    return imported
