"""Query result caching for HypergraphAI."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from hgai.config import get_settings
from hgai.db.mongodb import col_query_cache


async def get_cached_result(cache_key: str) -> Optional[Dict[str, Any]]:
    settings = get_settings()
    if not settings.cache_enabled:
        return None

    doc = await col_query_cache().find_one({"cache_key": cache_key})
    if not doc:
        return None

    # TTL check (belt-and-suspenders beyond MongoDB TTL index)
    expires_at = doc.get("expires_at")
    if expires_at and datetime.now(timezone.utc) > expires_at.replace(tzinfo=timezone.utc):
        await col_query_cache().delete_one({"cache_key": cache_key})
        return None

    return doc.get("result")


async def set_cached_result(cache_key: str, result: Dict[str, Any]) -> None:
    settings = get_settings()
    if not settings.cache_enabled:
        return

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.cache_ttl_seconds)
    await col_query_cache().replace_one(
        {"cache_key": cache_key},
        {
            "cache_key": cache_key,
            "result": result,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
        },
        upsert=True,
    )


async def invalidate_cache(graph_id: Optional[str] = None) -> int:
    """Invalidate cached query results. If graph_id given, only invalidate for that graph."""
    if graph_id:
        # Can't easily filter by graph_id in cache keys without storing metadata
        # For now, flush all cache when a graph is modified
        result = await col_query_cache().delete_many({})
    else:
        result = await col_query_cache().delete_many({})
    return result.deleted_count


async def get_cache_stats() -> Dict[str, Any]:
    total = await col_query_cache().count_documents({})
    now = datetime.now(timezone.utc)
    expired = await col_query_cache().count_documents({"expires_at": {"$lt": now}})
    return {
        "total_entries": total,
        "expired_entries": expired,
        "active_entries": total - expired,
    }
