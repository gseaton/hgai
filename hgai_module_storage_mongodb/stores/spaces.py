"""MongoDB space store implementation."""

from typing import Any, Dict, List, Optional, Tuple

from hgai.models.space import SpaceInDB
from hgai_module_storage.backend import SpaceStore
from hgai_module_storage.filters import SpaceFilters, SpacePatch

from ..connection import get_db


def _col():
    return get_db()["spaces"]


def _col_graphs():
    return get_db()["hypergraphs"]


class MongoSpaceStore(SpaceStore):

    async def create(self, doc: Dict[str, Any]) -> SpaceInDB:
        await _col().insert_one(doc)
        doc.pop("_id", None)
        return SpaceInDB(**doc)

    async def get(self, space_id: str) -> Optional[SpaceInDB]:
        raw = await _col().find_one({"id": space_id})
        if not raw:
            return None
        raw.pop("_id", None)
        return SpaceInDB(**raw)

    async def list(
        self,
        filters: SpaceFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[SpaceInDB]]:
        query: Dict[str, Any] = {"status": "active"}
        if filters.username:
            query["members.username"] = filters.username
        if filters.status:
            query["status"] = filters.status

        total = await _col().count_documents(query)
        cursor = _col().find(query).skip(skip).limit(limit).sort("system_created", -1)
        docs = await cursor.to_list(length=limit)
        spaces = []
        for doc in docs:
            doc.pop("_id", None)
            spaces.append(SpaceInDB(**doc))
        return total, spaces

    async def update(
        self,
        space_id: str,
        patch: SpacePatch,
    ) -> Optional[SpaceInDB]:
        from hgai.models.common import now_utc
        update_fields: Dict[str, Any] = {}
        for attr in ("label", "description", "status", "attributes"):
            val = getattr(patch, attr, None)
            if val is not None:
                update_fields[attr] = val
        update_fields["system_updated"] = now_utc()
        if patch.updated_by:
            update_fields["updated_by"] = patch.updated_by

        result = await _col().find_one_and_update(
            {"id": space_id},
            {"$set": update_fields, "$inc": {"version": 1}},
            return_document=True,
        )
        if not result:
            return None
        result.pop("_id", None)
        return SpaceInDB(**result)

    async def delete(self, space_id: str) -> bool:
        result = await _col().delete_one({"id": space_id})
        return result.deleted_count > 0

    async def add_member(self, space_id: str, username: str, role: str) -> Optional[SpaceInDB]:
        from hgai.models.common import now_utc
        now = now_utc()
        # Remove existing entry for this user, then add fresh entry
        await _col().update_one(
            {"id": space_id},
            {"$pull": {"members": {"username": username}}},
        )
        result = await _col().find_one_and_update(
            {"id": space_id},
            {
                "$push": {"members": {"username": username, "role": role}},
                "$set": {"system_updated": now},
                "$inc": {"version": 1},
            },
            return_document=True,
        )
        if not result:
            return None
        result.pop("_id", None)
        return SpaceInDB(**result)

    async def remove_member(self, space_id: str, username: str) -> Optional[SpaceInDB]:
        from hgai.models.common import now_utc
        result = await _col().find_one_and_update(
            {"id": space_id},
            {
                "$pull": {"members": {"username": username}},
                "$set": {"system_updated": now_utc()},
                "$inc": {"version": 1},
            },
            return_document=True,
        )
        if not result:
            return None
        result.pop("_id", None)
        return SpaceInDB(**result)

    async def get_member_role(self, space_id: str, username: str) -> Optional[str]:
        doc = await _col().find_one(
            {"id": space_id, "members.username": username},
            {"members.$": 1},
        )
        if not doc or not doc.get("members"):
            return None
        return doc["members"][0].get("role")

    async def remove_user_from_all_spaces(self, username: str) -> None:
        await _col().update_many(
            {"members.username": username},
            {"$pull": {"members": {"username": username}}},
        )

    async def list_space_ids_for_member(self, username: str) -> List[str]:
        cursor = _col().find(
            {"members.username": username, "status": "active"},
            {"id": 1},
        )
        return [doc["id"] async for doc in cursor]

    async def get_space_for_graph(self, graph_id: str) -> Optional[str]:
        doc = await _col_graphs().find_one({"id": graph_id}, {"space_id": 1})
        if not doc:
            return None
        return doc.get("space_id")

    async def update_many_hypergraphs(
        self, space_id: str, update_doc: Dict[str, Any]
    ) -> None:
        await _col_graphs().update_many({"space_id": space_id}, update_doc)

    async def list_active_space_ids_for_user(self, username: str) -> List[str]:
        cursor = _col().find(
            {"members.username": username, "status": "active"},
            {"id": 1},
        )
        return [doc["id"] async for doc in cursor]
