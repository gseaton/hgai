"""HypergraphAI core hypergraph engine.

Provides CRUD operations for hypergraphs, hypernodes, and hyperedges,
including hyperkey generation, temporal support, and versioning.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from hgai.db.storage import get_storage
from hgai.core.cache import invalidate_cache
from hgai.models.common import Status, now_utc
from hgai.models.hyperedge import HyperedgeCreate, HyperedgeInDB, HyperedgeUpdate
from hgai.models.hypergraph import HypergraphCreate, HypergraphInDB, HypergraphUpdate
from hgai.models.hypernode import HypernodeCreate, HypernodeInDB, HypernodeUpdate
from hgai_module_storage.filters import (
    HyperedgeFilters,
    HyperedgePatch,
    HypergraphFilters,
    HypergraphPatch,
    HypernodeFilters,
    HypernodePatch,
)


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

def _hypergraph_ref(graph_id: str, space_id: Optional[str]) -> str:
    """Return the value stored as hypergraph_id on node/edge documents.

    Space-owned graph:  "space_id/graph_id"
    Unowned graph:      "graph_id"

    This composite key ensures nodes/edges from different spaces that happen
    to share the same graph_id are never confused with each other.
    """
    return f"{space_id}/{graph_id}" if space_id else graph_id


def _graph_filter(graph_id: str, space_id: Optional[str]) -> Dict[str, Any]:
    """Build a filter dict for a graph by (id, space_id).

    Kept for backwards compatibility in places that still pass this to the store.
    """
    return {"id": graph_id, "space_id": space_id}


async def find_hypergraph_by_id(graph_id: str) -> Optional[HypergraphInDB]:
    """Look up a graph by id alone, ignoring space scope.

    Used only by auth and HQL/SHQL resolution paths that do not yet have
    space context. Prefer get_hypergraph(..., space_id=...) when the space
    is known to avoid ambiguity when the same graph_id exists in multiple spaces.
    """
    return await get_storage().hypergraphs.find_by_id_unscoped(graph_id)


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
    return await get_storage().hypergraphs.create(doc)


async def get_hypergraph(graph_id: str, space_id: Optional[str] = None) -> Optional[HypergraphInDB]:
    return await get_storage().hypergraphs.get(graph_id, space_id)


async def list_hypergraphs(
    status: Optional[str] = "active",
    tags: Optional[List[str]] = None,
    space_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[int, List[HypergraphInDB]]:
    filters = HypergraphFilters(status=status, tags=tags, space_id=space_id)
    return await get_storage().hypergraphs.list(filters, skip=skip, limit=limit)


async def update_hypergraph(
    graph_id: str, data: HypergraphUpdate, updated_by: str, space_id: Optional[str] = None
) -> Optional[HypergraphInDB]:
    dumped = {k: v for k, v in data.model_dump(exclude_none=True).items() if k != "version"}
    patch = HypergraphPatch(
        label=dumped.get("label"),
        description=dumped.get("description"),
        status=dumped.get("status"),
        tags=dumped.get("tags"),
        attributes=dumped.get("attributes"),
        composition=dumped.get("composition"),
        remote_refs=dumped.get("remote_refs"),
        updated_by=updated_by,
    )
    result = await get_storage().hypergraphs.update(graph_id, patch, space_id=space_id)
    if result:
        await invalidate_cache(graph_id)
    return result


async def delete_hypergraph(graph_id: str, space_id: Optional[str] = None) -> bool:
    deleted = await get_storage().hypergraphs.delete(graph_id, space_id)
    if deleted:
        ref = _hypergraph_ref(graph_id, space_id)
        await get_storage().hypernodes.delete_by_graph(ref)
        await get_storage().hyperedges.delete_by_graph(ref)
        await invalidate_cache(graph_id)
        return True
    return False


async def get_hypergraph_stats(graph_id: str, space_id: Optional[str] = None) -> Dict[str, Any]:
    return await get_storage().hypergraphs.stats(graph_id, space_id)


# ─── Hypernode Engine ─────────────────────────────────────────────────────────

async def create_hypernode(
    graph_id: str, data: HypernodeCreate, created_by: str, space_id: Optional[str] = None
) -> HypernodeInDB:
    now = now_utc()
    doc = data.model_dump()
    doc.update(
        hypergraph_id=_hypergraph_ref(graph_id, space_id),
        system_created=now,
        system_updated=now,
        created_by=created_by,
        version=1,
    )
    node = await get_storage().hypernodes.create(doc)
    await get_storage().hypergraphs.increment_counts(graph_id, space_id, node_delta=1)
    await invalidate_cache(graph_id)
    return node


async def get_hypernode(
    graph_id: str, node_id: str, space_id: Optional[str] = None
) -> Optional[HypernodeInDB]:
    return await get_storage().hypernodes.get(
        hypergraph_id=_hypergraph_ref(graph_id, space_id),
        node_id=node_id,
    )


async def list_hypernodes(
    graph_id: str,
    node_type: Optional[str] = None,
    status: Optional[str] = "active",
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    pit: Optional[datetime] = None,
    space_id: Optional[str] = None,
) -> Tuple[int, List[HypernodeInDB]]:
    filters = HypernodeFilters(
        hypergraph_id=_hypergraph_ref(graph_id, space_id),
        node_type=node_type,
        status=status,
        tags=tags,
        search=search,
        pit=pit,
    )
    return await get_storage().hypernodes.list(filters, skip=skip, limit=limit)


async def update_hypernode(
    graph_id: str, node_id: str, data: HypernodeUpdate, updated_by: str,
    space_id: Optional[str] = None,
) -> Optional[HypernodeInDB]:
    dumped = {k: v for k, v in data.model_dump(exclude_none=True).items() if k != "version"}
    patch = HypernodePatch(
        label=dumped.get("label"),
        description=dumped.get("description"),
        type=dumped.get("type"),
        status=dumped.get("status"),
        tags=dumped.get("tags"),
        attributes=dumped.get("attributes"),
        valid_from=dumped.get("valid_from"),
        valid_to=dumped.get("valid_to"),
        updated_by=updated_by,
    )
    result = await get_storage().hypernodes.update(
        hypergraph_id=_hypergraph_ref(graph_id, space_id),
        node_id=node_id,
        patch=patch,
    )
    if result:
        await invalidate_cache(graph_id)
    return result


async def delete_hypernode(graph_id: str, node_id: str, space_id: Optional[str] = None) -> bool:
    deleted = await get_storage().hypernodes.delete(
        hypergraph_id=_hypergraph_ref(graph_id, space_id),
        node_id=node_id,
    )
    if deleted:
        await get_storage().hypergraphs.increment_counts(graph_id, space_id, node_delta=-1)
        await invalidate_cache(graph_id)
        return True
    return False


# ─── Hyperedge Engine ─────────────────────────────────────────────────────────

async def create_hyperedge(
    graph_id: str, data: HyperedgeCreate, created_by: str, space_id: Optional[str] = None
) -> HyperedgeInDB:
    now = now_utc()
    doc = data.model_dump()

    member_ids = [m["node_id"] for m in doc.get("members", [])]
    ref = _hypergraph_ref(graph_id, space_id)
    hyperkey = generate_hyperkey(doc["relation"], member_ids, ref)

    if not doc.get("id"):
        doc["id"] = hyperkey

    doc.update(
        hypergraph_id=ref,
        hyperkey=hyperkey,
        system_created=now,
        system_updated=now,
        created_by=created_by,
        version=1,
    )
    edge = await get_storage().hyperedges.create(doc)
    await get_storage().hypergraphs.increment_counts(graph_id, space_id, edge_delta=1)
    await invalidate_cache(graph_id)
    return edge


async def get_hyperedge(
    graph_id: str, edge_id: str, space_id: Optional[str] = None
) -> Optional[HyperedgeInDB]:
    return await get_storage().hyperedges.get_by_id_or_hyperkey(
        hypergraph_id=_hypergraph_ref(graph_id, space_id),
        edge_id=edge_id,
    )


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
    space_id: Optional[str] = None,
) -> Tuple[int, List[HyperedgeInDB]]:
    filters = HyperedgeFilters(
        hypergraph_id=_hypergraph_ref(graph_id, space_id),
        relation=relation,
        flavor=flavor,
        status=status,
        tags=tags,
        member_node_id=node_id,
        pit=pit,
    )
    return await get_storage().hyperedges.list(filters, skip=skip, limit=limit)


async def update_hyperedge(
    graph_id: str, edge_id: str, data: HyperedgeUpdate, updated_by: str,
    space_id: Optional[str] = None,
) -> Optional[HyperedgeInDB]:
    ref = _hypergraph_ref(graph_id, space_id)
    dumped = {k: v for k, v in data.model_dump(exclude_none=True).items() if k != "version"}

    # Regenerate hyperkey if members or relation changed
    existing = await get_hyperedge(graph_id, edge_id, space_id=space_id)
    if existing:
        relation = dumped.get("relation", existing.relation)
        members = dumped.get("members", [m.model_dump() for m in existing.members])
        member_ids = [m["node_id"] if isinstance(m, dict) else m.node_id for m in members]
        dumped["hyperkey"] = generate_hyperkey(relation, member_ids, ref)

    patch = HyperedgePatch(
        label=dumped.get("label"),
        description=dumped.get("description"),
        relation=dumped.get("relation"),
        flavor=dumped.get("flavor"),
        status=dumped.get("status"),
        tags=dumped.get("tags"),
        attributes=dumped.get("attributes"),
        members=dumped.get("members"),
        valid_from=dumped.get("valid_from"),
        valid_to=dumped.get("valid_to"),
        skos_broader=dumped.get("skos_broader"),
        skos_narrower=dumped.get("skos_narrower"),
        skos_related=dumped.get("skos_related"),
        updated_by=updated_by,
    )
    # Pass the regenerated hyperkey as an extra field to the store.
    extra_fields = {"hyperkey": dumped["hyperkey"]} if "hyperkey" in dumped else None

    from hgai_module_storage_mongodb.stores.hyperedges import MongoHyperedgeStore
    mongo_store = get_storage().hyperedges
    if isinstance(mongo_store, MongoHyperedgeStore):
        result = await mongo_store.update(
            hypergraph_id=ref,
            edge_id=edge_id,
            patch=patch,
            extra_fields=extra_fields,
        )
    else:
        result = await get_storage().hyperedges.update(
            hypergraph_id=ref,
            edge_id=edge_id,
            patch=patch,
        )

    if result:
        await invalidate_cache(graph_id)
    return result


async def delete_hyperedge(graph_id: str, edge_id: str, space_id: Optional[str] = None) -> bool:
    deleted = await get_storage().hyperedges.delete(
        hypergraph_id=_hypergraph_ref(graph_id, space_id),
        edge_id=edge_id,
    )
    if deleted:
        await get_storage().hypergraphs.increment_counts(graph_id, space_id, edge_delta=-1)
        await invalidate_cache(graph_id)
        return True
    return False


# ─── Import / Export ──────────────────────────────────────────────────────────

async def export_hypergraph(graph_id: str, space_id: Optional[str] = None) -> Dict[str, Any]:
    """Export all nodes and edges of a hypergraph."""
    graph = await get_hypergraph(graph_id, space_id=space_id)
    if not graph:
        return {}

    _, nodes = await list_hypernodes(graph_id, status=None, limit=10000, space_id=space_id)
    _, edges = await list_hyperedges(graph_id, status=None, limit=10000, space_id=space_id)

    return {
        "hgai_export": "1.0",
        "graph": graph.model_dump(),
        "nodes": [n.model_dump() for n in nodes],
        "edges": [e.model_dump() for e in edges],
    }


async def import_hypergraph_data(
    graph_id: str, data: Dict[str, Any], created_by: str, space_id: Optional[str] = None
) -> Dict[str, int]:
    """Import nodes and edges into a hypergraph. Returns counts."""
    imported = {"nodes": 0, "edges": 0, "errors": 0}

    for node_data in data.get("nodes", []):
        try:
            node_data.pop("hypergraph_id", None)
            node_data.pop("system_created", None)
            node_data.pop("system_updated", None)
            node_create = HypernodeCreate(**node_data)
            await create_hypernode(graph_id, node_create, created_by, space_id=space_id)
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
            await create_hyperedge(graph_id, edge_create, created_by, space_id=space_id)
            imported["edges"] += 1
        except Exception:
            imported["errors"] += 1

    return imported
