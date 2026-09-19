"""Per-account history of submitted AI Agent Chat prompts.

Same pattern as hgai_module_shql/history.py (see docs/module-development.md's
"Custom Module Storage") — a small, account-scoped, non-hypergraph concern
that owns its own plain Mongo collection rather than the pluggable
StorageBackend ABC. Deliberately a flat list of raw prompt text spanning
every session (not scoped to one session/model) — the point is "what did I
recently type into this chat," not a second copy of any one session's
transcript (see hgai_module_agentchat/store.py's AgentChatMessage for that).

Every submitted prompt is recorded regardless of whether the turn that
followed it succeeded — this is a history of what was *submitted*, not of
what got a good answer. Recording is fire-and-forget from the caller's
perspective (see the UI's addToAgentChatHistory()): a chat turn still runs
normally even if history recording itself fails.
"""

import uuid
from typing import Any, Dict, List

from hgai.models.common import now_utc

HISTORY_MAX_PER_ACCOUNT = 50


def _collection():
    from hgai_module_storage_mongodb.connection import get_db
    return get_db()["agent_chat_prompt_history"]


async def add_history_entry(username: str, prompt: str) -> Dict[str, Any]:
    """Record one submitted prompt for `username`, evicting the oldest
    entries beyond `HISTORY_MAX_PER_ACCOUNT`.

    Re-submitting a prompt whose text exactly matches an existing entry for
    the same account replaces it (moves it to the top) rather than adding a
    duplicate — the same de-dup behavior hgai_module_shql's query history
    already established for this app.
    """
    text = (prompt or "").strip()
    doc = {
        "id": uuid.uuid4().hex,
        "username": username,
        "prompt": text,
        "created_at": now_utc(),
    }
    if not text:
        return doc

    coll = _collection()
    await coll.delete_many({"username": username, "prompt": text})
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
    """The account's submitted prompts, newest first."""
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
