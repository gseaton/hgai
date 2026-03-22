"""Hypernode (entity node) data models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field

from hgai.models.common import Status, TimestampedModel


class HypernodeBase(TimestampedModel):
    """Base hypernode fields."""

    id: str = Field(..., description="Human-readable unique identifier within hypergraph")
    label: str = Field(..., description="Display label")
    type: str = Field(default="Entity", description="Entity type (e.g., Person, Organization)")
    description: Optional[str] = Field(default=None)

    # Temporal existential qualifiers
    valid_from: Optional[datetime] = Field(
        default=None, description="When this node became valid in the real world"
    )
    valid_to: Optional[datetime] = Field(
        default=None, description="When this node ceased to be valid in the real world"
    )

    # SKOS semantic relationships (to other node IDs)
    skos_broader: List[str] = Field(default_factory=list, description="SKOS broader concepts")
    skos_narrower: List[str] = Field(default_factory=list, description="SKOS narrower concepts")
    skos_related: List[str] = Field(default_factory=list, description="SKOS related concepts")


class HypernodeCreate(HypernodeBase):
    """Schema for creating a hypernode."""
    pass


class HypernodeUpdate(TimestampedModel):
    """Schema for updating a hypernode (all fields optional)."""

    label: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    status: Optional[Status] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    skos_broader: Optional[List[str]] = None
    skos_narrower: Optional[List[str]] = None
    skos_related: Optional[List[str]] = None


class HypernodeInDB(HypernodeBase):
    """Hypernode as stored in MongoDB."""

    hypergraph_id: str = Field(..., description="Parent hypergraph ID")

    class Config:
        populate_by_name = True


class HypernodeResponse(HypernodeInDB):
    """Hypernode API response."""
    pass
