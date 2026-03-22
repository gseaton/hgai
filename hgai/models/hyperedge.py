"""Hyperedge (first-class semantic relationship) data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from hgai.models.common import Status, TimestampedModel


class EdgeFlavor(str, Enum):
    """Hyperedge relationship pattern flavors."""

    hub = "hub"                          # One-to-many (hub node connects to member nodes)
    symmetric = "symmetric"              # All members are equivalent (e.g., siblings)
    direct = "direct"                    # Directed from first to last member
    transitive = "transitive"            # Transitive chain (A→B, B→C implies A→C)
    inverse_transitive = "inverse-transitive"  # Inverse transitive chain


class EdgeMember(TimestampedModel):
    """A member node in a hyperedge."""

    node_id: str = Field(..., description="Hypernode ID")
    role: Optional[str] = Field(default=None, description="Role of this node in the edge")
    seq: int = Field(default=0, description="Sequence position within the edge")
    order: Optional[int] = Field(default=None, description="Display order (node order matters for flavor)")

    # Allow extra attributes on membership
    class Config:
        extra = "allow"
        populate_by_name = True


class HyperedgeBase(TimestampedModel):
    """Base hyperedge fields."""

    id: Optional[str] = Field(
        default=None,
        description="Human-readable ID (auto-generated hyperkey if not provided)"
    )
    relation: str = Field(..., description="Semantic relation type (e.g., 'has-member', 'sibling')")
    label: Optional[str] = Field(default=None, description="Display label")
    flavor: EdgeFlavor = Field(default=EdgeFlavor.hub, description="Relationship pattern flavor")
    members: List[EdgeMember] = Field(
        default_factory=list, description="Ordered list of participating hypernodes"
    )
    description: Optional[str] = Field(default=None)

    # Temporal existential qualifiers
    valid_from: Optional[datetime] = Field(
        default=None, description="When this relationship became valid"
    )
    valid_to: Optional[datetime] = Field(
        default=None, description="When this relationship ceased to be valid"
    )

    # SKOS semantic relationships (to other edge IDs for inferencing)
    skos_broader: List[str] = Field(default_factory=list)
    skos_narrower: List[str] = Field(default_factory=list)
    skos_related: List[str] = Field(default_factory=list)

    # Reference to semantic relation node (optional)
    relation_node_id: Optional[str] = Field(
        default=None, description="ID of the RelationType hypernode for this relation"
    )


class HyperedgeCreate(HyperedgeBase):
    """Schema for creating a hyperedge."""
    pass


class HyperedgeUpdate(TimestampedModel):
    """Schema for updating a hyperedge."""

    relation: Optional[str] = None
    label: Optional[str] = None
    flavor: Optional[EdgeFlavor] = None
    members: Optional[List[EdgeMember]] = None
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    status: Optional[Status] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    skos_broader: Optional[List[str]] = None
    skos_narrower: Optional[List[str]] = None
    skos_related: Optional[List[str]] = None


class HyperedgeInDB(HyperedgeBase):
    """Hyperedge as stored in MongoDB."""

    hypergraph_id: str = Field(..., description="Parent hypergraph ID")
    hyperkey: Optional[str] = Field(
        default=None, description="SHA-256 hyperkey (auto-generated)"
    )

    class Config:
        populate_by_name = True


class HyperedgeResponse(HyperedgeInDB):
    """Hyperedge API response."""
    pass
