"""hgai_module_storage_mongodb — MongoDB storage backend for HypergraphAI.

Importing this module registers the "mongodb" backend in the storage registry.
"""

from hgai_module_storage.registry import register_backend

from .backend import MongoStorageBackend

register_backend("mongodb", MongoStorageBackend)

__all__ = ["MongoStorageBackend"]
