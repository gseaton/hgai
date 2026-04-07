"""MongoDB connection and collection accessors."""

import logging
from typing import Optional

import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from hgai.config import get_settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def ensure_indexes() -> None:
    """Create all collection indexes. Safe to call on every startup — idempotent."""

    # ── hypergraphs ───────────────────────────────────────────────────────────
    # Drop the old global unique index if it still exists (idempotent migration).
    try:
        await col_hypergraphs().drop_index("id_unique")
    except Exception:
        pass  # index doesn't exist — safe to continue

    await col_hypergraphs().create_indexes([
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
    await col_hypernodes().create_indexes([
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
    await col_hyperedges().create_indexes([
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
    await col_spaces().create_indexes([
        IndexModel([("id", ASCENDING)], unique=True, name="id_unique"),
        IndexModel([("members.username", ASCENDING)], name="members_username"),
        IndexModel([("status", ASCENDING)], name="status"),
    ])

    # ── meshes ────────────────────────────────────────────────────────────────
    await col_meshes().create_indexes([
        IndexModel([("id", ASCENDING)], unique=True, name="id_unique"),
    ])

    # ── accounts ──────────────────────────────────────────────────────────────
    await col_accounts().create_indexes([
        IndexModel([("username", ASCENDING)], unique=True, name="username_unique"),
    ])

    # ── query_cache ───────────────────────────────────────────────────────────
    await col_query_cache().create_indexes([
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
    await col_audit_log().create_indexes([
        IndexModel([("timestamp", DESCENDING)], name="timestamp_desc"),
    ])

    logger.info("MongoDB indexes ensured")


async def connect_db() -> None:
    global _client, _db
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongo_uri)
    _db = _client[settings.mongo_db]
    # Verify connection
    await _client.admin.command("ping")
    await ensure_indexes()


async def close_db() -> None:
    global _client
    if _client:
        _client.close()
        _client = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _db


# Collection accessors
def col_hypergraphs():
    return get_db()["hypergraphs"]


def col_hypernodes():
    return get_db()["hypernodes"]


def col_hyperedges():
    return get_db()["hyperedges"]


def col_accounts():
    return get_db()["accounts"]


def col_spaces():
    return get_db()["spaces"]


def col_meshes():
    return get_db()["meshes"]


def col_query_cache():
    return get_db()["query_cache"]


def col_audit_log():
    return get_db()["audit_log"]
