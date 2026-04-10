"""Single accessor for the pluggable storage backend.

This module replaces hgai/db/mongodb.py as the central import point for
all storage operations. Callers obtain per-entity stores via get_storage()
and access e.g. get_storage().hypergraphs, get_storage().hypernodes, etc.
"""

from __future__ import annotations

import logging
from typing import Optional

from hgai_module_storage.backend import StorageBackend

logger = logging.getLogger(__name__)

_backend: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """Return the active StorageBackend.

    Raises RuntimeError if init_storage() has not been called yet.
    """
    if _backend is None:
        raise RuntimeError(
            "Storage backend not initialized. Call init_storage() first."
        )
    return _backend


async def init_storage(backend_name: str, **kwargs) -> None:
    """Initialize and connect the storage backend.

    Imports the backend module (triggering self-registration) then
    instantiates and connects the backend.

    Args:
        backend_name: Registered backend name (e.g. "mongodb").
        **kwargs: Keyword arguments forwarded to the backend constructor
                  (e.g. mongo_uri, mongo_db for the MongoDB backend).
    """
    global _backend

    # Import the concrete backend module so it self-registers.
    if backend_name == "mongodb":
        import hgai_module_storage_mongodb  # noqa: F401

    from hgai_module_storage.registry import get_backend_class

    cls = get_backend_class(backend_name)
    _backend = cls(**kwargs)
    await _backend.connect()
    await _backend.ensure_schema()
    logger.info(f"Storage backend '{backend_name}' initialized")


async def close_storage() -> None:
    """Close the storage backend connection."""
    global _backend
    if _backend is not None:
        await _backend.close()
        _backend = None
        logger.info("Storage backend closed")
