"""Abstract storage backend interface for HypergraphAI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from .filters import (
    AccountFilters,
    AccountPatch,
    HyperedgeFilters,
    HyperedgePatch,
    HyperedgeSearchFilters,
    HypergraphFilters,
    HypergraphPatch,
    HypernodeFilters,
    HypernodePatch,
    HypernodeSearchFilters,
    MeshFilters,
    MeshPatch,
    TransitiveSearchFilter,
)


# ─── Hypergraph Store ─────────────────────────────────────────────────────────

class HypergraphStore(ABC):
    """CRUD operations for hypergraphs."""

    @abstractmethod
    async def create(self, doc: Dict[str, Any]) -> Any:
        """Insert a new hypergraph document and return the HypergraphInDB model."""

    @abstractmethod
    async def get(self, graph_id: str, space_id: Optional[str] = None) -> Optional[Any]:
        """Return a HypergraphInDB or None. space_id=None targets unowned graphs."""

    @abstractmethod
    async def find_by_id_unscoped(self, graph_id: str) -> Optional[Any]:
        """Look up a graph by id only, ignoring space scope.

        Used by auth/HQL paths that lack space context. Returns the first match.
        """

    @abstractmethod
    async def list(
        self,
        filters: HypergraphFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Any]]:
        """Return (total_count, [HypergraphInDB, ...]) matching filters."""

    @abstractmethod
    async def update(
        self,
        graph_id: str,
        patch: HypergraphPatch,
        space_id: Optional[str] = None,
    ) -> Optional[Any]:
        """Apply patch fields and bump version. Returns updated HypergraphInDB or None."""

    @abstractmethod
    async def delete(self, graph_id: str, space_id: Optional[str] = None) -> bool:
        """Delete the hypergraph document. Returns True if deleted."""

    @abstractmethod
    async def stats(self, graph_id: str, space_id: Optional[str] = None) -> Dict[str, Any]:
        """Return node_count, edge_count, relation_types, node_types for the graph."""

    @abstractmethod
    async def increment_counts(
        self,
        graph_id: str,
        space_id: Optional[str] = None,
        node_delta: int = 0,
        edge_delta: int = 0,
    ) -> None:
        """Atomically adjust node_count and/or edge_count on the graph document."""

    @abstractmethod
    async def list_ids_for_space(self, space_id: str) -> List[str]:
        """Return all graph IDs belonging to the given space."""

    @abstractmethod
    async def reassign_space(
        self, graph_id: str, old_space_id: Optional[str], new_space_id: Optional[str]
    ) -> bool:
        """Change (or clear) the space_id on a graph. Returns True if modified."""

    @abstractmethod
    async def list_by_space_ids(
        self, space_ids: List[str], status: Optional[str] = "active"
    ) -> List[str]:
        """Return all graph IDs whose space_id is in space_ids."""

    @abstractmethod
    async def list_space_graphs(
        self, space_id: str, skip: int = 0, limit: int = 50
    ) -> Tuple[int, List[Any]]:
        """Return (total, [HypergraphInDB]) for graphs in the given space."""

    @abstractmethod
    async def find_composition_member(self, member_id: str) -> Optional[Any]:
        """Find a single hypergraph document by id for logical graph composition."""


# ─── Hypernode Store ──────────────────────────────────────────────────────────

class HypernodeStore(ABC):
    """CRUD operations for hypernodes."""

    @abstractmethod
    async def create(self, doc: Dict[str, Any]) -> Any:
        """Insert a hypernode document and return HypernodeInDB."""

    @abstractmethod
    async def get(self, hypergraph_id: str, node_id: str) -> Optional[Any]:
        """Return HypernodeInDB or None."""

    @abstractmethod
    async def list(
        self,
        filters: HypernodeFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Any]]:
        """Return (total_count, [HypernodeInDB, ...]) matching filters."""

    @abstractmethod
    async def update(
        self,
        hypergraph_id: str,
        node_id: str,
        patch: HypernodePatch,
    ) -> Optional[Any]:
        """Apply patch and bump version. Returns updated HypernodeInDB or None."""

    @abstractmethod
    async def delete(self, hypergraph_id: str, node_id: str) -> bool:
        """Delete a single hypernode. Returns True if deleted."""

    @abstractmethod
    async def delete_by_graph(self, hypergraph_id: str) -> int:
        """Delete all hypernodes for a hypergraph. Returns count deleted."""

    @abstractmethod
    async def search(
        self,
        filters: HypernodeSearchFilters,
        skip: int = 0,
        limit: int = 500,
    ) -> List[Any]:
        """Return a list of raw node dicts matching the search filters (used by HQL/SHQL)."""

    @abstractmethod
    async def get_distinct_types(self, hypergraph_id: str) -> List[str]:
        """Return all distinct 'type' values for nodes in the graph."""

    @abstractmethod
    async def find_by_ids(
        self, node_ids: List[str], hypergraph_ids: List[str]
    ) -> List[Any]:
        """Return raw node dicts for the given node_ids scoped to hypergraph_ids."""

    @abstractmethod
    async def find_relation_node(
        self, relation: str, hypergraph_id: str
    ) -> Optional[Dict[str, Any]]:
        """Find the RelationType hypernode for a given relation string."""


# ─── Hyperedge Store ──────────────────────────────────────────────────────────

class HyperedgeStore(ABC):
    """CRUD operations for hyperedges."""

    @abstractmethod
    async def create(self, doc: Dict[str, Any]) -> Any:
        """Insert a hyperedge document and return HyperedgeInDB."""

    @abstractmethod
    async def get_by_id_or_hyperkey(
        self, hypergraph_id: str, edge_id: str
    ) -> Optional[Any]:
        """Return HyperedgeInDB by id or hyperkey. Returns None if not found."""

    @abstractmethod
    async def list(
        self,
        filters: HyperedgeFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Any]]:
        """Return (total_count, [HyperedgeInDB, ...]) matching filters."""

    @abstractmethod
    async def update(
        self,
        hypergraph_id: str,
        edge_id: str,
        patch: HyperedgePatch,
    ) -> Optional[Any]:
        """Apply patch and bump version. Returns updated HyperedgeInDB or None."""

    @abstractmethod
    async def delete(self, hypergraph_id: str, edge_id: str) -> bool:
        """Delete a single hyperedge by id or hyperkey. Returns True if deleted."""

    @abstractmethod
    async def delete_by_graph(self, hypergraph_id: str) -> int:
        """Delete all hyperedges for a hypergraph. Returns count deleted."""

    @abstractmethod
    async def search(
        self,
        filters: HyperedgeSearchFilters,
        skip: int = 0,
        limit: int = 500,
    ) -> List[Any]:
        """Return a list of raw edge dicts matching the search filters (used by HQL/SHQL)."""

    @abstractmethod
    async def get_distinct_relations(self, hypergraph_id: str) -> List[str]:
        """Return all distinct 'relation' values for edges in the graph."""

    @abstractmethod
    async def find_for_transitive(
        self, filters: TransitiveSearchFilter
    ) -> List[Dict[str, Any]]:
        """Return raw edge dicts (with 'members' field) for transitive closure traversal."""

    @abstractmethod
    async def find_relation_node(
        self, relation: str, hypergraph_id: str
    ) -> Optional[Dict[str, Any]]:
        """Alias helper: find the RelationType hypernode for a given relation."""


# ─── Account Store ────────────────────────────────────────────────────────────

class AccountStore(ABC):
    """CRUD operations for accounts."""

    @abstractmethod
    async def create(self, doc: Dict[str, Any]) -> Any:
        """Insert an account document and return AccountInDB."""

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[Any]:
        """Return AccountInDB or None."""

    @abstractmethod
    async def exists(self, username: str) -> bool:
        """Return True if an account with that username exists."""

    @abstractmethod
    async def list(
        self,
        filters: AccountFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Any]]:
        """Return (total_count, [raw account dicts]) matching filters."""

    @abstractmethod
    async def update(
        self,
        username: str,
        update_fields: Dict[str, Any],
    ) -> Optional[Any]:
        """Apply update_fields dict (already built by caller). Returns raw doc or None."""

    @abstractmethod
    async def delete(self, username: str) -> bool:
        """Delete an account. Returns True if deleted."""

    @abstractmethod
    async def record_login(self, username: str) -> None:
        """Set last_login to now for the given account."""


# ─── Space Store ──────────────────────────────────────────────────────────────

class SpaceStore(ABC):
    """CRUD and membership operations for spaces."""

    @abstractmethod
    async def create(self, doc: Dict[str, Any]) -> Any:
        """Insert a space document and return SpaceInDB."""

    @abstractmethod
    async def get(self, space_id: str) -> Optional[Any]:
        """Return SpaceInDB or None."""

    @abstractmethod
    async def list(
        self,
        filters: SpaceFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Any]]:
        """Return (total_count, [SpaceInDB, ...]) matching filters."""

    @abstractmethod
    async def update(
        self,
        space_id: str,
        patch: SpacePatch,
    ) -> Optional[Any]:
        """Apply patch and bump version. Returns updated SpaceInDB or None."""

    @abstractmethod
    async def delete(self, space_id: str) -> bool:
        """Delete a space document. Returns True if deleted."""

    @abstractmethod
    async def add_member(self, space_id: str, username: str, role: str) -> Optional[Any]:
        """Add or replace member entry. Returns updated SpaceInDB or None."""

    @abstractmethod
    async def remove_member(self, space_id: str, username: str) -> Optional[Any]:
        """Remove a member from a space. Returns updated SpaceInDB or None."""

    @abstractmethod
    async def get_member_role(self, space_id: str, username: str) -> Optional[str]:
        """Return the role string for the given member, or None if not a member."""

    @abstractmethod
    async def remove_user_from_all_spaces(self, username: str) -> None:
        """Remove a username from the members array of every space it belongs to."""

    @abstractmethod
    async def list_space_ids_for_member(self, username: str) -> List[str]:
        """Return all space IDs where the given user is an active member."""

    @abstractmethod
    async def get_space_for_graph(self, graph_id: str) -> Optional[str]:
        """Return the space_id of a graph (via the hypergraph collection)."""

    @abstractmethod
    async def update_many_hypergraphs(
        self, space_id: str, update_doc: Dict[str, Any]
    ) -> None:
        """Apply an update document to all hypergraphs belonging to the given space."""

    @abstractmethod
    async def list_active_space_ids_for_user(self, username: str) -> List[str]:
        """Return IDs of active spaces where username is a member."""


# ─── Mesh Store ───────────────────────────────────────────────────────────────

class MeshStore(ABC):
    """CRUD operations for meshes."""

    @abstractmethod
    async def create(self, doc: Dict[str, Any]) -> Any:
        """Insert a mesh document and return MeshInDB."""

    @abstractmethod
    async def get(self, mesh_id: str) -> Optional[Any]:
        """Return raw mesh dict or None."""

    @abstractmethod
    async def list(
        self,
        filters: MeshFilters,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Any]]:
        """Return (total_count, [raw mesh dicts]) matching filters."""

    @abstractmethod
    async def update(
        self,
        mesh_id: str,
        update_fields: Dict[str, Any],
    ) -> Optional[Any]:
        """Apply update_fields (already built by caller). Returns raw doc or None."""

    @abstractmethod
    async def delete(self, mesh_id: str) -> bool:
        """Delete a mesh document. Returns True if deleted."""

    @abstractmethod
    async def update_servers(
        self, mesh_id: str, servers: List[Any]
    ) -> None:
        """Replace the servers list on a mesh (used after sync). No return value."""

    @abstractmethod
    async def list_active(self) -> List[Dict[str, Any]]:
        """Return all active mesh documents (used by scheduler)."""


# ─── Cache Store ──────────────────────────────────────────────────────────────

class CacheStore(ABC):
    """Query result cache operations."""

    @abstractmethod
    async def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Return cached result dict or None (None if expired or missing)."""

    @abstractmethod
    async def set(
        self,
        cache_key: str,
        result: Dict[str, Any],
        graph_ids: Optional[List[str]] = None,
        ttl_seconds: int = 300,
    ) -> None:
        """Store a result. graph_ids enables graph-scoped invalidation."""

    @abstractmethod
    async def invalidate(self, graph_id: Optional[str] = None) -> int:
        """Invalidate entries. If graph_id given, only invalidate entries for that graph.
        Returns number of entries removed."""

    @abstractmethod
    async def stats(self) -> Dict[str, Any]:
        """Return total_entries, expired_entries, active_entries counts."""


# ─── SpacePatch import ────────────────────────────────────────────────────────
# Re-export so callers can import from backend instead of filters
from .filters import SpacePatch  # noqa: E402


# ─── Top-level StorageBackend ABC ─────────────────────────────────────────────

class StorageBackend(ABC):
    """Top-level storage backend. Owns connection lifecycle and exposes per-entity stores."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the underlying storage system."""

    @abstractmethod
    async def close(self) -> None:
        """Close the connection."""

    @abstractmethod
    async def ensure_schema(self) -> None:
        """Create indexes, collections, or schema objects. Safe to call on every startup."""

    @property
    @abstractmethod
    def hypergraphs(self) -> HypergraphStore:
        """Hypergraph store."""

    @property
    @abstractmethod
    def hypernodes(self) -> HypernodeStore:
        """Hypernode store."""

    @property
    @abstractmethod
    def hyperedges(self) -> HyperedgeStore:
        """Hyperedge store."""

    @property
    @abstractmethod
    def accounts(self) -> AccountStore:
        """Account store."""

    @property
    @abstractmethod
    def spaces(self) -> SpaceStore:
        """Space store."""

    @property
    @abstractmethod
    def meshes(self) -> MeshStore:
        """Mesh store."""

    @property
    @abstractmethod
    def cache(self) -> CacheStore:
        """Cache store."""
