"""Account (user/agent) data models."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, EmailStr, model_validator

from hgai.models.common import Status, TimestampedModel


class Role(str, Enum):
    # `admin` is the legacy global role. It is still stored and accepted, and
    # is read as SystemRole.system_admin (see AccountBase). `tenant_admin`
    # administers one tenant. See docs/architecture/hypergraph-ai-multi-tenancy-*.md.
    admin = "admin"
    tenant_admin = "tenant_admin"
    user = "user"
    agent = "agent"
    readonly = "readonly"


class SystemRole(str, Enum):
    """Roles that sit above tenants. `system_admin` replaces the legacy global `admin`."""

    system_admin = "system_admin"
    # Read-only across every tenant, for audit and support: graphs, spaces, accounts,
    # tenants and queries. Cannot change anything, and cannot reach users' own notes,
    # media, saved queries or chats.
    system_auditor = "system_auditor"


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
    system_role: Optional[SystemRole] = Field(
        default=None,
        description="System-wide role across all tenants. None for ordinary tenant accounts.",
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant this account belongs to. None for system accounts, and for accounts "
                    "stored before multi-tenancy (read as the default tenant).",
    )

    @model_validator(mode="after")
    def _legacy_admin_is_system_admin(self):
        # The legacy global `admin` role is the system admin. Normalize on read
        # so stored data, tokens and scripts written against the old model work.
        if self.system_role is None and Role.admin in self.roles:
            self.system_role = SystemRole.system_admin
        return self


class AccountCreate(AccountBase):
    """Schema for creating an account."""

    password: str = Field(..., min_length=6, description="Plain-text password (will be hashed)")


class AccountUpdate(TimestampedModel):
    """Schema for updating an account."""

    email: Optional[str] = None
    description: Optional[str] = None
    roles: Optional[List[Role]] = None
    permissions: Optional[AccountPermissions] = None
    system_role: Optional[SystemRole] = None
    tenant_id: Optional[str] = None
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


class MeResponse(AccountResponse):
    """`GET /auth/me`: the account plus what a client needs to show tenancy correctly."""

    multitenancy_enabled: bool = Field(default=False, description="Whether tenant isolation is enforced on this server")
    tenant_label: Optional[str] = Field(default=None, description="Display name of the account's tenant")


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
