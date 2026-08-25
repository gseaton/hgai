"""Media reference helpers: mesh-qualified id parsing and refcount bookkeeping.

media_id format:
    "<media-identifier>"                    - local media, owned by this server
    "<mesh-hgai-server>/<media-identifier>" - remote media, owned by another mesh server

`media-identifier` is a UUID4/ULID by construction and never contains "/", so
parsing on the first "/" is unambiguous.
"""

from datetime import timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from hgai.db.storage import get_storage
from hgai.models.common import now_utc


def parse_media_id(media_id: str) -> Tuple[Optional[str], str]:
    """Split a media_id into (server_id, local_id). server_id is None when local."""
    if "/" in media_id:
        server_id, local_id = media_id.split("/", 1)
        return server_id, local_id
    return None, media_id


def _extract_local_ids(media_refs: Optional[List[Any]]) -> Set[str]:
    """Return the set of *local* media ids referenced by a media list.

    Accepts either MediaRef model instances or plain dicts (both occur:
    engine callers may pass validated models on create, while patch data
    coming from `.model_dump()` is already plain dicts).
    Mesh-qualified (remote) ids are skipped — they're refcounted by their
    origin server, not this one.
    """
    ids: Set[str] = set()
    for ref in media_refs or []:
        media_id = ref.media_id if hasattr(ref, "media_id") else ref.get("media_id")
        if not media_id:
            continue
        server_id, local_id = parse_media_id(media_id)
        if server_id is None:
            ids.add(local_id)
    return ids


async def adjust_media_refs(media_refs: Optional[List[Any]], delta: int) -> None:
    """Apply `delta` to ref_count for every local media_id in `media_refs`."""
    for local_id in _extract_local_ids(media_refs):
        await get_storage().media.adjust_ref_count(local_id, delta)


async def apply_media_diff(
    old_refs: Optional[List[Any]], new_refs: Optional[List[Any]]
) -> None:
    """On update: increment newly-added local media ids, decrement removed ones.

    If `new_refs` is None, the update didn't touch `media` at all — no-op.
    """
    if new_refs is None:
        return
    old_ids = _extract_local_ids(old_refs)
    new_ids = _extract_local_ids(new_refs)
    for local_id in new_ids - old_ids:
        await get_storage().media.adjust_ref_count(local_id, 1)
    for local_id in old_ids - new_ids:
        await get_storage().media.adjust_ref_count(local_id, -1)


async def delete_media_checked(media_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Delete a local media item after verifying it's safe to delete.

    Shared by the REST endpoint and the MCP tool so both enforce the same
    rules. Returns (deleted, reason_code, message):
      - (True, None, None) on success
      - (False, "remote", ...)     — media_id is mesh-qualified, not ours to delete
      - (False, "not_found", ...)  — no such media
      - (False, "referenced", ...) — ref_count > 0, still attached somewhere
    """
    server_id, local_id = parse_media_id(media_id)
    if server_id is not None:
        return False, "remote", "Cannot delete media owned by another mesh server"

    metadata = await get_storage().media.get_metadata(local_id)
    if not metadata:
        return False, "not_found", f"Media '{media_id}' not found"
    if metadata.ref_count > 0:
        return False, "referenced", (
            f"Media '{media_id}' is still referenced by {metadata.ref_count} "
            f"entit{'y' if metadata.ref_count == 1 else 'ies'}"
        )
    await get_storage().media.delete(local_id)
    return True, None, None


async def sweep_orphaned_media(older_than_hours: int = 24) -> Dict[str, int]:
    """GC safety net: permanently delete media with ref_count == 0 that's older
    than the grace period.

    Refcounting keeps most media accurate, but orphans can still accumulate —
    most commonly because the UI uploads a file immediately on selection (so
    the media record exists) but only attaches it to an entity on Save; a
    user who closes the modal without saving leaves that upload referenced by
    nothing, forever, unless something sweeps it. The grace period avoids
    racing a just-uploaded file that hasn't been attached yet.
    """
    cutoff = now_utc() - timedelta(hours=older_than_hours)
    orphans = await get_storage().media.list_orphaned(cutoff)
    deleted = 0
    for m in orphans:
        if await get_storage().media.delete(m.id):
            deleted += 1
    return {"scanned": len(orphans), "deleted": deleted}
