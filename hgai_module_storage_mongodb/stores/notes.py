"""MongoDB note store implementation."""

from typing import Any, Dict, List, Optional, Tuple

from hgai.models.note import NoteInDB
from hgai_module_storage.backend import NoteStore
from hgai_module_storage.filters import NoteFilters, NotePatch

from ..connection import get_db


def _col():
    return get_db()["notes"]


def _visibility_clause(username: str) -> Dict[str, Any]:
    """A note is visible to `username` iff they own it or appear in its acl —
    matches `hgai.core.notes.can_view_note`'s definition of visibility, kept
    in sync deliberately since this is the query-side equivalent."""
    return {"$or": [{"owner_username": username}, {"acl.username": username}]}


class MongoNoteStore(NoteStore):

    async def create(self, doc: Dict[str, Any]) -> NoteInDB:
        await _col().insert_one(doc)
        doc.pop("_id", None)
        return NoteInDB(**doc)

    async def get(self, note_id: str) -> Optional[NoteInDB]:
        raw = await _col().find_one({"id": note_id})
        if not raw:
            return None
        raw.pop("_id", None)
        return NoteInDB(**raw)

    async def list(
        self,
        filters: NoteFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[NoteInDB]]:
        # Built as an explicit $and of clauses, not merged dict keys — the
        # visibility check and the search check each need their own $or,
        # and a plain dict can only ever hold one top-level "$or" key.
        clauses: List[Dict[str, Any]] = []
        if filters.username:
            clauses.append(_visibility_clause(filters.username))
        if filters.status:
            clauses.append({"status": filters.status})
        if filters.tags:
            clauses.append({"tags": {"$all": filters.tags}})
        if filters.search:
            clauses.append({"$or": [
                {"label": {"$regex": filters.search, "$options": "i"}},
                {"name": {"$regex": filters.search, "$options": "i"}},
                {"text": {"$regex": filters.search, "$options": "i"}},
            ]})
        query: Dict[str, Any] = {"$and": clauses} if clauses else {}

        total = await _col().count_documents(query)
        sort_spec = filters.sort or [("system_created", -1)]
        cursor = _col().find(query).skip(skip).limit(limit).sort(sort_spec)
        docs = await cursor.to_list(length=limit)
        notes = []
        for doc in docs:
            doc.pop("_id", None)
            notes.append(NoteInDB(**doc))
        return total, notes

    async def update(self, note_id: str, patch: NotePatch) -> Optional[NoteInDB]:
        from hgai.models.common import now_utc
        update_fields: Dict[str, Any] = {}
        for attr in ("label", "name", "text", "media", "tags", "attributes", "status", "acl", "mutations"):
            val = getattr(patch, attr, None)
            if val is not None:
                update_fields[attr] = val
        update_fields["system_updated"] = now_utc()

        result = await _col().find_one_and_update(
            {"id": note_id},
            {"$set": update_fields, "$inc": {"version": 1}},
            return_document=True,
        )
        if not result:
            return None
        result.pop("_id", None)
        return NoteInDB(**result)

    async def delete(self, note_id: str) -> bool:
        result = await _col().delete_one({"id": note_id})
        return result.deleted_count > 0
