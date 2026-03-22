"""Account (user/agent) data models."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, EmailStr

from hgai.models.common import Status, TimestampedModel


class Role(str, Enum):
    admin = "admin"
    user = "user"
    agent = "agent"
    readonly = "readonly"


class Operation(str, Enum):
    read = "read"
    write = "write"
    delete = "delete"
    admin = "admin"
    query = "query"
    export = "export"
    import_ = "import"


class AccountPermissions(TimestampedModel):
    """Granular RBAC permissions for an account."""

    graphs: List[str] = Field(
        default_factory=lambda: [],
        description="List of hypergraph IDs this account can access ('*' for all)"
    )
    operations: List[str] = Field(
        default_factory=lambda: ["read", "query"],
        description="Permitted operations"
    )


class AccountBase(TimestampedModel):
    """Base account fields."""

    username: str = Field(..., description="Unique username")
    email: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    roles: List[Role] = Field(default_factory=lambda: [Role.user])
    permissions: AccountPermissions = Field(default_factory=AccountPermissions)


class AccountCreate(AccountBase):
    """Schema for creating an account."""

    password: str = Field(..., min_length=6, description="Plain-text password (will be hashed)")


class AccountUpdate(TimestampedModel):
    """Schema for updating an account."""

    email: Optional[str] = None
    description: Optional[str] = None
    roles: Optional[List[Role]] = None
    permissions: Optional[AccountPermissions] = None
    attributes: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    status: Optional[Status] = None
    password: Optional[str] = Field(default=None, min_length=6)


class AccountInDB(AccountBase):
    """Account as stored in MongoDB (includes password hash)."""

    password_hash: str = Field(..., description="bcrypt password hash")
    last_login: Optional[Any] = Field(default=None)

    class Config:
        populate_by_name = True


class AccountResponse(AccountBase):
    """Account API response (no password hash)."""

    last_login: Optional[Any] = Field(default=None)


class TokenResponse(TimestampedModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    username: str
    roles: List[str]


class TokenData(TimestampedModel):
    """Data encoded in JWT token."""

    username: str
    roles: List[str] = Field(default_factory=list)
