"""Note (rich per-account document) data models.

A Note is a first-class resource independent of the hypergraph model —
closer in shape to Quill's flat notes (label, tags, Markdown text) than to
a hypernode/hyperedge. It lives at the same tier as Accounts/Spaces/Media,
not inside any particular hypergraph, since a personal document isn't
naturally an N-ary fact about graph entities.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from hgai.models.common import MutationRecord, Status, TimestampedModel
from hgai.models.media import MediaRef


class NoteRole(str, Enum):
    """Access level granted to one other account on one note.

    Deliberately just two levels (not the four-level Space hierarchy) —
    a note's owner already has full control implicitly, so a grant only
    ever needs to say "can this other account read it, or also change it."
    """

    viewer = "viewer"
    editor = "editor"


class NoteGrant(BaseModel):
    """One entry in a note's `acl`: one other account's access level.

    The owner is never listed here — ownership is tracked separately via
    `owner_username` and always implies full (view + edit + share + delete)
    access, so there's nothing to express by also granting the owner a role.
    """

    username: str = Field(..., description="Account username granted access")
    role: NoteRole = Field(default=NoteRole.viewer)


class NoteBase(TimestampedModel):
    """Base note fields.

    `label` is the note's primary display/identifying title, unchanged by
    this field's addition. `name` is a separate, optional human-readable
    name/subtitle — shown alongside (never instead of) the label in
    listings and the folder sidebar, mirroring Quill's own label/name
    distinction. Neither field is enforced unique at the storage layer;
    `id` (below) is the only actual unique identifier.
    """

    label: str = Field(..., max_length=200, description="Display title")
    name: str = Field(default="", max_length=200, description="Optional human-readable name/subtitle")
    text: str = Field(default="", description="Note body (Markdown)")
    media: List[MediaRef] = Field(default_factory=list, description="Embedded/attached media references")

    @field_validator("label")
    @classmethod
    def _clean_label(cls, value: str) -> str:
        return value.strip()

    @field_validator("name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        return value.strip()


class NoteCreate(NoteBase):
    """Schema for creating a note. The creating account becomes its owner."""


class NoteUpdate(BaseModel):
    """Schema for updating a note's own fields (all optional). Sharing is
    managed separately via the share/unshare endpoints, not through this —
    keeps "who changed the content" and "who changed who can see it" as
    two distinctly auditable kinds of action."""

    label: Optional[str] = None
    name: Optional[str] = None
    text: Optional[str] = None
    media: Optional[List[MediaRef]] = None
    tags: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None
    status: Optional[Status] = None


class NoteInDB(NoteBase):
    """Note as stored."""

    id: str = Field(..., description="Note identifier (UUID4)")
    owner_username: str = Field(..., description="Account that created this note; always has full access")
    acl: List[NoteGrant] = Field(default_factory=list, description="Other accounts granted view/edit access")
    mutations: List[MutationRecord] = Field(default_factory=list, description="Audit trail of create/mutate/share events")

    class Config:
        populate_by_name = True


class NoteResponse(NoteInDB):
    """Note API response."""
    pass


class ShareNoteRequest(BaseModel):
    """Request body for granting (or replacing) one account's access to a note."""

    username: str = Field(..., description="Account username to grant access to")
    role: NoteRole = Field(default=NoteRole.viewer)
