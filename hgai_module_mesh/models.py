"""HypergraphAI Mesh data models."""

from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from hgai.models.common import Status, TimestampedModel


class MeshServer(TimestampedModel):
    """A HypergraphAI server within a mesh."""

    server_id: str = Field(..., description="Unique server identifier")

    @field_validator("server_id")
    @classmethod
    def server_id_no_dots(cls, v: str) -> str:
        if "." in v:
            raise ValueError("Server ID must not contain '.' (reserved for mesh dot-notation)")
        return v
    server_name: str = Field(..., description="Display name")
    url: str = Field(..., description="Server base URL")
    api_token: Optional[str] = Field(default=None, description="Auth token for this server")
    graphs: List[str] = Field(default_factory=list, description="Available graph IDs on this server")
    status: Status = Field(default=Status.active)


class MeshBase(TimestampedModel):
    """Base mesh fields."""

    id: str = Field(..., description="Unique mesh identifier")

    @field_validator("id")
    @classmethod
    def id_no_dots(cls, v: str) -> str:
        if "." in v:
            raise ValueError("Mesh ID must not contain '.' (reserved for mesh dot-notation)")
        return v
    label: str = Field(..., description="Display label")
    description: Optional[str] = Field(default=None)
    servers: List[MeshServer] = Field(
        default_factory=list, description="HypergraphAI servers in this mesh"
    )


class MeshCreate(MeshBase):
    """Schema for creating a mesh."""
    pass


class MeshUpdate(TimestampedModel):
    """Schema for updating a mesh."""

    label: Optional[str] = None
    description: Optional[str] = None
    servers: Optional[List[MeshServer]] = None
    attributes: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    status: Optional[Status] = None


class MeshInDB(MeshBase):
    """Mesh as stored in MongoDB."""

    class Config:
        populate_by_name = True


class MeshResponse(MeshInDB):
    """Mesh API response."""
    pass
