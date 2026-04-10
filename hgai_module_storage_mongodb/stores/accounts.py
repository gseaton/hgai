"""MongoDB account store implementation."""

from typing import Any, Dict, List, Optional, Tuple

from hgai_module_storage.backend import AccountStore
from hgai_module_storage.filters import AccountFilters

from ..connection import get_db


def _col():
    return get_db()["accounts"]


class MongoAccountStore(AccountStore):

    async def create(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        await _col().insert_one(doc)
        doc.pop("_id", None)
        return doc

    async def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        doc = await _col().find_one({"username": username})
        if not doc:
            return None
        doc.pop("_id", None)
        return doc

    async def exists(self, username: str) -> bool:
        doc = await _col().find_one({"username": username}, {"_id": 1})
        return doc is not None

    async def list(
        self,
        filters: AccountFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        query: Dict[str, Any] = {}
        if filters.status:
            query["status"] = filters.status
        if filters.role:
            query["roles"] = filters.role

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
        username: str,
        update_fields: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        result = await _col().find_one_and_update(
            {"username": username},
            {"$set": update_fields, "$inc": {"version": 1}},
            return_document=True,
        )
        if not result:
            return None
        result.pop("_id", None)
        return result

    async def delete(self, username: str) -> bool:
        result = await _col().delete_one({"username": username})
        return result.deleted_count > 0

    async def record_login(self, username: str) -> None:
        from hgai.models.common import now_utc
        await _col().update_one(
            {"username": username},
            {"$set": {"last_login": now_utc()}},
        )
