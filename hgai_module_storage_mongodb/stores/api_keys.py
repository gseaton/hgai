"""MongoDB API key store implementation."""

from typing import Any, Dict, List, Optional, Tuple

from hgai.models.api_key import ApiKeyInDB
from hgai_module_storage.backend import ApiKeyStore

from ..connection import get_db


def _col():
    return get_db()["api_keys"]


class MongoApiKeyStore(ApiKeyStore):

    async def create(self, doc: Dict[str, Any]) -> ApiKeyInDB:
        await _col().insert_one(doc)
        doc.pop("_id", None)
        return ApiKeyInDB(**doc)

    async def get(self, key_id: str) -> Optional[ApiKeyInDB]:
        raw = await _col().find_one({"id": key_id})
        if not raw:
            return None
        raw.pop("_id", None)
        return ApiKeyInDB(**raw)

    async def get_by_hash(self, key_hash: str) -> Optional[ApiKeyInDB]:
        raw = await _col().find_one({"key_hash": key_hash})
        if not raw:
            return None
        raw.pop("_id", None)
        return ApiKeyInDB(**raw)

    async def list(self, tenant_id: Optional[str], skip: int = 0, limit: int = 50) -> Tuple[int, List[ApiKeyInDB]]:
        query: Dict[str, Any] = {} if tenant_id is None else {"tenant_id": tenant_id}
        total = await _col().count_documents(query)
        docs = await _col().find(query).skip(skip).limit(limit).sort("system_created", -1).to_list(length=limit)
        keys = []
        for doc in docs:
            doc.pop("_id", None)
            keys.append(ApiKeyInDB(**doc))
        return total, keys

    async def delete(self, key_id: str) -> bool:
        result = await _col().delete_one({"id": key_id})
        return result.deleted_count > 0

    async def touch(self, key_id: str, when: Any) -> None:
        await _col().update_one({"id": key_id}, {"$set": {"last_used": when}})
