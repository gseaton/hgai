"""Startup migration that stamps pre-multi-tenancy records with a tenant.

Idempotent: only documents with no `tenant_id` field are touched, so running it
on every boot changes nothing after the first run. An explicit null `tenant_id`
means "system level" and is never revisited.
"""

import logging
from typing import Dict

from .connection import get_db

logger = logging.getLogger(__name__)

_MISSING = {"$exists": False}

# (collection, field naming the record's owning account)
_OWNED = (
    ("notes", "owner_username"),
    ("parameterized_queries", "created_by"),
    ("media", "created_by"),
    ("shql_query_history", "username"),
    ("agent_chat_sessions", "owner_username"),
)


async def migrate_tenancy(default_tenant_id: str, system_graph_ids: frozenset) -> Dict[str, int]:
    db = get_db()
    counts: Dict[str, int] = {}

    # Accounts: the legacy global `admin` role is the system admin and belongs to no tenant.
    r = await db["accounts"].update_many(
        {"roles": "admin", "system_role": _MISSING}, {"$set": {"system_role": "system_admin"}}
    )
    counts["accounts_system_admin"] = r.modified_count
    r = await db["accounts"].update_many(
        {"tenant_id": _MISSING, "system_role": _MISSING}, {"$set": {"tenant_id": default_tenant_id}}
    )
    counts["accounts"] = r.modified_count

    system_users = [
        a["username"] async for a in db["accounts"].find({"system_role": {"$ne": None, "$exists": True}}, {"username": 1})
    ]

    r = await db["spaces"].update_many({"tenant_id": _MISSING}, {"$set": {"tenant_id": default_tenant_id}})
    counts["spaces"] = r.modified_count

    # Graphs: a space graph takes its space's tenant; unowned graphs go to the
    # default tenant, except system graphs, which stay tenantless (explicit null).
    graphs = 0
    space_ids = await db["hypergraphs"].distinct("space_id", {"tenant_id": _MISSING, "space_id": {"$type": "string"}})
    for sid in space_ids:
        space = await db["spaces"].find_one({"id": sid}, {"tenant_id": 1})
        tenant = (space or {}).get("tenant_id", default_tenant_id)
        r = await db["hypergraphs"].update_many(
            {"tenant_id": _MISSING, "space_id": sid}, {"$set": {"tenant_id": tenant}}
        )
        graphs += r.modified_count
    if system_graph_ids:
        r = await db["hypergraphs"].update_many(
            {"tenant_id": _MISSING, "space_id": None, "id": {"$in": sorted(system_graph_ids)}},
            {"$set": {"tenant_id": None}},
        )
        graphs += r.modified_count
    r = await db["hypergraphs"].update_many({"tenant_id": _MISSING}, {"$set": {"tenant_id": default_tenant_id}})
    counts["hypergraphs"] = graphs + r.modified_count

    # Owner-scoped data follows its owner: a system account's data is system level.
    for collection, owner_field in _OWNED:
        col = db[collection]
        changed = 0
        if system_users:
            r = await col.update_many(
                {"tenant_id": _MISSING, owner_field: {"$in": system_users}}, {"$set": {"tenant_id": None}}
            )
            changed += r.modified_count
        r = await col.update_many({"tenant_id": _MISSING}, {"$set": {"tenant_id": default_tenant_id}})
        counts[collection] = changed + r.modified_count

    changed = {k: v for k, v in counts.items() if v}
    if changed:
        logger.info(f"Tenancy migration stamped records: {changed}")
    return counts
