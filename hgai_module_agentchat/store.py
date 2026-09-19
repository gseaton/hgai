"""MongoDB persistence for AI Agent vendors/models/chat sessions/messages.

Module-owned collections (agent_vendors, agent_models, agent_chat_sessions,
agent_chat_messages) rather than an extension to the pluggable StorageBackend
ABC — the same trade-off already made for hgai_module_shql's query-history
collection; see docs/module-development.md's "Custom Module Storage"
section. `_db()` is a thin, separately-patchable indirection so tests can
substitute a fake in-memory database without touching the real Mongo
connection (see tests/test_agent_chat.py).
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple

from hgai.core.mutations import append_mutation as _append_mutation
from hgai.core.mutations import create_delta as _create_delta
from hgai.core.mutations import update_delta as _update_delta
from hgai.models.common import now_utc

from .crypto import decrypt_api_key, encrypt_api_key, last4
from .models import (
    AgentChatMessageInDB,
    AgentChatSessionCreate,
    AgentChatSessionInDB,
    AgentModelCreate,
    AgentModelInDB,
    AgentModelUpdate,
    AgentVendorCreate,
    AgentVendorInDB,
    AgentVendorName,
    AgentVendorUpdate,
)

VENDOR_TRACKED_FIELDS = ["name", "label", "base_url", "enabled", "tags", "status", "attributes"]
MODEL_TRACKED_FIELDS = [
    "vendor_id", "model_id", "label", "description",
    "default_temperature", "default_max_tokens", "enabled", "tags", "status", "attributes",
]


def _db():
    from hgai_module_storage_mongodb.connection import get_db
    return get_db()


def _vendors():
    return _db()["agent_vendors"]


def _models():
    return _db()["agent_models"]


def _sessions():
    return _db()["agent_chat_sessions"]


def _messages():
    return _db()["agent_chat_messages"]


def _build_query(
    search_fields: List[str],
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    extra_clauses: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    clauses: List[Dict[str, Any]] = list(extra_clauses or [])
    if status:
        clauses.append({"status": status})
    if tags:
        clauses.append({"tags": {"$all": tags}})
    if search:
        clauses.append({"$or": [{f: {"$regex": search, "$options": "i"}} for f in search_fields]})
    return {"$and": clauses} if clauses else {}


# ─── Vendors ────────────────────────────────────────────────────────────────

async def create_vendor(data: AgentVendorCreate, created_by: str) -> AgentVendorInDB:
    now = now_utc()
    doc = data.model_dump(exclude={"api_key"})
    plaintext_key = data.api_key or ""
    create_delta = _create_delta(doc, VENDOR_TRACKED_FIELDS)
    doc.update(
        id=uuid.uuid4().hex,
        api_key_encrypted=encrypt_api_key(plaintext_key) if plaintext_key else "",
        api_key_last4=last4(plaintext_key) if plaintext_key else "",
        system_created=now,
        system_updated=now,
        created_by=created_by,
        version=1,
        mutations=_append_mutation([], "create", create_delta, created_by),
    )
    await _vendors().insert_one(dict(doc))
    doc.pop("_id", None)
    return AgentVendorInDB(**doc)


async def get_vendor(vendor_id: str) -> Optional[AgentVendorInDB]:
    raw = await _vendors().find_one({"id": vendor_id})
    if not raw:
        return None
    raw.pop("_id", None)
    return AgentVendorInDB(**raw)


async def list_vendors(
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[int, List[AgentVendorInDB]]:
    query = _build_query(["label", "name", "base_url"], tags=tags, search=search, status=status)
    total = await _vendors().count_documents(query)
    cursor = _vendors().find(query).skip(skip).limit(limit).sort([("system_created", -1)])
    docs = await cursor.to_list(length=limit)
    items = []
    for doc in docs:
        doc.pop("_id", None)
        items.append(AgentVendorInDB(**doc))
    return total, items


async def update_vendor(vendor_id: str, data: AgentVendorUpdate, updated_by: str) -> Optional[AgentVendorInDB]:
    existing = await get_vendor(vendor_id)
    if not existing:
        return None

    dumped = data.model_dump(exclude_none=True, exclude={"api_key"})
    existing_dump = existing.model_dump()
    existing_mutations = existing_dump.get("mutations", [])
    update_delta = _update_delta(existing_dump, dumped, VENDOR_TRACKED_FIELDS)
    new_mutations = _append_mutation(existing_mutations, "mutate", update_delta, updated_by)

    update_fields: Dict[str, Any] = dict(dumped)
    if data.api_key:
        update_fields["api_key_encrypted"] = encrypt_api_key(data.api_key)
        update_fields["api_key_last4"] = last4(data.api_key)
    update_fields["system_updated"] = now_utc()
    if new_mutations is not existing_mutations:
        update_fields["mutations"] = new_mutations

    result = await _vendors().find_one_and_update(
        {"id": vendor_id},
        {"$set": update_fields, "$inc": {"version": 1}},
        return_document=True,
    )
    if not result:
        return None
    result.pop("_id", None)
    return AgentVendorInDB(**result)


async def delete_vendor(vendor_id: str) -> bool:
    result = await _vendors().delete_one({"id": vendor_id})
    return result.deleted_count > 0


async def get_decrypted_api_key(vendor_id: str) -> Optional[str]:
    """Internal-only accessor for the agent engine (Phase 2) — never exposed
    via the API. Returns the plaintext key, or None if the vendor doesn't
    exist or has no key configured."""
    vendor = await get_vendor(vendor_id)
    if not vendor or not vendor.api_key_encrypted:
        return None
    return decrypt_api_key(vendor.api_key_encrypted)


# ─── Models ─────────────────────────────────────────────────────────────────

async def create_model(data: AgentModelCreate, created_by: str) -> AgentModelInDB:
    now = now_utc()
    doc = data.model_dump()
    create_delta = _create_delta(doc, MODEL_TRACKED_FIELDS)
    doc.update(
        id=uuid.uuid4().hex,
        system_created=now,
        system_updated=now,
        created_by=created_by,
        version=1,
        mutations=_append_mutation([], "create", create_delta, created_by),
    )
    await _models().insert_one(dict(doc))
    doc.pop("_id", None)
    return AgentModelInDB(**doc)


async def get_model(model_id: str) -> Optional[AgentModelInDB]:
    raw = await _models().find_one({"id": model_id})
    if not raw:
        return None
    raw.pop("_id", None)
    return AgentModelInDB(**raw)


async def list_models(
    vendor_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    enabled_only: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[int, List[AgentModelInDB]]:
    extra: List[Dict[str, Any]] = []
    if vendor_id:
        extra.append({"vendor_id": vendor_id})
    if enabled_only:
        extra.append({"enabled": True})
    query = _build_query(["label", "model_id", "description"], tags=tags, search=search, status=status, extra_clauses=extra)
    total = await _models().count_documents(query)
    cursor = _models().find(query).skip(skip).limit(limit).sort([("system_created", -1)])
    docs = await cursor.to_list(length=limit)
    items = []
    for doc in docs:
        doc.pop("_id", None)
        items.append(AgentModelInDB(**doc))
    return total, items


async def update_model(model_id: str, data: AgentModelUpdate, updated_by: str) -> Optional[AgentModelInDB]:
    existing = await get_model(model_id)
    if not existing:
        return None

    dumped = data.model_dump(exclude_none=True)
    existing_dump = existing.model_dump()
    existing_mutations = existing_dump.get("mutations", [])
    update_delta = _update_delta(existing_dump, dumped, MODEL_TRACKED_FIELDS)
    new_mutations = _append_mutation(existing_mutations, "mutate", update_delta, updated_by)

    update_fields: Dict[str, Any] = dict(dumped)
    update_fields["system_updated"] = now_utc()
    if new_mutations is not existing_mutations:
        update_fields["mutations"] = new_mutations

    result = await _models().find_one_and_update(
        {"id": model_id},
        {"$set": update_fields, "$inc": {"version": 1}},
        return_document=True,
    )
    if not result:
        return None
    result.pop("_id", None)
    return AgentModelInDB(**result)


async def delete_model(model_id: str) -> bool:
    result = await _models().delete_one({"id": model_id})
    return result.deleted_count > 0


# ─── Chat sessions ──────────────────────────────────────────────────────────

async def create_session(data: AgentChatSessionCreate, owner_username: str) -> AgentChatSessionInDB:
    now = now_utc()
    doc = {
        "id": uuid.uuid4().hex,
        "owner_username": owner_username,
        "title": data.title or "",
        "model_id": data.model_id,
        "last_message_at": None,
        "message_count": 0,
        "status": "active",
        "system_created": now,
        "system_updated": now,
    }
    await _sessions().insert_one(dict(doc))
    doc.pop("_id", None)
    return AgentChatSessionInDB(**doc)


async def get_session(session_id: str) -> Optional[AgentChatSessionInDB]:
    raw = await _sessions().find_one({"id": session_id})
    if not raw:
        return None
    raw.pop("_id", None)
    return AgentChatSessionInDB(**raw)


async def list_sessions(owner_username: str, skip: int = 0, limit: int = 50) -> Tuple[int, List[AgentChatSessionInDB]]:
    query = {"owner_username": owner_username}
    total = await _sessions().count_documents(query)
    # Most-recently-active first; a session with no messages yet (last_message_at
    # is None) sorts after every active one, then falls back to creation time.
    cursor = _sessions().find(query).skip(skip).limit(limit).sort(
        [("last_message_at", -1), ("system_created", -1)]
    )
    docs = await cursor.to_list(length=limit)
    items = []
    for d in docs:
        d.pop("_id", None)
        items.append(AgentChatSessionInDB(**d))
    return total, items


async def update_session_title(session_id: str, title: str) -> Optional[AgentChatSessionInDB]:
    result = await _sessions().find_one_and_update(
        {"id": session_id},
        {"$set": {"title": title, "system_updated": now_utc()}},
        return_document=True,
    )
    if not result:
        return None
    result.pop("_id", None)
    return AgentChatSessionInDB(**result)


async def touch_session(session_id: str) -> None:
    """Bump `message_count` and `last_message_at` after a turn completes."""
    await _sessions().find_one_and_update(
        {"id": session_id},
        {"$set": {"last_message_at": now_utc(), "system_updated": now_utc()}, "$inc": {"message_count": 1}},
        return_document=True,
    )


async def delete_session(session_id: str) -> bool:
    await _messages().delete_many({"session_id": session_id})
    result = await _sessions().delete_one({"id": session_id})
    return result.deleted_count > 0


# ─── Chat messages ──────────────────────────────────────────────────────────

async def create_message(**fields: Any) -> AgentChatMessageInDB:
    doc: Dict[str, Any] = dict(fields)
    doc["id"] = uuid.uuid4().hex
    doc.setdefault("created_at", now_utc())
    await _messages().insert_one(dict(doc))
    doc.pop("_id", None)
    return AgentChatMessageInDB(**doc)


async def get_message(message_id: str) -> Optional[AgentChatMessageInDB]:
    raw = await _messages().find_one({"id": message_id})
    if not raw:
        return None
    raw.pop("_id", None)
    return AgentChatMessageInDB(**raw)


async def list_messages(session_id: str, skip: int = 0, limit: int = 200) -> List[AgentChatMessageInDB]:
    cursor = _messages().find({"session_id": session_id}).skip(skip).limit(limit).sort([("created_at", 1)])
    docs = await cursor.to_list(length=limit)
    items = []
    for d in docs:
        d.pop("_id", None)
        items.append(AgentChatMessageInDB(**d))
    return items


# ─── Default catalog seeding ────────────────────────────────────────────────

# (vendor_name, vendor_label, [(model_id, model_label, description), ...])
_DEFAULT_CATALOG = [
    (AgentVendorName.anthropic, "Anthropic", [
        ("claude-opus-5", "Claude Opus 5", "Anthropic's most capable model"),
        ("claude-sonnet-5", "Claude Sonnet 5", "Balanced speed and capability"),
    ]),
    (AgentVendorName.openai, "OpenAI", [
        ("gpt-5", "GPT-5", "OpenAI's flagship model"),
    ]),
    (AgentVendorName.xai, "xAI", [
        ("grok-4", "Grok 4", "xAI's flagship model"),
    ]),
]


async def seed_defaults() -> None:
    """Idempotently seed a small default vendor/model catalog on first run —
    every seeded vendor starts with no key and `enabled=False`, so the chat
    panel's model picker isn't empty on a fresh install, but nothing is
    actually callable until an admin adds a real key via the UI.

    Safe to call on every startup: it only inserts a vendor for a `name`
    that doesn't already exist, so an admin's own edits — including
    deleting a seeded row entirely — are never overwritten or resurrected.
    """
    for vendor_name, vendor_label, models in _DEFAULT_CATALOG:
        existing = await _vendors().find_one({"name": vendor_name.value})
        if existing:
            continue
        vendor = await create_vendor(
            AgentVendorCreate(name=vendor_name, label=vendor_label, enabled=False),
            created_by="system",
        )
        for model_id, label, description in models:
            await create_model(
                AgentModelCreate(
                    vendor_id=vendor.id,
                    model_id=model_id,
                    label=label,
                    description=description,
                    enabled=False,
                ),
                created_by="system",
            )
