"""S3-compatible media store implementation.

Blob bytes go to an S3-compatible bucket instead of GridFS; metadata (id,
checksum, ref_count, ...) stays in the *same* Mongo `media` collection that
MongoMediaStore uses, so refcounting/dedup/orphan-sweep logic is identical
regardless of which blob backend is active — only the byte storage differs.
Selected via HGAI_MEDIA_BACKEND=s3 (see hgai/config.py).

Note on streaming: uploads are buffered in memory before a single blocking
`put_object` call (bounded by the already-enforced HGAI_MAX_MEDIA_SIZE_MB —
not unbounded), since S3's simple PUT API needs a known content length;
downloads *do* stream properly, via chunked reads off the S3 response body.
A full multipart-upload implementation would avoid the upload-side buffering
but is meaningfully more code for a config-toggled, optional backend this
environment has no live AWS S3 access to test against end-to-end (verified
here against a local moto mock server instead).
"""

import asyncio
import hashlib
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

from hgai.config import get_settings
from hgai.models.common import now_utc
from hgai.models.media import Media
from hgai_module_storage.backend import MediaStore
from hgai_module_storage.filters import MediaFilters, MediaPatch

from ..connection import get_db

_UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1MB read chunks while buffering an upload


def _col():
    return get_db()["media"]


def _s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url or None,
        aws_access_key_id=settings.s3_access_key_id or None,
        aws_secret_access_key=settings.s3_secret_access_key or None,
        region_name=settings.s3_region,
    )


class S3MediaStore(MediaStore):

    def __init__(self):
        settings = get_settings()
        if not settings.s3_bucket:
            raise ValueError("HGAI_S3_BUCKET must be set when HGAI_MEDIA_BACKEND=s3")
        self._bucket = settings.s3_bucket

    async def put(
        self,
        media_id: str,
        stream: Any,
        content_type: str,
        filename: Optional[str],
        uploaded_by: str,
    ) -> Media:
        hasher = hashlib.sha256()
        chunks: List[bytes] = []
        size_bytes = 0
        while True:
            chunk = await stream.read(_UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
            size_bytes += len(chunk)
            chunks.append(chunk)
        body = b"".join(chunks)
        checksum = hasher.hexdigest()

        # Dedup — see MongoMediaStore.put() for the same best-effort rationale.
        existing_raw = await _col().find_one({"checksum": checksum})
        if existing_raw:
            existing_raw.pop("_id", None)
            return Media(**existing_raw)

        bucket = self._bucket

        def _upload():
            _s3_client().put_object(
                Bucket=bucket, Key=media_id, Body=body, ContentType=content_type
            )
        await asyncio.to_thread(_upload)

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

        bucket = self._bucket
        try:
            s3_body = await asyncio.to_thread(
                lambda: _s3_client().get_object(Bucket=bucket, Key=media_id)["Body"]
            )
        except ClientError:
            return None

        async def _aiter():
            while True:
                chunk = await asyncio.to_thread(s3_body.read, _UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk

        return metadata, _aiter()

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
        bucket = self._bucket

        def _remove():
            try:
                _s3_client().delete_object(Bucket=bucket, Key=media_id)
            except ClientError:
                pass  # metadata is already gone; blob deletion is best-effort cleanup
        await asyncio.to_thread(_remove)
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
