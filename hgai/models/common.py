"""Common base models and types for HypergraphAI."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Status(str, Enum):
    active = "active"
    draft = "draft"
    archived = "archived"


class HgaiBaseModel(BaseModel):
    """Base model with common HypergraphAI fields."""

    tags: List[str] = Field(default_factory=list, description="Searchable string tags")
    status: Status = Field(default=Status.active, description="Artifact status")
    attributes: Dict[str, Any] = Field(
        default_factory=dict, description="Flexible document-based attributes"
    )

    class Config:
        populate_by_name = True
        use_enum_values = True


class TimestampedModel(HgaiBaseModel):
    """Model with system timestamps."""

    system_created: Optional[datetime] = Field(default=None)
    system_updated: Optional[datetime] = Field(default=None)
    created_by: Optional[str] = Field(default=None)
    version: int = Field(default=1)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class PaginationParams(BaseModel):
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=500)


class PaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[Any]
