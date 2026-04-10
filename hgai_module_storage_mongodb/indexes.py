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
    ])

    # ── meshes ────────────────────────────────────────────────────────────────
    await db["meshes"].create_indexes([
        IndexModel([("id", ASCENDING)], unique=True, name="id_unique"),
    ])

    # ── accounts ──────────────────────────────────────────────────────────────
    await db["accounts"].create_indexes([
        IndexModel([("username", ASCENDING)], unique=True, name="username_unique"),
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

    # ── audit_log ─────────────────────────────────────────────────────────────
    await db["audit_log"].create_indexes([
        IndexModel([("timestamp", DESCENDING)], name="timestamp_desc"),
    ])

    logger.info("MongoDB indexes ensured")
