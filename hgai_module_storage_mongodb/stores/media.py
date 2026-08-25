"""MongoDB (GridFS-backed) media store implementation."""

import hashlib
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorGridFSBucket

from hgai.models.common import now_utc
from hgai.models.media import Media
from hgai_module_storage.backend import MediaStore
from hgai_module_storage.filters import MediaFilters, MediaPatch

from ..connection import get_db

_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1MB read chunks while streaming an upload in


def _col():
    return get_db()["media"]


def _bucket() -> AsyncIOMotorGridFSBucket:
    return AsyncIOMotorGridFSBucket(get_db(), bucket_name="media")


class MongoMediaStore(MediaStore):

    async def put(
        self,
        media_id: str,
        stream: Any,
        content_type: str,
        filename: Optional[str],
        uploaded_by: str,
    ) -> Media:
        bucket = _bucket()
        hasher = hashlib.sha256()
        size_bytes = 0

        # open_upload_stream_with_id() is NOT a coroutine — it returns the GridIn
        # synchronously; only .write()/.close() on it are awaitable.
        grid_in = bucket.open_upload_stream_with_id(
            media_id, filename or media_id, metadata={"content_type": content_type}
        )
        try:
            while True:
                chunk = await stream.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
                size_bytes += len(chunk)
                await grid_in.write(chunk)
            await grid_in.close()
        except Exception:
            await grid_in.abort()
            raise

        checksum = hasher.hexdigest()

        # Dedup: the checksum can only be known once the stream is fully
        # consumed, so the blob is always written first — if another media
        # record already has this exact content, discard the copy we just
        # wrote and hand back the existing record instead of storing a
        # duplicate. Best-effort under concurrency (no unique-index race
        # guard); a rare simultaneous duplicate upload may still keep both
        # blobs, which is safe, just not maximally deduplicated.
        existing_raw = await _col().find_one({"checksum": checksum})
        if existing_raw:
            try:
                await bucket.delete(media_id)
            except Exception:
                pass
            existing_raw.pop("_id", None)
            return Media(**existing_raw)

        now = now_utc()
        doc = {
            "id": media_id,
            "content_type": content_type,
            "filename": filename,
            "size_bytes": size_bytes,
            "checksum": checksum,
            "uploaded_by": uploaded_by,
            "ref_count": 0,
            "system_created": now,
            "system_updated": now,
            "created_by": uploaded_by,
            "version": 1,
            "tags": [],
            "status": "active",
            "attributes": {},
        }
        await _col().insert_one(dict(doc))
        doc.pop("_id", None)
        return Media(**doc)

    async def get_stream(self, media_id: str) -> Optional[Tuple[Media, AsyncIterator[bytes]]]:
        metadata = await self.get_metadata(media_id)
        if not metadata:
            return None
        grid_out = await _bucket().open_download_stream(media_id)
        return metadata, grid_out

    async def get_metadata(self, media_id: str) -> Optional[Media]:
        raw = await _col().find_one({"id": media_id})
        if not raw:
            return None
        raw.pop("_id", None)
        return Media(**raw)

    async def delete(self, media_id: str) -> bool:
        result = await _col().delete_one({"id": media_id})
        if result.deleted_count == 0:
            return False
        try:
            await _bucket().delete(media_id)
        except Exception:
            pass  # metadata is already gone; blob deletion is best-effort cleanup
        return True

    async def adjust_ref_count(self, media_id: str, delta: int) -> None:
        await _col().find_one_and_update(
            {"id": media_id}, {"$inc": {"ref_count": delta}}
        )

    async def list_orphaned(self, older_than: datetime) -> List[Media]:
        cursor = _col().find({"ref_count": 0, "system_created": {"$lt": older_than}})
        out = []
        async for doc in cursor:
            doc.pop("_id", None)
            out.append(Media(**doc))
        return out

    async def list(
        self,
        filters: MediaFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Media]]:
        query: Dict[str, Any] = {}
        if filters.status:
            query["status"] = filters.status
        if filters.content_type:
            query["content_type"] = filters.content_type
        if filters.tags:
            query["tags"] = {"$all": filters.tags}
        if filters.search:
            query["filename"] = {"$regex": filters.search, "$options": "i"}

        total = await _col().count_documents(query)
        cursor = _col().find(query).skip(skip).limit(limit).sort("system_created", -1)
        docs = await cursor.to_list(length=limit)
        items = []
        for doc in docs:
            doc.pop("_id", None)
            items.append(Media(**doc))
        return total, items

    async def update(self, media_id: str, patch: MediaPatch) -> Optional[Media]:
        update_fields: Dict[str, Any] = {}
        for attr in ("filename", "tags", "attributes", "status"):
            val = getattr(patch, attr, None)
            if val is not None:
                update_fields[attr] = val
        update_fields["system_updated"] = now_utc()
        if patch.updated_by:
            update_fields["updated_by"] = patch.updated_by

        result = await _col().find_one_and_update(
            {"id": media_id},
            {"$set": update_fields, "$inc": {"version": 1}},
            return_document=True,
        )
        if not result:
            return None
        result.pop("_id", None)
        return Media(**result)
