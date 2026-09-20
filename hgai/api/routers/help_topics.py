"""Help topic API: the built-in `docs/help` topics plus any `system:help`-tagged
Notes visible to the caller (see hgai.core.help).

Read-only — help files are edited on disk, and note-backed topics are edited
through the ordinary Notes API. Every route just requires authentication;
note-backed topics are additionally filtered by the Note's own owner/ACL.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from hgai.api.deps import get_current_active_account, parse_sort_param
from hgai.core import help as help_core
from hgai.models.account import AccountInDB
from hgai.models.common import PaginatedResponse

router = APIRouter(prefix="/help", tags=["help"])

HELP_SORT_FIELDS = {"label", "name", "system_updated", "source"}


@router.get("/topics", response_model=PaginatedResponse)
async def list_help_topics_route(
    tags: Optional[List[str]] = Query(default=None, description="Topic must carry every listed tag"),
    search: Optional[str] = Query(default=None, description="Every word must appear in the id, label, name, description, tags, or text"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    sort: Optional[str] = Query(default=None, description=f"Comma-separated fields, '-' prefix = descending. Allowed: {sorted(HELP_SORT_FIELDS)}"),
    account: AccountInDB = Depends(get_current_active_account),
):
    total, items = await help_core.list_topics(
        account.username, search=search, tags=tags, skip=skip, limit=limit,
        sort=parse_sort_param(sort, HELP_SORT_FIELDS),
    )
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=items)


@router.get("/home")
async def get_help_home_route(account: AccountInDB = Depends(get_current_active_account)):
    topic = await help_core.get_home_topic(account.username)
    if not topic:
        raise HTTPException(status_code=404, detail="No home help topic is installed (expected notes/home.md)")
    return topic


@router.get("/topics/{topic_id}")
async def get_help_topic_route(topic_id: str, account: AccountInDB = Depends(get_current_active_account)):
    topic = await help_core.get_topic(account.username, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Help topic '{topic_id}' not found")
    return topic


@router.get("/media")
async def list_help_media_route(account: AccountInDB = Depends(get_current_active_account)):
    return {"items": help_core.list_media()}


@router.get("/media/{media_path:path}")
async def get_help_media_route(media_path: str, account: AccountInDB = Depends(get_current_active_account)):
    path = help_core.resolve_media_path(media_path)
    if not path:
        raise HTTPException(status_code=404, detail=f"Help media '{media_path}' not found")
    # The headers keep a served SVG/HTML file from running scripts or being
    # sniffed into another type if someone opens the URL directly.
    return FileResponse(
        path,
        headers={
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
            "X-Content-Type-Options": "nosniff",
        },
    )
