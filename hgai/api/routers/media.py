"""Media (binary file) upload/download/delete API endpoints.

Not graph-scoped — media is a standalone entity referenced by hypernodes/
hyperedges via their `media: List[MediaRef]` field, so any active account
may upload/download/delete it (mirroring the account-level, non-graph-scoped
access pattern used by e.g. /accounts).
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from hgai.api.deps import get_current_active_account
from hgai.config import get_settings
from hgai.core.auth import require_admin
from hgai.core.media import delete_media_checked, parse_media_id, sweep_orphaned_media
from hgai.db.storage import get_storage
from hgai.models.account import AccountInDB
from hgai.models.common import PaginatedResponse
from hgai.models.media import MediaResponse, MediaUpdate
from hgai_module_storage.filters import MediaFilters, MediaPatch

router = APIRouter(prefix="/media", tags=["media"])


@router.get("", response_model=PaginatedResponse)
async def list_media(
    search: Optional[str] = Query(default=None, description="Filename search (case-insensitive substring)"),
    content_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    tags: Optional[List[str]] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    account: AccountInDB = Depends(get_current_active_account),
):
    filters = MediaFilters(search=search, content_type=content_type, status=status, tags=tags)
    total, items = await get_storage().media.list(filters, skip=skip, limit=limit)
    return PaginatedResponse(
        total=total, skip=skip, limit=limit,
        items=[m.model_dump() for m in items],
    )


@router.post("", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile,
    account: AccountInDB = Depends(get_current_active_account),
):
    settings = get_settings()
    max_bytes = settings.max_media_size_mb * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.max_media_size_mb}MB upload limit",
        )

    media_id = uuid.uuid4().hex
    media = await get_storage().media.put(
        media_id,
        file,
        content_type=file.content_type or "application/octet-stream",
        filename=file.filename,
        uploaded_by=account.username,
    )
    return MediaResponse(**media.model_dump())


@router.get("/{media_id:path}")
async def download_media(
    media_id: str,
    account: AccountInDB = Depends(get_current_active_account),
):
    server_id, local_id = parse_media_id(media_id)
    if server_id is not None:
        return await _proxy_download(server_id, local_id, media_id)

    result = await get_storage().media.get_stream(media_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Media '{media_id}' not found")
    metadata, chunks = result
    return StreamingResponse(
        chunks,
        media_type=metadata.content_type,
        headers={"Content-Disposition": f'inline; filename="{metadata.filename or media_id}"'},
    )


async def _proxy_download(server_id: str, local_id: str, full_media_id: str) -> StreamingResponse:
    """Stream media bytes from the mesh server that owns them.

    Reuses the mesh module's shared HTTP client and the same
    "Authorization: Bearer <api_token>" header every other mesh call already
    sends (hgai_module_mesh.engine._headers) — the receiving server
    authenticates it through its normal get_current_account dependency, so no
    separate media-proxy auth path is needed.
    """
    try:
        from hgai_module_mesh.engine import find_server_by_id, get_http_client, _headers
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mesh module is not available on this server",
        )

    server = await find_server_by_id(server_id)
    if not server:
        raise HTTPException(
            status_code=404,
            detail=f"Mesh server '{server_id}' is not registered in any mesh on this server",
        )

    client = get_http_client()
    remote_url = f"{server.url.rstrip('/')}/api/v1/media/{local_id}"
    try:
        request = client.build_request("GET", remote_url, headers=_headers(server))
        resp = await client.send(request, stream=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach mesh server '{server_id}': {e}",
        )

    if resp.status_code == 404:
        await resp.aclose()
        raise HTTPException(status_code=404, detail=f"Media '{full_media_id}' not found on '{server_id}'")
    if resp.status_code >= 400:
        await resp.aclose()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Mesh server '{server_id}' returned {resp.status_code} for media '{full_media_id}'",
        )

    return StreamingResponse(
        resp.aiter_bytes(),
        media_type=resp.headers.get("content-type", "application/octet-stream"),
        headers={
            "Content-Disposition": resp.headers.get(
                "content-disposition", f'inline; filename="{local_id}"'
            )
        },
        background=BackgroundTask(resp.aclose),
    )


@router.put("/{media_id:path}", response_model=MediaResponse)
async def update_media(
    media_id: str,
    data: MediaUpdate,
    account: AccountInDB = Depends(get_current_active_account),
):
    server_id, local_id = parse_media_id(media_id)
    if server_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update media owned by another mesh server",
        )
    patch = MediaPatch(
        filename=data.filename,
        tags=data.tags,
        attributes=data.attributes,
        status=data.status,
        updated_by=account.username,
    )
    result = await get_storage().media.update(local_id, patch)
    if not result:
        raise HTTPException(status_code=404, detail=f"Media '{media_id}' not found")
    return MediaResponse(**result.model_dump())


_DELETE_STATUS_BY_REASON = {
    "remote": status.HTTP_400_BAD_REQUEST,
    "not_found": status.HTTP_404_NOT_FOUND,
    "referenced": status.HTTP_409_CONFLICT,
}


@router.delete("/{media_id:path}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    media_id: str,
    account: AccountInDB = Depends(get_current_active_account),
):
    deleted, reason, message = await delete_media_checked(media_id)
    if not deleted:
        raise HTTPException(status_code=_DELETE_STATUS_BY_REASON[reason], detail=message)


@router.post("/sweep-orphaned")
async def sweep_orphaned(
    older_than_hours: int = 24,
    _admin: AccountInDB = Depends(require_admin),
):
    """GC safety net: permanently delete media with ref_count == 0 older than
    `older_than_hours` (default 24h grace period). Admin-only."""
    return await sweep_orphaned_media(older_than_hours=older_than_hours)
