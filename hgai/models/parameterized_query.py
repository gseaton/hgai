"""Parameterized query (prepared statement) data models.

A ParameterizedQuery is a reusable SHQL template — ordinary SHQL text with
`/$name$/`-style placeholders (see hgai.core.query_templates) — stored as a
first-class resource independent of any hypergraph, alongside Notes/Media,
so it can be listed, searched, tagged, and executed from either its own
"Parameterized Queries" screen or the "Query (SHQL)" screen.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from hgai.models.common import TimestampedModel


class QueryParameter(BaseModel):
    """One placeholder declared in a template's `shql` text, as parsed by
    hgai.core.query_templates.parse_parameters — never hand-authored."""

    name: str
    type: str = "str"
    default: Optional[Any] = None
    enum: Optional[List[str]] = None


class ParameterizedQueryBase(TimestampedModel):
    """Base parameterized-query fields.

    `label` is the primary display title (same convention as Note); `name`
    is a separate, short machine-ish handle (unique isn't enforced at
    storage — `id` is the only actual unique identifier — but it's meant to
    read like a stable slug, e.g. for future programmatic lookup).
    """

    name: str = Field(..., max_length=200, description="Short machine-ish handle")
    label: str = Field(..., max_length=200, description="Display title")
    description: str = Field(default="", description="What this query does, in prose")
    shql: str = Field(..., description="SHQL template text, with /$name$/-style placeholders")

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("label")
    @classmethod
    def _clean_label(cls, value: str) -> str:
        return value.strip()


class ParameterizedQueryCreate(ParameterizedQueryBase):
    """Schema for creating a parameterized query."""


class ParameterizedQueryUpdate(BaseModel):
    """Schema for updating a parameterized query's own fields (all optional)."""

    name: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    shql: Optional[str] = None
    tags: Optional[List[str]] = None
    attributes: Optional[dict] = None
    status: Optional[str] = None


class ParameterizedQueryInDB(ParameterizedQueryBase):
    """Parameterized query as stored — `parameters` is recomputed from
    `shql` on every create/update, never set directly by a caller."""

    id: str = Field(..., description="Parameterized query identifier (UUID4)")
    parameters: List[QueryParameter] = Field(default_factory=list)
    mutations: List[Any] = Field(default_factory=list, description="Audit trail of create/mutate events")

    class Config:
        populate_by_name = True


class ParameterizedQueryResponse(ParameterizedQueryInDB):
    """Parameterized query API response."""


class ExecuteParameterizedQueryRequest(BaseModel):
    """Request body for running a parameterized query with concrete values."""

    values: dict = Field(default_factory=dict, description="parameter name -> value")
    use_cache: bool = True
