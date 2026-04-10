"""MongoDB AsyncIOMotorClient lifecycle management."""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

import logging

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect(mongo_uri: str, mongo_db: str) -> AsyncIOMotorDatabase:
    """Create and verify the Motor client, return the database handle."""
    global _client, _db
    _client = AsyncIOMotorClient(mongo_uri)
    _db = _client[mongo_db]
    await _client.admin.command("ping")
    logger.info(f"Connected to MongoDB: {mongo_db}")
    return _db


async def close() -> None:
    """Close the Motor client."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")


def get_db() -> AsyncIOMotorDatabase:
    """Return the active database handle, raising if not connected."""
    if _db is None:
        raise RuntimeError("MongoDB not connected. Call connect() first.")
    return _db
