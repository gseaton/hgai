"""Tenant data models.

A tenant is the top-level isolation boundary: accounts belong to one tenant and
see only that tenant's spaces, graphs and data. System accounts (see
SystemRole) sit above tenants. See docs/architecture/hypergraph-ai-multi-tenancy-*.md.
"""

import re
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hgai.models.common import TimestampedModel

# Tenant every pre-multi-tenancy record is migrated into, and the implicit
# tenant of a deployment that leaves HGAI_MULTITENANCY_ENABLED off.
DEFAULT_TENANT_ID = "default"

# Reserved: never a real tenant id (names the system level in logs/telemetry).
SYSTEM_TENANT_ID = "__system"

# Unowned graphs that belong to the system level, not to any tenant. The
# migration stamps them with an explicit null tenant instead of the default one.
SYSTEM_GRAPH_IDS = frozenset({"__local-telemetry"})

_TENANT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class TenantQuotas(BaseModel):
    """Per-tenant limits, kept in `Tenant.settings["quotas"]`. A missing limit is unlimited.

    Limits are soft: they are checked at creation without locking, so two simultaneous
    creations can overshoot by a little.
    """

    model_config = ConfigDict(extra="forbid")

    max_accounts: Optional[int] = Field(default=None, ge=0)
    max_spaces: Optional[int] = Field(default=None, ge=0)
    max_graphs: Optional[int] = Field(default=None, ge=0, description="Hypergraphs, including those in spaces")
    max_nodes: Optional[int] = Field(default=None, ge=0, description="Hypernodes across all of the tenant's graphs")
    max_edges: Optional[int] = Field(default=None, ge=0, description="Hyperedges across all of the tenant's graphs")


# The resources a quota can limit. Each is counted by TenantStore.usage.
QUOTA_RESOURCES = ("accounts", "spaces", "graphs", "nodes", "edges")


def _check_settings(settings: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if settings and "quotas" in settings:
        settings = dict(settings, quotas=TenantQuotas.model_validate(settings["quotas"] or {}).model_dump(exclude_none=True))
    return settings


class TenantStatus(str, Enum):
    active = "active"
    suspended = "suspended"  # blocks every account in the tenant


class TenantBase(TimestampedModel):
    id: str = Field(..., description="Unique tenant identifier (immutable once created)")
    label: str = Field(..., description="Display name")
    description: Optional[str] = Field(default=None)
    settings: Dict[str, Any] = Field(
        default_factory=dict, description="Reserved for per-tenant options (quotas, feature flags)"
    )
    status: TenantStatus = Field(default=TenantStatus.active)

    @field_validator("settings")
    @classmethod
    def _valid_settings(cls, v):
        return _check_settings(v)

    @field_validator("id")
    @classmethod
    def _valid_id(cls, v: str) -> str:
        if v == SYSTEM_TENANT_ID:
            raise ValueError(f"Tenant ID '{v}' is reserved")
        if not _TENANT_ID_RE.match(v):
            raise ValueError(
                "Tenant ID must start with a letter or digit and contain only letters, digits, '-' and '_'"
            )
        return v


class TenantCreate(TenantBase):
    pass


class TenantUpdate(TimestampedModel):
    """Tenant ids are immutable, so `id` is not updatable."""

    label: Optional[str] = None
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    attributes: Optional[Dict[str, Any]] = None
    status: Optional[TenantStatus] = None

    @field_validator("settings")
    @classmethod
    def _valid_settings(cls, v):
        return _check_settings(v)


class TenantInDB(TenantBase):
    class Config:
        populate_by_name = True


class TenantResponse(TenantInDB):
    pass
