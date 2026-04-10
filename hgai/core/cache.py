"""Query result caching for HypergraphAI."""

from typing import Any, Dict, List, Optional

from hgai.config import get_settings
from hgai.db.storage import get_storage


async def get_cached_result(cache_key: str) -> Optional[Dict[str, Any]]:
    settings = get_settings()
    if not settings.cache_enabled:
        return None
    return await get_storage().cache.get(cache_key)


async def set_cached_result(
    cache_key: str,
    result: Dict[str, Any],
    graph_ids: Optional[List[str]] = None,
) -> None:
    """Store a query result in the cache.

    graph_ids should be the list of local hypergraph IDs the query touched.
    These are stored on the cache document so invalidate_cache(graph_id) can
    target only the entries affected by a specific graph mutation.
    """
    settings = get_settings()
    if not settings.cache_enabled:
        return
    await get_storage().cache.set(
        cache_key,
        result,
        graph_ids=graph_ids,
        ttl_seconds=settings.cache_ttl_seconds,
    )


async def invalidate_cache(graph_id: Optional[str] = None) -> int:
    """Invalidate cached query results.

    If graph_id is provided, only entries that queried that specific graph are
    removed — leaving unrelated graph caches intact.
    If graph_id is None, the entire cache is flushed.
    """
    return await get_storage().cache.invalidate(graph_id)


async def get_cache_stats() -> Dict[str, Any]:
    return await get_storage().cache.stats()
