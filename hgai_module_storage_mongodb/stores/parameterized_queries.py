"""MongoDB parameterized-query store implementation."""

from typing import Any, Dict, List, Optional, Tuple

from hgai.models.parameterized_query import ParameterizedQueryInDB
from hgai_module_storage.backend import ParameterizedQueryStore
from hgai_module_storage.filters import ParameterizedQueryFilters, ParameterizedQueryPatch

from ..connection import get_db


def _col():
    return get_db()["parameterized_queries"]


class MongoParameterizedQueryStore(ParameterizedQueryStore):

    async def create(self, doc: Dict[str, Any]) -> ParameterizedQueryInDB:
        await _col().insert_one(doc)
        doc.pop("_id", None)
        return ParameterizedQueryInDB(**doc)

    async def get(self, query_id: str) -> Optional[ParameterizedQueryInDB]:
        raw = await _col().find_one({"id": query_id})
        if not raw:
            return None
        raw.pop("_id", None)
        return ParameterizedQueryInDB(**raw)

    async def list(
        self,
        filters: ParameterizedQueryFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[ParameterizedQueryInDB]]:
        clauses: List[Dict[str, Any]] = []
        if filters.status:
            clauses.append({"status": filters.status})
        if filters.tags:
            clauses.append({"tags": {"$all": filters.tags}})
        if filters.search:
            clauses.append({"$or": [
                {"name": {"$regex": filters.search, "$options": "i"}},
                {"label": {"$regex": filters.search, "$options": "i"}},
                {"description": {"$regex": filters.search, "$options": "i"}},
            ]})
        query: Dict[str, Any] = {"$and": clauses} if clauses else {}

        total = await _col().count_documents(query)
        sort_spec = filters.sort or [("system_created", -1)]
        cursor = _col().find(query).skip(skip).limit(limit).sort(sort_spec)
        docs = await cursor.to_list(length=limit)
        queries = []
        for doc in docs:
            doc.pop("_id", None)
            queries.append(ParameterizedQueryInDB(**doc))
        return total, queries

    async def update(self, query_id: str, patch: ParameterizedQueryPatch) -> Optional[ParameterizedQueryInDB]:
        from hgai.models.common import now_utc
        update_fields: Dict[str, Any] = {}
        for attr in ("name", "label", "description", "shql", "parameters", "tags", "attributes", "status", "mutations"):
            val = getattr(patch, attr, None)
            if val is not None:
                update_fields[attr] = val
        update_fields["system_updated"] = now_utc()

        result = await _col().find_one_and_update(
            {"id": query_id},
            {"$set": update_fields, "$inc": {"version": 1}},
            return_document=True,
        )
        if not result:
            return None
        result.pop("_id", None)
        return ParameterizedQueryInDB(**result)

    async def delete(self, query_id: str) -> bool:
        result = await _col().delete_one({"id": query_id})
        return result.deleted_count > 0
