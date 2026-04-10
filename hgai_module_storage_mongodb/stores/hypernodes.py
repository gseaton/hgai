"""MongoDB hypernode store implementation."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from hgai.models.hypernode import HypernodeInDB
from hgai_module_storage.backend import HypernodeStore
from hgai_module_storage.filters import HypernodeFilters, HypernodePatch, HypernodeSearchFilters

from ..connection import get_db


def _col():
    return get_db()["hypernodes"]


def _pit_clause(pit: datetime) -> List[Dict[str, Any]]:
    return [
        {"$or": [{"valid_from": None}, {"valid_from": {"$lte": pit}}]},
        {"$or": [{"valid_to": None}, {"valid_to": {"$gte": pit}}]},
    ]


class MongoHypernodeStore(HypernodeStore):

    async def create(self, doc: Dict[str, Any]) -> HypernodeInDB:
        await _col().insert_one(doc)
        doc.pop("_id", None)
        return HypernodeInDB(**doc)

    async def get(self, hypergraph_id: str, node_id: str) -> Optional[HypernodeInDB]:
        raw = await _col().find_one({"id": node_id, "hypergraph_id": hypergraph_id})
        if not raw:
            return None
        raw.pop("_id", None)
        return HypernodeInDB(**raw)

    async def list(
        self,
        filters: HypernodeFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[HypernodeInDB]]:
        query: Dict[str, Any] = {"hypergraph_id": filters.hypergraph_id}
        if filters.status:
            query["status"] = filters.status
        if filters.node_type:
            query["type"] = filters.node_type
        if filters.tags:
            query["tags"] = {"$all": filters.tags}
        if filters.search:
            query["label"] = {"$regex": filters.search, "$options": "i"}
        if filters.pit:
            query["$and"] = _pit_clause(filters.pit)

        total = await _col().count_documents(query)
        cursor = _col().find(query).skip(skip).limit(limit).sort("system_created", -1)
        docs = await cursor.to_list(length=limit)
        nodes = []
        for doc in docs:
            doc.pop("_id", None)
            nodes.append(HypernodeInDB(**doc))
        return total, nodes

    async def update(
        self,
        hypergraph_id: str,
        node_id: str,
        patch: HypernodePatch,
    ) -> Optional[HypernodeInDB]:
        from hgai.models.common import now_utc
        update_fields: Dict[str, Any] = {}
        for attr in ("label", "description", "type", "status", "tags", "attributes", "valid_from", "valid_to"):
            val = getattr(patch, attr, None)
            if val is not None:
                update_fields[attr] = val
        update_fields["system_updated"] = now_utc()
        if patch.updated_by:
            update_fields["updated_by"] = patch.updated_by

        result = await _col().find_one_and_update(
            {"id": node_id, "hypergraph_id": hypergraph_id},
            {"$set": update_fields, "$inc": {"version": 1}},
            return_document=True,
        )
        if not result:
            return None
        result.pop("_id", None)
        return HypernodeInDB(**result)

    async def delete(self, hypergraph_id: str, node_id: str) -> bool:
        result = await _col().delete_one({"id": node_id, "hypergraph_id": hypergraph_id})
        return result.deleted_count > 0

    async def delete_by_graph(self, hypergraph_id: str) -> int:
        result = await _col().delete_many({"hypergraph_id": hypergraph_id})
        return result.deleted_count

    async def search(
        self,
        filters: HypernodeSearchFilters,
        skip: int = 0,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {
            "hypergraph_id": {"$in": filters.hypergraph_ids},
        }
        if filters.status:
            query["status"] = filters.status
        if filters.node_type:
            query["type"] = filters.node_type
        if filters.tags:
            query["tags"] = {"$all": filters.tags}
        if filters.search:
            query["label"] = {"$regex": filters.search, "$options": "i"}
        if filters.node_ids_in:
            query["id"] = {"$in": filters.node_ids_in}
        if filters.attributes:
            for k, v in filters.attributes.items():
                query[f"attributes.{k}"] = v
        if filters.pit:
            query["$and"] = _pit_clause(filters.pit)

        cursor = _col().find(query).skip(skip).limit(limit)
        docs = []
        async for doc in cursor:
            doc.pop("_id", None)
            docs.append(doc)
        return docs

    async def get_distinct_types(self, hypergraph_id: str) -> List[str]:
        return await _col().distinct("type", {"hypergraph_id": hypergraph_id})

    async def find_by_ids(
        self, node_ids: List[str], hypergraph_ids: List[str]
    ) -> List[Dict[str, Any]]:
        cursor = _col().find(
            {"id": {"$in": node_ids}, "hypergraph_id": {"$in": hypergraph_ids}}
        )
        docs = []
        async for doc in cursor:
            doc.pop("_id", None)
            docs.append(doc)
        return docs

    async def find_relation_node(
        self, relation: str, hypergraph_id: str
    ) -> Optional[Dict[str, Any]]:
        doc = await _col().find_one(
            {"id": relation, "hypergraph_id": hypergraph_id, "type": "RelationType"},
            {"attributes.inverse": 1},
        )
        return doc
