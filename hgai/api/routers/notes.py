"""Note CRUD + sharing API endpoints.

Every route requires authentication (`get_current_active_account`) but has
no path-based scoping the way graph-nested resources do — a note's
visibility is entirely a function of `owner_username`/`acl`, checked here
against the calling account rather than via a path-injected graph_id/space_id.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hgai.api.deps import get_current_active_account, parse_sort_param
from hgai.core.notes import (
    can_edit_note,
    can_view_note,
    create_note,
    delete_note,
    get_note,
    list_notes_visible_to,
    share_note,
    unshare_note,
    update_note,
)
from hgai.models.account import AccountInDB
from hgai.models.common import PaginatedResponse
from hgai.models.note import NoteCreate, NoteResponse, NoteUpdate, ShareNoteRequest

router = APIRouter(prefix="/notes", tags=["notes"])

NOTE_SORT_FIELDS = {"label", "name", "owner_username", "status", "system_created", "system_updated"}


def _is_admin(account: AccountInDB) -> bool:
    return "admin" in account.roles


async def _get_viewable(note_id: str, account: AccountInDB):
    note = await get_note(note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note '{note_id}' not found")
    if not _is_admin(account) and not can_view_note(note, account.username):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access to note '{note_id}' not permitted")
    return note


async def _get_editable(note_id: str, account: AccountInDB):
    note = await _get_viewable(note_id, account)
    if not _is_admin(account) and not can_edit_note(note, account.username):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Edit access to note '{note_id}' not permitted")
    return note


@router.get("", response_model=PaginatedResponse)
async def list_notes(
    tags: Optional[List[str]] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Substring match against label or text"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    sort: Optional[str] = Query(default=None, description=f"Comma-separated fields, '-' prefix = descending. Allowed: {sorted(NOTE_SORT_FIELDS)}"),
    account: AccountInDB = Depends(get_current_active_account),
):
    """Notes visible to the calling account: owned, or shared with them.
    An admin still only sees their own + shared notes here — use a direct
    GET /notes/{id} (also admin-bypassed) to reach any specific note."""
    total, notes = await list_notes_visible_to(
        account.username, tags=tags, search=search, skip=skip, limit=limit,
        sort=parse_sort_param(sort, NOTE_SORT_FIELDS),
    )
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=[n.model_dump() for n in notes])


@router.post("", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note_route(
    data: NoteCreate,
    account: AccountInDB = Depends(get_current_active_account),
):
    return await create_note(data, account.username)


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note_route(
    note_id: str,
    account: AccountInDB = Depends(get_current_active_account),
):
    return await _get_viewable(note_id, account)


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note_route(
    note_id: str,
    data: NoteUpdate,
    account: AccountInDB = Depends(get_current_active_account),
):
    await _get_editable(note_id, account)
    result = await update_note(note_id, data, account.username)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note '{note_id}' not found")
    return result


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note_route(
    note_id: str,
    account: AccountInDB = Depends(get_current_active_account),
):
    note = await _get_viewable(note_id, account)
    if not _is_admin(account) and note.owner_username != account.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can delete a note")
    await delete_note(note_id)


@router.get("/{note_id}/share")
async def list_note_shares(
    note_id: str,
    account: AccountInDB = Depends(get_current_active_account),
):
    note = await _get_viewable(note_id, account)
    return {"owner_username": note.owner_username, "acl": [g.model_dump() for g in note.acl]}


@router.post("/{note_id}/share", response_model=NoteResponse)
async def share_note_route(
    note_id: str,
    data: ShareNoteRequest,
    account: AccountInDB = Depends(get_current_active_account),
):
    note = await _get_viewable(note_id, account)
    if not _is_admin(account) and note.owner_username != account.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can change sharing")
    if data.username == note.owner_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Note owner already has full access")
    result = await share_note(note_id, data.username, data.role, account.username)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note '{note_id}' not found")
    return result


@router.delete("/{note_id}/share/{username}", response_model=NoteResponse)
async def unshare_note_route(
    note_id: str,
    username: str,
    account: AccountInDB = Depends(get_current_active_account),
):
    note = await _get_viewable(note_id, account)
    if not _is_admin(account) and note.owner_username != account.username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the owner can change sharing")
    result = await unshare_note(note_id, username, account.username)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note '{note_id}' not found")
    return result
