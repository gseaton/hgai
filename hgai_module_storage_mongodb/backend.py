"""MongoDB StorageBackend implementation."""

import logging

from hgai.config import get_settings
from hgai_module_storage.backend import MediaStore, StorageBackend

from . import connection, indexes
from .stores.accounts import MongoAccountStore
from .stores.cache import MongoCacheStore
from .stores.hyperedges import MongoHyperedgeStore
from .stores.hypergraphs import MongoHypergraphStore
from .stores.hypernodes import MongoHypernodeStore
from .stores.media import MongoMediaStore
from .stores.meshes import MongoMeshStore
from .stores.spaces import MongoSpaceStore

logger = logging.getLogger(__name__)


class MongoStorageBackend(StorageBackend):
    """MongoDB-backed StorageBackend."""

    def __init__(self, mongo_uri: str, mongo_db: str) -> None:
        self._mongo_uri = mongo_uri
        self._mongo_db = mongo_db

        self._hypergraphs = MongoHypergraphStore()
        self._hypernodes = MongoHypernodeStore()
        self._hyperedges = MongoHyperedgeStore()
        self._accounts = MongoAccountStore()
        self._spaces = MongoSpaceStore()
        self._meshes = MongoMeshStore()
        self._cache = MongoCacheStore()

        # Media blob backend is independently config-toggled (HGAI_MEDIA_BACKEND)
        # from the primary storage_backend — metadata always stays in this same
        # Mongo instance either way; only where the bytes live changes.
        if get_settings().media_backend == "s3":
            from .stores.media_s3 import S3MediaStore
            self._media = S3MediaStore()
        else:
            self._media = MongoMediaStore()

    async def connect(self) -> None:
        await connection.connect(self._mongo_uri, self._mongo_db)
        logger.info(f"MongoStorageBackend connected to {self._mongo_db}")

    async def close(self) -> None:
        await connection.close()

    async def ensure_schema(self) -> None:
        await indexes.ensure_indexes()

    @property
    def hypergraphs(self) -> MongoHypergraphStore:
        return self._hypergraphs

    @property
    def hypernodes(self) -> MongoHypernodeStore:
        return self._hypernodes

    @property
    def hyperedges(self) -> MongoHyperedgeStore:
        return self._hyperedges

    @property
    def accounts(self) -> MongoAccountStore:
        return self._accounts

    @property
    def spaces(self) -> MongoSpaceStore:
        return self._spaces

    @property
    def meshes(self) -> MongoMeshStore:
        return self._meshes

    @property
    def cache(self) -> MongoCacheStore:
        return self._cache

    @property
    def media(self) -> "MediaStore":
        return self._media
