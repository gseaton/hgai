"""MongoDB index definitions for all HypergraphAI collections."""

import logging

from pymongo import ASCENDING, DESCENDING, IndexModel

from .connection import get_db

logger = logging.getLogger(__name__)


async def ensure_indexes() -> None:
    """Create all collection indexes. Safe to call on every startup — idempotent."""
    db = get_db()

    # ── hypergraphs ───────────────────────────────────────────────────────────
    # Drop the old global unique index if it still exists (idempotent migration).
    try:
        await db["hypergraphs"].drop_index("id_unique")
    except Exception:
        pass  # index doesn't exist — safe to continue

    await db["hypergraphs"].create_indexes([
        # Unowned graphs (space_id is null): id must be globally unique.
        IndexModel(
            [("id", ASCENDING)],
            unique=True,
            name="id_unowned_unique",
            partialFilterExpression={"space_id": {"$eq": None}},
        ),
        # Space-owned graphs: (id, space_id) pair must be unique.
        IndexModel(
            [("id", ASCENDING), ("space_id", ASCENDING)],
            unique=True,
            name="id_space_unique",
            partialFilterExpression={"space_id": {"$exists": True, "$type": "string"}},
        ),
        IndexModel([("status", ASCENDING)], name="status"),
        IndexModel([("space_id", ASCENDING)], name="space_id", sparse=True),
        # Tenant lookups. Deliberately NOT unique yet: unowned-graph lookups are
        # not tenant-aware until multi-tenancy Phase 3, so `id_unowned_unique`
        # above stays globally unique until then (then swapped for a unique
        # (tenant_id, id)).
        IndexModel([("tenant_id", ASCENDING), ("id", ASCENDING)], name="tenant_id_id"),
    ])

    # ── hypernodes ────────────────────────────────────────────────────────────
    await db["hypernodes"].create_indexes([
        IndexModel(
            [("id", ASCENDING), ("hypergraph_id", ASCENDING)],
            unique=True, name="id_graph_unique",
        ),
        IndexModel(
            [("hypergraph_id", ASCENDING), ("status", ASCENDING)],
            name="graph_status",
        ),
        IndexModel(
            [("hypergraph_id", ASCENDING), ("type", ASCENDING)],
            name="graph_type",
        ),
        IndexModel([("tags", ASCENDING)], name="tags"),
        IndexModel([("label", ASCENDING)], name="label"),
        IndexModel(
            [("hypergraph_id", ASCENDING), ("valid_from", ASCENDING), ("valid_to", ASCENDING)],
            name="graph_pit",
            sparse=True,
        ),
    ])

    # ── hyperedges ────────────────────────────────────────────────────────────
    await db["hyperedges"].create_indexes([
        IndexModel(
            [("id", ASCENDING), ("hypergraph_id", ASCENDING)],
            unique=True, name="id_graph_unique",
        ),
        IndexModel(
            [("hyperkey", ASCENDING), ("hypergraph_id", ASCENDING)],
            unique=True, name="hyperkey_graph_unique",
        ),
        IndexModel(
            [("hypergraph_id", ASCENDING), ("status", ASCENDING)],
            name="graph_status",
        ),
        IndexModel(
            [("hypergraph_id", ASCENDING), ("relation", ASCENDING)],
            name="graph_relation",
        ),
        IndexModel([("members.node_id", ASCENDING)], name="members_node_id"),
        IndexModel(
            [("hypergraph_id", ASCENDING), ("valid_from", ASCENDING), ("valid_to", ASCENDING)],
            name="graph_pit",
            sparse=True,
        ),
    ])

    # ── spaces ────────────────────────────────────────────────────────────────
    await db["spaces"].create_indexes([
        IndexModel([("id", ASCENDING)], unique=True, name="id_unique"),
        IndexModel([("members.username", ASCENDING)], name="members_username"),
        IndexModel([("status", ASCENDING)], name="status"),
        IndexModel([("tenant_id", ASCENDING)], name="tenant_id"),
    ])

    # ── api_keys ──────────────────────────────────────────────────────────────
    await db["api_keys"].create_indexes([
        IndexModel([("id", ASCENDING)], unique=True, name="id_unique"),
        IndexModel([("key_hash", ASCENDING)], unique=True, name="key_hash_unique"),
        IndexModel([("tenant_id", ASCENDING)], name="tenant_id"),
    ])

    # ── tenants ───────────────────────────────────────────────────────────────
    await db["tenants"].create_indexes([
        IndexModel([("id", ASCENDING)], unique=True, name="id_unique"),
        IndexModel([("status", ASCENDING)], name="status"),
    ])

    # ── meshes ────────────────────────────────────────────────────────────────
    await db["meshes"].create_indexes([
        IndexModel([("id", ASCENDING)], unique=True, name="id_unique"),
    ])

    # ── accounts ──────────────────────────────────────────────────────────────
    await db["accounts"].create_indexes([
        IndexModel([("username", ASCENDING)], unique=True, name="username_unique"),
        IndexModel([("tenant_id", ASCENDING)], name="tenant_id"),
    ])

    # ── query_cache ───────────────────────────────────────────────────────────
    await db["query_cache"].create_indexes([
        IndexModel([("cache_key", ASCENDING)], unique=True, name="cache_key_unique"),
        # Multikey index on graph_ids array — enables graph-scoped invalidation
        IndexModel([("graph_ids", ASCENDING)], name="graph_ids"),
        # TTL index: MongoDB automatically removes expired documents
        IndexModel(
            [("expires_at", ASCENDING)],
            expireAfterSeconds=0,
            name="expires_at_ttl",
        ),
    ])

    # ── media ─────────────────────────────────────────────────────────────────
    await db["media"].create_indexes([
        IndexModel([("tenant_id", ASCENDING)], name="tenant_id"),
        IndexModel([("id", ASCENDING)], unique=True, name="id_unique"),
        IndexModel([("checksum", ASCENDING)], name="checksum"),
    ])

    # ── audit_log ─────────────────────────────────────────────────────────────
    await db["audit_log"].create_indexes([
        IndexModel([("timestamp", DESCENDING)], name="timestamp_desc"),
    ])

    # ── notes ─────────────────────────────────────────────────────────────────
    await db["notes"].create_indexes([
        IndexModel([("id", ASCENDING)], unique=True, name="id_unique"),
        IndexModel([("owner_username", ASCENDING)], name="owner_username"),
        IndexModel([("acl.username", ASCENDING)], name="acl_username"),
        IndexModel([("scope", ASCENDING)], name="scope"),
        IndexModel([("tenant_id", ASCENDING)], name="tenant_id"),
        IndexModel([("tags", ASCENDING)], name="tags"),
    ])

    # ── parameterized_queries ────────────────────────────────────────────────
    await db["parameterized_queries"].create_indexes([
        IndexModel([("id", ASCENDING)], unique=True, name="id_unique"),
        IndexModel([("tags", ASCENDING)], name="tags"),
        IndexModel([("name", ASCENDING)], name="name"),
        IndexModel([("tenant_id", ASCENDING)], name="tenant_id"),
    ])

    # ── shql_query_history ───────────────────────────────────────────────────
    # See hgai_module_shql/history.py — module-owned collection (not part of
    # the pluggable storage-backend abstraction), same pattern as query_cache.
    await db["shql_query_history"].create_indexes([
        IndexModel([("id", ASCENDING)], unique=True, name="id_unique"),
        IndexModel([("username", ASCENDING), ("created_at", DESCENDING)], name="username_created_at"),
    ])

    logger.info("MongoDB indexes ensured")
