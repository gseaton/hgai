"""Note engine: CRUD, sharing, and access-control logic for rich per-account notes.

A Note is a first-class resource (see hgai/models/note.py) — not a hypernode
or hyperedge — so this module, not hgai/core/engine.py, owns its lifecycle.
Follows the same mutations-audit-trail convention hypernodes/hyperedges use,
via the shared `hgai.core.mutations` helpers they were extracted into.
"""

import uuid
from typing import List, Optional, Tuple

from hgai.core.media import adjust_media_refs, apply_media_diff
from hgai.core.mutations import append_mutation as _append_mutation
from hgai.core.mutations import create_delta as _create_delta
from hgai.core.mutations import update_delta as _update_delta
from hgai.db.storage import get_storage
from hgai.models.common import now_utc
from hgai.models.note import NoteCreate, NoteGrant, NoteInDB, NoteRole, NoteUpdate
from hgai_module_storage.filters import NoteFilters, NotePatch

NOTE_TRACKED_FIELDS = ["label", "name", "text", "media", "tags", "status", "attributes"]


def can_view_note(note: NoteInDB, username: str) -> bool:
    """Owner always can; otherwise any ACL entry (viewer or editor) grants view."""
    if note.owner_username == username:
        return True
    return any(grant.username == username for grant in note.acl)


def can_edit_note(note: NoteInDB, username: str) -> bool:
    """Owner always can; otherwise only an ACL entry with role=editor grants edit."""
    if note.owner_username == username:
        return True
    return any(grant.username == username and grant.role == NoteRole.editor for grant in note.acl)


async def create_note(data: NoteCreate, owner_username: str) -> NoteInDB:
    now = now_utc()
    doc = data.model_dump()
    create_delta = _create_delta(doc, NOTE_TRACKED_FIELDS)
    doc.update(
        id=uuid.uuid4().hex,
        owner_username=owner_username,
        acl=[],
        system_created=now,
        system_updated=now,
        created_by=owner_username,
        version=1,
        mutations=_append_mutation([], "create", create_delta, owner_username),
    )
    note = await get_storage().notes.create(doc)
    await adjust_media_refs(data.media, 1)
    return note


async def get_note(note_id: str) -> Optional[NoteInDB]:
    return await get_storage().notes.get(note_id)


async def list_notes_visible_to(
    username: str,
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    sort: Optional[List[Tuple[str, int]]] = None,
) -> Tuple[int, List[NoteInDB]]:
    filters = NoteFilters(username=username, tags=tags, search=search, sort=sort)
    return await get_storage().notes.list(filters, skip=skip, limit=limit)


async def update_note(note_id: str, data: NoteUpdate, updated_by: str) -> Optional[NoteInDB]:
    existing = await get_note(note_id)
    if not existing:
        return None

    dumped = data.model_dump(exclude_none=True)
    existing_dump = existing.model_dump()
    existing_mutations = existing_dump.get("mutations", [])
    update_delta = _update_delta(existing_dump, dumped, NOTE_TRACKED_FIELDS)
    new_mutations = _append_mutation(existing_mutations, "mutate", update_delta, updated_by)

    patch = NotePatch(
        label=dumped.get("label"),
        name=dumped.get("name"),
        text=dumped.get("text"),
        media=dumped.get("media"),
        tags=dumped.get("tags"),
        attributes=dumped.get("attributes"),
        status=dumped.get("status"),
        mutations=new_mutations if new_mutations is not existing_mutations else None,
    )
    result = await get_storage().notes.update(note_id, patch)
    if result and "media" in dumped:
        await apply_media_diff(existing.media, dumped.get("media"))
    return result


async def delete_note(note_id: str) -> bool:
    existing = await get_note(note_id)
    deleted = await get_storage().notes.delete(note_id)
    if deleted and existing:
        await adjust_media_refs(existing.media, -1)
    return deleted


async def share_note(note_id: str, username: str, role: NoteRole, shared_by: str) -> Optional[NoteInDB]:
    """Grant (or change) one account's access level. Idempotent: sharing
    with the same role again produces no new mutation entry (redundant
    sequential mutation, same suppression rule as any other field)."""
    existing = await get_note(note_id)
    if not existing:
        return None

    existing_mutations = existing.model_dump().get("mutations", [])
    new_acl = [g for g in existing.acl if g.username != username]
    new_acl.append(NoteGrant(username=username, role=role))
    old_dump = [g.model_dump() for g in existing.acl]
    new_dump = [g.model_dump() for g in new_acl]
    # Compared as a set of (username, role) pairs, not the raw list, so
    # re-sharing with an unchanged role is correctly seen as a no-op even
    # when the remove-then-append above happens to reorder other entries.
    unchanged = {(g["username"], g["role"]) for g in old_dump} == {(g["username"], g["role"]) for g in new_dump}
    delta = [] if unchanged else [{"field": "acl", "old": old_dump, "new": new_dump}]
    new_mutations = _append_mutation(existing_mutations, "share", delta, shared_by)

    patch = NotePatch(
        acl=new_dump,
        mutations=new_mutations if new_mutations is not existing_mutations else None,
    )
    return await get_storage().notes.update(note_id, patch)


async def unshare_note(note_id: str, username: str, unshared_by: str) -> Optional[NoteInDB]:
    """Revoke one account's access. A no-op (returns the note unchanged,
    still a 2xx from the caller's perspective) if that account had no grant."""
    existing = await get_note(note_id)
    if not existing:
        return None

    new_acl = [g for g in existing.acl if g.username != username]
    if len(new_acl) == len(existing.acl):
        return existing

    old_dump = [g.model_dump() for g in existing.acl]
    new_dump = [g.model_dump() for g in new_acl]
    existing_mutations = existing.model_dump().get("mutations", [])
    new_mutations = _append_mutation(
        existing_mutations, "unshare", [{"field": "acl", "old": old_dump, "new": new_dump}], unshared_by,
    )
    patch = NotePatch(acl=new_dump, mutations=new_mutations)
    return await get_storage().notes.update(note_id, patch)
