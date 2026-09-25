"""MongoDB hyperedge store implementation."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from hgai.models.hyperedge import HyperedgeInDB
from hgai_module_storage.backend import HyperedgeStore
from hgai_module_storage.filters import (
    AggregateSpec,
    HyperedgeFilters,
    HyperedgePatch,
    HyperedgeSearchFilters,
    TransitiveSearchFilter,
)
from hgai_module_storage.ordering import normalise_order

from ..aggregation import run_aggregate
from ..connection import get_db


def _col():
    return get_db()["hyperedges"]


def _pit_clause(pit: datetime) -> List[Dict[str, Any]]:
    return [
        {"$or": [{"valid_from": None}, {"valid_from": {"$lte": pit}}]},
        {"$or": [{"valid_to": None}, {"valid_to": {"$gte": pit}}]},
    ]


def _build_search_query(filters: HyperedgeSearchFilters) -> Dict[str, Any]:
    query: Dict[str, Any] = {
        "hypergraph_id": {"$in": filters.hypergraph_ids},
    }
    if filters.status:
        query["status"] = filters.status
    if filters.relation:
        query["relation"] = filters.relation
    if filters.flavor:
        query["flavor"] = filters.flavor
    if filters.tags:
        query["tags"] = {"$all": filters.tags}
    if filters.member_node_id:
        query["members.node_id"] = filters.member_node_id
    if filters.member_node_ids_all:
        query["members.node_id"] = {"$all": filters.member_node_ids_all}
    if filters.member_node_ids_any:
        query["members.node_id"] = {"$in": filters.member_node_ids_any}
    if filters.attributes:
        for k, v in filters.attributes.items():
            query[f"attributes.{k}"] = v
    if filters.extra_filters:
        query.update(filters.extra_filters)
    if filters.pit:
        existing_and = query.pop("$and", [])
        query["$and"] = existing_and + _pit_clause(filters.pit)
    return query


class MongoHyperedgeStore(HyperedgeStore):

    supports_aggregate_pushdown = True
    supports_ordered_search = True

    async def create(self, doc: Dict[str, Any]) -> HyperedgeInDB:
        await _col().insert_one(doc)
        doc.pop("_id", None)
        return HyperedgeInDB(**doc)

    async def get_by_id_or_hyperkey(
        self, hypergraph_id: str, edge_id: str
    ) -> Optional[HyperedgeInDB]:
        raw = await _col().find_one(
            {"$or": [{"id": edge_id}, {"hyperkey": edge_id}], "hypergraph_id": hypergraph_id}
        )
        if not raw:
            return None
        raw.pop("_id", None)
        return HyperedgeInDB(**raw)

    async def list(
        self,
        filters: HyperedgeFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[HyperedgeInDB]]:
        query: Dict[str, Any] = {"hypergraph_id": filters.hypergraph_id}
        if filters.status:
            query["status"] = filters.status
        if filters.relation:
            query["relation"] = filters.relation
        if filters.flavor:
            query["flavor"] = filters.flavor
        if filters.tags:
            query["tags"] = {"$all": filters.tags}
        if filters.member_node_id:
            query["members.node_id"] = filters.member_node_id
        if filters.pit:
            query["$and"] = _pit_clause(filters.pit)

        total = await _col().count_documents(query)
        sort_spec = filters.sort or [("system_created", -1)]
        cursor = _col().find(query).skip(skip).limit(limit).sort(sort_spec)
        docs = await cursor.to_list(length=limit)
        edges = []
        for doc in docs:
            doc.pop("_id", None)
            edges.append(HyperedgeInDB(**doc))
        return total, edges

    async def update(
        self,
        hypergraph_id: str,
        edge_id: str,
        patch: HyperedgePatch,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Optional[HyperedgeInDB]:
        from hgai.models.common import now_utc
        update_fields: Dict[str, Any] = {}
        for attr in (
            "label", "description", "relation", "flavor", "status", "tags",
            "attributes", "members", "valid_from", "valid_to",
            "skos_broader", "skos_narrower", "skos_related", "media", "default_media_id",
            "mutations",
        ):
            val = getattr(patch, attr, None)
            if val is not None:
                update_fields[attr] = val
        update_fields["system_updated"] = now_utc()
        if patch.updated_by:
            update_fields["updated_by"] = patch.updated_by
        if extra_fields:
            update_fields.update(extra_fields)

        result = await _col().find_one_and_update(
            {"$or": [{"id": edge_id}, {"hyperkey": edge_id}], "hypergraph_id": hypergraph_id},
            {"$set": update_fields, "$inc": {"version": 1}},
            return_document=True,
        )
        if not result:
            return None
        result.pop("_id", None)
        return HyperedgeInDB(**result)

    async def delete(self, hypergraph_id: str, edge_id: str) -> bool:
        result = await _col().delete_one(
            {"$or": [{"id": edge_id}, {"hyperkey": edge_id}], "hypergraph_id": hypergraph_id}
        )
        return result.deleted_count > 0

    async def delete_by_graph(self, hypergraph_id: str) -> int:
        result = await _col().delete_many({"hypergraph_id": hypergraph_id})
        return result.deleted_count

    async def search(
        self,
        filters: HyperedgeSearchFilters,
        skip: int = 0,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        query = _build_search_query(filters)

        cursor = _col().find(query).skip(skip).limit(limit)
        docs = []
        async for doc in cursor:
            doc.pop("_id", None)
            docs.append(doc)
        return docs

    async def search_ordered(
        self, filters: HyperedgeSearchFilters, order_by, skip: int = 0, limit: int = 500,
    ) -> List[Dict[str, Any]]:
        sort = [(p, -1 if desc else 1) for p, desc in normalise_order(order_by)]
        if limit <= 0:   # Mongo treats limit(0) as "no limit"
            return []
        cursor = (
            _col().find(_build_search_query(filters))
            .sort(sort).skip(skip).limit(limit).allow_disk_use(True)
        )
        docs = []
        async for doc in cursor:
            doc.pop("_id", None)
            docs.append(doc)
        return docs

    async def aggregate(
        self, filters: HyperedgeSearchFilters, spec: AggregateSpec
    ) -> List[Dict[str, Any]]:
        return await run_aggregate(_col(), _build_search_query(filters), spec)

    async def get_distinct_relations(self, hypergraph_id: str) -> List[str]:
        return await _col().distinct("relation", {"hypergraph_id": hypergraph_id})

    async def find_for_transitive(
        self, filters: TransitiveSearchFilter
    ) -> List[Dict[str, Any]]:
        """Return full raw edge dicts for transitive/axiom closure traversal."""
        query: Dict[str, Any] = {
            "hypergraph_id": {"$in": filters.hypergraph_ids},
            "relation": filters.relation,
            "members.node_id": {"$in": filters.member_node_ids},
            "status": "active",
        }
        if filters.pit:
            query["$and"] = _pit_clause(filters.pit)
        cursor = _col().find(query)
        docs = []
        async for doc in cursor:
            doc.pop("_id", None)
            docs.append(doc)
        return docs

    async def find_relation_node(
        self, relation: str, hypergraph_id: str
    ) -> Optional[Dict[str, Any]]:
        """Delegate to hypernodes collection to find the RelationType node."""
        db = get_db()
        doc = await db["hypernodes"].find_one(
            {"id": relation, "hypergraph_id": hypergraph_id, "type": "RelationType"},
            {"attributes.inverse": 1},
        )
        return doc
