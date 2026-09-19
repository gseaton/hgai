"""AI Agent Chat data models: vendor credentials, model catalog, and chat
sessions/messages.

Not a hypergraph entity, no ACL — vendors/models share the ParameterizedQuery/
Mesh visibility model (globally unique `id`, admin-gated writes). Sessions
and messages are per-account instead (owner-only, like Notes), since a chat
conversation is private the way a hyperedge is not.

Sessions/messages are hgai's own lightweight audit/export layer — NOT the
source of truth for conversation replay. Agno's own MongoDb-backed session
store (see hgai_module_agentchat/engine.py) owns that; these records exist
so the UI can list/restart sessions and so a turn can be exported to a Note
with its vendor/model/timing/token metadata (see hgai.core.notes).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from hgai.models.common import TimestampedModel


class AgentVendorName(str, Enum):
    """Which Agno model class family a vendor maps to (see
    hgai_module_agentchat.engine.build_agent, added in Phase 2). `custom` is
    reserved for a future OpenAI-compatible/local endpoint via `base_url`."""

    anthropic = "anthropic"
    openai = "openai"
    xai = "xai"
    custom = "custom"


class AgentVendorBase(TimestampedModel):
    name: AgentVendorName = Field(..., description="Vendor kind — selects which Agno model class to use")
    label: str = Field(..., max_length=200, description="Display name, e.g. 'Anthropic'")
    base_url: Optional[str] = Field(default=None, description="Override endpoint (OpenAI-compatible/local models)")
    enabled: bool = Field(default=True)

    @field_validator("label")
    @classmethod
    def _clean_label(cls, value: str) -> str:
        return value.strip()


class AgentVendorCreate(AgentVendorBase):
    """`api_key` is write-only and optional — a vendor can be created as a
    placeholder (no usable key yet, e.g. the seeded default catalog) and
    have a key added later via update. It is never stored in plaintext
    (see hgai_module_agentchat.crypto) and never echoed back in a response."""

    api_key: Optional[str] = Field(default=None, description="Plaintext API key (encrypted at rest)")


class AgentVendorUpdate(BaseModel):
    """All fields optional. `api_key`, when given, rotates the stored key;
    omit it to leave the existing key untouched."""

    label: Optional[str] = None
    base_url: Optional[str] = None
    enabled: Optional[bool] = None
    api_key: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


class AgentVendorInDB(AgentVendorBase):
    """Vendor as stored. `api_key_encrypted` is marked `exclude=True` so
    Pydantic drops it from every serialization (API responses, `.model_dump()`
    calls, logs that happen to dump the model) automatically — not something
    a future route has to remember to scrub by hand. `api_key_last4` is the
    only key-derived value ever surfaced, for display/confirmation only."""

    id: str = Field(..., description="Agent vendor identifier (UUID4)")
    api_key_encrypted: str = Field(default="", exclude=True, description="Fernet ciphertext — internal only")
    api_key_last4: str = Field(default="", description="Last 4 characters of the plaintext key, display only")
    mutations: List[Any] = Field(default_factory=list, description="Audit trail of create/mutate events")

    class Config:
        populate_by_name = True


class AgentVendorResponse(AgentVendorInDB):
    """Vendor API response. Inherits `api_key_encrypted`'s `exclude=True`."""


class AgentModelBase(TimestampedModel):
    vendor_id: str = Field(..., description="AgentVendor.id this model calls through")
    model_id: str = Field(..., max_length=200, description="Vendor's own model identifier, e.g. 'claude-sonnet-5'")
    label: str = Field(..., max_length=200, description="Display name")
    description: str = Field(default="")
    default_temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    default_max_tokens: Optional[int] = Field(default=None, gt=0)
    enabled: bool = Field(default=True)

    @field_validator("label")
    @classmethod
    def _clean_label(cls, value: str) -> str:
        return value.strip()


class AgentModelCreate(AgentModelBase):
    pass


class AgentModelUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    default_temperature: Optional[float] = None
    default_max_tokens: Optional[int] = None
    enabled: Optional[bool] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None


class AgentModelInDB(AgentModelBase):
    id: str = Field(..., description="Agent model identifier (UUID4)")
    mutations: List[Any] = Field(default_factory=list, description="Audit trail of create/mutate events")

    class Config:
        populate_by_name = True


class AgentModelResponse(AgentModelInDB):
    pass


class AgentChatSessionCreate(BaseModel):
    model_id: str = Field(..., description="AgentModel.id this session is pinned to")
    title: str = Field(default="", max_length=200, description="Editable title; auto-set from the first prompt if left blank")


class AgentChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None


class AgentChatSessionInDB(BaseModel):
    """A chat conversation thread. `id` doubles as Agno's own `session_id` —
    one identifier, not two — so "restarting" a session is simply reusing
    this id on a later call; Agno's Mongo-backed history does the rest."""

    id: str = Field(..., description="Chat session identifier (UUID4) — also the Agno session_id")
    owner_username: str = Field(..., description="Account that owns this session; only it (or an admin) may access it")
    title: str = Field(default="")
    model_id: str = Field(..., description="AgentModel.id this session is pinned to")
    last_message_at: Optional[datetime] = Field(default=None)
    message_count: int = Field(default=0)
    status: str = Field(default="active")
    system_created: Optional[datetime] = Field(default=None)
    system_updated: Optional[datetime] = Field(default=None)

    class Config:
        populate_by_name = True


class AgentChatSessionResponse(AgentChatSessionInDB):
    pass


class AgentChatSendRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="The user's chat prompt for this turn")


class AgentChatMessageInDB(BaseModel):
    """One turn's user or assistant message — hgai's own audit/export
    record (see module docstring); not used to replay conversation context
    back to the model."""

    id: str = Field(..., description="Chat message identifier (UUID4)")
    session_id: str
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(default="", description="Markdown content")
    vendor_name: Optional[str] = Field(default=None)
    model_id: Optional[str] = Field(default=None)
    started_at: Optional[datetime] = Field(default=None)
    ended_at: Optional[datetime] = Field(default=None)
    duration_ms: Optional[int] = Field(default=None)
    tokens_input: Optional[int] = Field(default=None)
    tokens_output: Optional[int] = Field(default=None)
    tokens_total: Optional[int] = Field(default=None)
    created_at: Optional[datetime] = Field(default=None)

    class Config:
        populate_by_name = True


class AgentChatMessageResponse(AgentChatMessageInDB):
    pass
