"""MongoDB hypergraph store implementation."""

from typing import Any, Dict, List, Optional, Tuple

from hgai.models.hypergraph import HypergraphInDB
from hgai_module_storage.backend import HypergraphStore
from hgai_module_storage.filters import HypergraphFilters, HypergraphPatch

from ..connection import get_db


def _col():
    return get_db()["hypergraphs"]


def _graph_filter(graph_id: str, space_id: Optional[str]) -> Dict[str, Any]:
    """Build a filter that matches a graph by (id, space_id) exactly."""
    return {"id": graph_id, "space_id": space_id}


class MongoHypergraphStore(HypergraphStore):

    async def create(self, doc: Dict[str, Any]) -> HypergraphInDB:
        await _col().insert_one(doc)
        doc.pop("_id", None)
        return HypergraphInDB(**doc)

    async def get(self, graph_id: str, space_id: Optional[str] = None) -> Optional[HypergraphInDB]:
        raw = await _col().find_one(_graph_filter(graph_id, space_id))
        if not raw:
            return None
        raw.pop("_id", None)
        return HypergraphInDB(**raw)

    async def find_by_id_unscoped(self, graph_id: str) -> Optional[HypergraphInDB]:
        raw = await _col().find_one({"id": graph_id})
        if not raw:
            return None
        raw.pop("_id", None)
        return HypergraphInDB(**raw)

    async def list(
        self,
        filters: HypergraphFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[HypergraphInDB]]:
        query: Dict[str, Any] = {}
        if filters.status:
            query["status"] = filters.status
        if filters.tags:
            query["tags"] = {"$all": filters.tags}
        if filters.space_id is not None:
            query["space_id"] = filters.space_id

        total = await _col().count_documents(query)
        cursor = _col().find(query).skip(skip).limit(limit).sort("system_created", -1)
        docs = await cursor.to_list(length=limit)
        graphs = []
        for doc in docs:
            doc.pop("_id", None)
            graphs.append(HypergraphInDB(**doc))
        return total, graphs

    async def update(
        self,
        graph_id: str,
        patch: HypergraphPatch,
        space_id: Optional[str] = None,
    ) -> Optional[HypergraphInDB]:
        from hgai.models.common import now_utc
        update_fields: Dict[str, Any] = {}
        for attr in ("label", "description", "status", "tags", "attributes", "composition", "remote_refs"):
            val = getattr(patch, attr, None)
            if val is not None:
                update_fields[attr] = val
        update_fields["system_updated"] = now_utc()
        if patch.updated_by:
            update_fields["updated_by"] = patch.updated_by

        result = await _col().find_one_and_update(
            _graph_filter(graph_id, space_id),
            {"$set": update_fields, "$inc": {"version": 1}},
            return_document=True,
        )
        if not result:
            return None
        result.pop("_id", None)
        return HypergraphInDB(**result)

    async def delete(self, graph_id: str, space_id: Optional[str] = None) -> bool:
        result = await _col().delete_one(_graph_filter(graph_id, space_id))
        return result.deleted_count > 0

    async def stats(self, graph_id: str, space_id: Optional[str] = None) -> Dict[str, Any]:
        from hgai_module_storage_mongodb.connection import get_db as _get_db
        # Compute the hypergraph_id ref used on node/edge docs
        ref = f"{space_id}/{graph_id}" if space_id else graph_id
        db = _get_db()
        node_count = await db["hypernodes"].count_documents({"hypergraph_id": ref, "status": "active"})
        edge_count = await db["hyperedges"].count_documents({"hypergraph_id": ref, "status": "active"})
        rel_types = await db["hyperedges"].distinct("relation", {"hypergraph_id": ref})
        node_types = await db["hypernodes"].distinct("type", {"hypergraph_id": ref})
        return {
            "graph_id": graph_id,
            "node_count": node_count,
            "edge_count": edge_count,
            "relation_types": sorted(rel_types),
            "node_types": sorted(node_types),
        }

    async def increment_counts(
        self,
        graph_id: str,
        space_id: Optional[str] = None,
        node_delta: int = 0,
        edge_delta: int = 0,
    ) -> None:
        inc: Dict[str, int] = {}
        if node_delta:
            inc["node_count"] = node_delta
        if edge_delta:
            inc["edge_count"] = edge_delta
        if inc:
            await _col().update_one(_graph_filter(graph_id, space_id), {"$inc": inc})

    async def list_ids_for_space(self, space_id: str) -> List[str]:
        cursor = _col().find({"space_id": space_id}, {"id": 1})
        return [doc["id"] async for doc in cursor]

    async def reassign_space(
        self, graph_id: str, old_space_id: Optional[str], new_space_id: Optional[str]
    ) -> bool:
        from hgai.models.common import now_utc
        result = await _col().update_one(
            {"id": graph_id, "space_id": old_space_id},
            {"$set": {"space_id": new_space_id, "system_updated": now_utc()}},
        )
        return result.modified_count > 0

    async def list_by_space_ids(
        self, space_ids: List[str], status: Optional[str] = "active"
    ) -> List[str]:
        query: Dict[str, Any] = {"space_id": {"$in": space_ids}}
        if status:
            query["status"] = status
        cursor = _col().find(query, {"id": 1})
        return [doc["id"] async for doc in cursor]

    async def list_space_graphs(
        self, space_id: str, skip: int = 0, limit: int = 50
    ) -> Tuple[int, List[HypergraphInDB]]:
        query = {"space_id": space_id, "status": "active"}
        total = await _col().count_documents(query)
        cursor = _col().find(query).skip(skip).limit(limit).sort("system_created", -1)
        docs = await cursor.to_list(length=limit)
        graphs = []
        for doc in docs:
            doc.pop("_id", None)
            graphs.append(HypergraphInDB(**doc))
        return total, graphs

    async def find_composition_member(self, member_id: str) -> Optional[HypergraphInDB]:
        raw = await _col().find_one({"id": member_id})
        if not raw:
            return None
        raw.pop("_id", None)
        return HypergraphInDB(**raw)
