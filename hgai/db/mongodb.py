"""MongoDB connection and collection accessors."""

from typing import Optional

import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from hgai.config import get_settings

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_db() -> None:
    global _client, _db
    settings = get_settings()
    _client = AsyncIOMotorClient(settings.mongo_uri)
    _db = _client[settings.mongo_db]
    # Verify connection
    await _client.admin.command("ping")


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


def col_meshes():
    return get_db()["meshes"]


def col_query_cache():
    return get_db()["query_cache"]


def col_audit_log():
    return get_db()["audit_log"]
