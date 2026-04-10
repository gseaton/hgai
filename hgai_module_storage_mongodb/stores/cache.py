"""MongoDB query cache store implementation."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from hgai_module_storage.backend import CacheStore

from ..connection import get_db


def _col():
    return get_db()["query_cache"]


class MongoCacheStore(CacheStore):

    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        doc = await _col().find_one({"cache_key": cache_key})
        if not doc:
            return None

        # Belt-and-suspenders TTL check beyond MongoDB TTL index
        expires_at = doc.get("expires_at")
        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires_at:
                await _col().delete_one({"cache_key": cache_key})
                return None

        return doc.get("result")

    async def set(
        self,
        cache_key: str,
        result: Dict[str, Any],
        graph_ids: Optional[List[str]] = None,
        ttl_seconds: int = 300,
    ) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        await _col().replace_one(
            {"cache_key": cache_key},
            {
                "cache_key": cache_key,
                "result": result,
                "graph_ids": graph_ids or [],
                "expires_at": expires_at,
                "created_at": datetime.now(timezone.utc),
            },
            upsert=True,
        )

    async def invalidate(self, graph_id: Optional[str] = None) -> int:
        if graph_id:
            result = await _col().delete_many({"graph_ids": graph_id})
        else:
            result = await _col().delete_many({})
        return result.deleted_count

    async def stats(self) -> Dict[str, Any]:
        total = await _col().count_documents({})
        now = datetime.now(timezone.utc)
        expired = await _col().count_documents({"expires_at": {"$lt": now}})
        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
        }
