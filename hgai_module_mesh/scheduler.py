"""Background mesh sync scheduler."""

import asyncio
import logging

logger = logging.getLogger(__name__)

_sync_task: asyncio.Task = None


async def _sync_loop(interval_seconds: int) -> None:
    """Periodically sync graph lists for all active meshes."""
    from hgai.db.mongodb import col_meshes
    from .engine import sync_mesh_graphs

    logger.info(f"Mesh sync scheduler started (interval: {interval_seconds}s)")
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            cursor = col_meshes().find({"status": "active"})
            async for doc in cursor:
                mesh_id = doc.get("id")
                if mesh_id:
                    try:
                        result = await sync_mesh_graphs(mesh_id)
                        logger.debug(f"Mesh sync: {result}")
                    except Exception as e:
                        logger.warning(f"Mesh sync failed for '{mesh_id}': {e}")
        except Exception as e:
            logger.warning(f"Mesh sync loop error: {e}")


def start_scheduler(interval_seconds: int) -> None:
    global _sync_task
    if interval_seconds <= 0:
        return
    _sync_task = asyncio.create_task(_sync_loop(interval_seconds))
    logger.info(f"Mesh background sync task created (interval: {interval_seconds}s)")


def stop_scheduler() -> None:
    global _sync_task
    if _sync_task and not _sync_task.done():
        _sync_task.cancel()
        _sync_task = None
        logger.info("Mesh background sync task stopped")
