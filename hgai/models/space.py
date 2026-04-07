"""Space (tenant namespace) data models."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from hgai.models.common import Status, TimestampedModel


class SpaceRole(str, Enum):
    owner  = "owner"   # manage space, transfer ownership, delete
    admin  = "admin"   # manage members and graphs
    member = "member"  # read/write graphs per space defaults
    viewer = "viewer"  # read-only across all space graphs


# Operations permitted per space role
SPACE_ROLE_OPERATIONS: Dict[str, set] = {
    SpaceRole.owner:  {"read", "write", "delete", "admin", "query", "export", "import"},
    SpaceRole.admin:  {"read", "write", "delete", "query", "export", "import"},
    SpaceRole.member: {"read", "write", "query", "export", "import"},
    SpaceRole.viewer: {"read", "query", "export"},
}


class SpaceMember(TimestampedModel):
    """A member of a space with an assigned role."""

    username: str = Field(..., description="Account username")
    role: SpaceRole = Field(default=SpaceRole.member)


class SpaceBase(TimestampedModel):
    """Base space fields."""

    id: str = Field(..., description="Unique space identifier")
    label: str = Field(..., description="Display label")
    description: Optional[str] = Field(default=None)
    members: List[SpaceMember] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def id_no_dots(cls, v: str) -> str:
        if "." in v:
            raise ValueError("Space ID must not contain '.' (reserved for mesh dot-notation)")
        return v


class SpaceCreate(SpaceBase):
    """Schema for creating a space."""
    pass


class SpaceUpdate(TimestampedModel):
    """Schema for updating a space."""

    label: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None
    status: Optional[Status] = None


class SpaceInDB(SpaceBase):
    """Space as stored in MongoDB."""

    class Config:
        populate_by_name = True


class SpaceResponse(SpaceInDB):
    """Space API response."""
    pass


class AddMemberRequest(TimestampedModel):
    """Request body for adding a space member."""

    username: str = Field(..., description="Account username to add")
    role: SpaceRole = Field(default=SpaceRole.member)


class UpdateMemberRoleRequest(TimestampedModel):
    """Request body for updating a member's role."""

    role: SpaceRole
