"""Hypergraph data models."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from hgai.models.common import TimestampedModel


class GraphType(str, Enum):
    instantiated = "instantiated"   # Physical collection in MongoDB
    logical = "logical"             # Virtual composition of other graphs


class RemoteGraphRef(TimestampedModel):
    """Reference to a graph on a remote HypergraphAI server (for mesh queries)."""

    server_id: str = Field(..., description="Remote server ID")
    server_url: str = Field(..., description="Remote server URL")
    graph_id: str = Field(..., description="Graph ID on the remote server")


class HypergraphBase(TimestampedModel):
    """Base hypergraph fields."""

    id: str = Field(..., description="Unique hypergraph identifier")
    label: str = Field(..., description="Display label")
    space_id: Optional[str] = Field(default=None, description="Owning space ID")

    @field_validator("id")
    @classmethod
    def id_no_dots(cls, v: str) -> str:
        if "." in v:
            raise ValueError("Hypergraph ID must not contain '.' (reserved for mesh dot-notation)")
        return v
    description: Optional[str] = Field(default=None)
    type: GraphType = Field(default=GraphType.instantiated)

    # For logical (composed) hypergraphs
    composition: List[str] = Field(
        default_factory=list,
        description="List of hypergraph IDs composed into this logical graph"
    )
    remote_refs: List[RemoteGraphRef] = Field(
        default_factory=list,
        description="Remote graph references for cross-server composition"
    )


class HypergraphCreate(HypergraphBase):
    """Schema for creating a hypergraph."""
    pass


class HypergraphUpdate(TimestampedModel):
    """Schema for updating a hypergraph."""

    label: Optional[str] = None
    description: Optional[str] = None
    type: Optional[GraphType] = None
    composition: Optional[List[str]] = None
    remote_refs: Optional[List[RemoteGraphRef]] = None
    attributes: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class HypergraphInDB(HypergraphBase):
    """Hypergraph as stored in MongoDB."""

    node_count: int = Field(default=0)
    edge_count: int = Field(default=0)

    class Config:
        populate_by_name = True


class HypergraphResponse(HypergraphInDB):
    """Hypergraph API response."""
    pass


class HypergraphStats(TimestampedModel):
    """Hypergraph statistics."""

    graph_id: str
    node_count: int
    edge_count: int
    relation_types: List[str]
    node_types: List[str]
    tags: List[str]
