"""Per-account SHQL query submission history.

Follows docs/module-development.md's "Custom Module Storage" pattern: this
is a small, module-specific concern (not a hypergraph entity, not shared
across modules), so it owns a plain MongoDB collection directly via
`hgai_module_storage_mongodb.connection.get_db()` rather than going through
the pluggable storage-backend abstraction in `hgai_module_storage` — the
same trade-off already made for `hgai.core.cache`'s `query_cache`
collection.

Every submitted query (successful or not — this is a history of what was
*run*, not of what succeeded) is recorded per account, capped at the 50
most recent per account. Recording is fire-and-forget from the caller's
perspective: a query still executes and returns normally even if history
recording itself fails (see the try/except in the SHQL router).
"""

import uuid
from typing import Any, Dict, List

from hgai.models.common import now_utc

HISTORY_MAX_PER_ACCOUNT = 50


def _collection():
    from hgai_module_storage_mongodb.connection import get_db
    return get_db()["shql_query_history"]


async def add_history_entry(username: str, shql: str) -> Dict[str, Any]:
    """Record one submitted query for `username`, evicting the oldest
    entries beyond `HISTORY_MAX_PER_ACCOUNT`.

    Re-submitting a query whose text exactly matches an existing entry for
    the same account replaces it (moves it to the top) rather than adding a
    duplicate — the same de-dup behavior the original client-side
    (localStorage) implementation had, now preserved server-side.
    """
    text = (shql or "").strip()
    doc = {
        "id": uuid.uuid4().hex,
        "username": username,
        "shql": text,
        "created_at": now_utc(),
    }
    if not text:
        return doc

    coll = _collection()
    await coll.delete_many({"username": username, "shql": text})
    await coll.insert_one(dict(doc))

    stale_ids = [
        d["_id"] async for d in coll.find(
            {"username": username},
            sort=[("created_at", -1)],
            skip=HISTORY_MAX_PER_ACCOUNT,
            projection={"_id": 1},
        )
    ]
    if stale_ids:
        await coll.delete_many({"_id": {"$in": stale_ids}})

    doc.pop("_id", None)
    return doc


async def list_history(username: str, limit: int = HISTORY_MAX_PER_ACCOUNT) -> List[Dict[str, Any]]:
    """The account's submitted queries, newest first."""
    coll = _collection()
    cursor = coll.find(
        {"username": username},
        sort=[("created_at", -1)],
        limit=limit,
        projection={"_id": 0},
    )
    return [doc async for doc in cursor]


async def clear_history(username: str) -> int:
    """Delete all of the account's history entries. Returns the count removed."""
    result = await _collection().delete_many({"username": username})
    return result.deleted_count
