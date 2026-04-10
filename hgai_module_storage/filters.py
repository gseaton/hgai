"""Typed filter and patch dataclasses used by the storage backend interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class HypergraphFilters:
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    space_id: Optional[str] = None  # None means unowned-only when explicitly passed as UNOWNED sentinel


@dataclass
class HypergraphPatch:
    label: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None
    composition: Optional[List[str]] = None
    remote_refs: Optional[List[Any]] = None
    updated_by: str = ""


@dataclass
class HypernodeFilters:
    hypergraph_id: str
    node_type: Optional[str] = None
    status: Optional[str] = "active"
    tags: Optional[List[str]] = None
    search: Optional[str] = None  # text search on label
    pit: Optional[datetime] = None  # point-in-time


@dataclass
class HypernodePatch:
    label: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    updated_by: str = ""


@dataclass
class HyperedgeFilters:
    hypergraph_id: str
    relation: Optional[str] = None
    flavor: Optional[str] = None
    status: Optional[str] = "active"
    tags: Optional[List[str]] = None
    member_node_id: Optional[str] = None  # edges containing this node
    pit: Optional[datetime] = None


@dataclass
class HyperedgePatch:
    label: Optional[str] = None
    description: Optional[str] = None
    relation: Optional[str] = None
    flavor: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None
    members: Optional[List[Any]] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    skos_broader: Optional[List[str]] = None
    skos_narrower: Optional[List[str]] = None
    skos_related: Optional[List[str]] = None
    updated_by: str = ""


@dataclass
class HypernodeSearchFilters:
    """Used by HQL/SHQL engines for rich node queries."""
    hypergraph_ids: List[str]
    node_type: Optional[str] = None
    status: Optional[str] = "active"
    tags: Optional[List[str]] = None
    search: Optional[str] = None
    pit: Optional[datetime] = None
    node_ids_in: Optional[List[str]] = None  # filter to specific node IDs
    attributes: Optional[Dict[str, Any]] = None  # attribute equality filters


@dataclass
class HyperedgeSearchFilters:
    """Used by HQL/SHQL engines for rich edge queries."""
    hypergraph_ids: List[str]
    relation: Optional[str] = None
    flavor: Optional[str] = None
    status: Optional[str] = "active"
    tags: Optional[List[str]] = None
    member_node_id: Optional[str] = None
    member_node_ids_all: Optional[List[str]] = None  # edges containing ALL of these nodes
    member_node_ids_any: Optional[List[str]] = None  # edges containing any of these nodes
    pit: Optional[datetime] = None
    attributes: Optional[Dict[str, Any]] = None
    extra_filters: Optional[Dict[str, Any]] = None  # pass-through arbitrary mongo-style filters


@dataclass
class TransitiveSearchFilter:
    """Used by inference engine for transitive closure traversal."""
    hypergraph_ids: List[str]
    relation: str
    member_node_ids: List[str]  # find edges containing any of these nodes


@dataclass
class AccountFilters:
    role: Optional[str] = None
    status: Optional[str] = None


@dataclass
class AccountPatch:
    email: Optional[str] = None
    display_name: Optional[str] = None
    roles: Optional[List[str]] = None
    status: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    permissions: Optional[Any] = None
    updated_by: str = ""


@dataclass
class SpaceFilters:
    username: Optional[str] = None  # filter spaces where this user is a member
    status: Optional[str] = None


@dataclass
class SpacePatch:
    label: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    updated_by: str = ""


@dataclass
class MeshFilters:
    status: Optional[str] = None


@dataclass
class MeshPatch:
    label: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    servers: Optional[List[Any]] = None
    updated_by: str = ""


@dataclass
class CacheStats:
    total_entries: int
    expired_entries: int


@dataclass
class GraphStats:
    node_count: int
    edge_count: int
    relation_types: List[str]
    node_types: List[str]
