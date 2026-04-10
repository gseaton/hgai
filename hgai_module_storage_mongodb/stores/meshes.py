"""MongoDB mesh store implementation."""

from typing import Any, Dict, List, Optional, Tuple

from hgai_module_storage.backend import MeshStore
from hgai_module_storage.filters import MeshFilters

from ..connection import get_db


def _col():
    return get_db()["meshes"]


class MongoMeshStore(MeshStore):

    async def create(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        await _col().insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def get(self, mesh_id: str) -> Optional[Dict[str, Any]]:
        doc = await _col().find_one({"id": mesh_id})
        if not doc:
            return None
        doc.pop("_id", None)
        return doc

    async def list(
        self,
        filters: MeshFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        query: Dict[str, Any] = {}
        if filters.status:
            query["status"] = filters.status

        total = await _col().count_documents(query)
        cursor = _col().find(query).skip(skip).limit(limit).sort("system_created", -1)
        docs = await cursor.to_list(length=limit)
        result = []
        for doc in docs:
            doc.pop("_id", None)
            result.append(doc)
        return total, result

    async def update(
        self,
        mesh_id: str,
        update_fields: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        result = await _col().find_one_and_update(
            {"id": mesh_id},
            {"$set": update_fields, "$inc": {"version": 1}},
            return_document=True,
        )
        if not result:
            return None
        result.pop("_id", None)
        return result

    async def delete(self, mesh_id: str) -> bool:
        result = await _col().delete_one({"id": mesh_id})
        return result.deleted_count > 0

    async def update_servers(self, mesh_id: str, servers: List[Any]) -> None:
        from hgai.models.common import now_utc
        await _col().update_one(
            {"id": mesh_id},
            {"$set": {"servers": servers, "system_updated": now_utc()}},
        )

    async def list_active(self) -> List[Dict[str, Any]]:
        cursor = _col().find({"status": "active"})
        docs = []
        async for doc in cursor:
            doc.pop("_id", None)
            docs.append(doc)
        return docs
