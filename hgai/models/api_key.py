"""Tenant-scoped API keys.

The two keys configured through HGAI_PRIMARY_API_KEY / HGAI_SECONDARY_API_KEY are full
system admin. A stored key is bound to one tenant: it acts as an `agent` account of that
tenant, limited to the operations it was issued with. The secret is shown once and only
its hash is stored.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import Field, field_validator

from hgai.models.common import TimestampedModel

# Keys are machine credentials: never `admin`.
KEY_OPERATIONS = ("read", "write", "delete", "query", "export", "import")
KEY_PREFIX = "hgai_"
KEY_USERNAME_PREFIX = "apikey:"


class ApiKeyStatus(str, Enum):
    active = "active"
    revoked = "revoked"


class ApiKeyCreate(TimestampedModel):
    label: str = Field(..., min_length=1, max_length=200, description="What the key is for")
    tenant_id: Optional[str] = Field(
        default=None, description="Tenant the key belongs to. A tenant admin's keys always use its own tenant."
    )
    operations: List[str] = Field(default_factory=lambda: ["read", "query"])
    expires_at: Optional[datetime] = Field(default=None, description="Key stops working at this time (UTC)")

    @field_validator("operations")
    @classmethod
    def _known_operations(cls, v):
        bad = [o for o in v if o not in KEY_OPERATIONS]
        if bad:
            raise ValueError(f"Unknown operations {bad}; allowed: {list(KEY_OPERATIONS)}")
        return sorted(set(v))


class ApiKeyInDB(TimestampedModel):
    id: str
    label: str
    tenant_id: str
    key_prefix: str = Field(..., description="First characters of the key, to recognise it in a list")
    key_hash: str
    operations: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    status: ApiKeyStatus = Field(default=ApiKeyStatus.active)

    class Config:
        populate_by_name = True


class ApiKeyResponse(TimestampedModel):
    """A key as listed: never the secret or its hash."""

    id: str
    label: str
    tenant_id: str
    key_prefix: str
    operations: List[str] = Field(default_factory=list)
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    status: ApiKeyStatus = Field(default=ApiKeyStatus.active)


class ApiKeyCreated(ApiKeyResponse):
    key: str = Field(..., description="The secret. Shown once; store it now.")
