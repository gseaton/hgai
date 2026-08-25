"""Media (binary file) data models.

A Media record is the metadata for one uploaded file; its bytes live in the
storage backend's blob store (GridFS for the Mongo backend), keyed by the
same id. Hypernodes/hyperedges never embed bytes — they carry a MediaRef
pointing at a Media record's id instead, so the same file can be attached to
many entities without duplicating storage.

media_id format (see hgai/core/media.py for the parser):
    "<media-identifier>"                    - local media, owned by this server
    "<mesh-hgai-server>/<media-identifier>" - remote media, owned by another mesh server
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from hgai.models.common import Status, TimestampedModel


class Media(TimestampedModel):
    """Metadata for one uploaded binary file. Stored in the `media` collection."""

    id: str = Field(..., description="Media identifier (never contains '/')")
    content_type: str = Field(..., description="MIME type of the uploaded content")
    filename: Optional[str] = Field(default=None, description="Original filename, if provided")
    size_bytes: int = Field(..., description="Size of the stored content in bytes")
    checksum: str = Field(..., description="sha256 hex digest of the content")
    uploaded_by: str = Field(..., description="Username of the uploading account")
    ref_count: int = Field(default=0, description="Number of entities currently referencing this media")


class MediaResponse(Media):
    """Media metadata as returned by the API."""
    pass


class MediaUpdate(BaseModel):
    """Schema for updating a media record's editable metadata (not its bytes)."""

    filename: Optional[str] = None
    tags: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None
    status: Optional[Status] = None


class MediaRef(BaseModel):
    """A reference to a Media record, embedded in a hypernode's or hyperedge's `media` list."""

    media_id: str = Field(..., description="\"<id>\" (local) or \"<server>/<id>\" (mesh-remote)")
    role: Optional[str] = Field(default=None, description="How this media relates to the entity, e.g. 'profile-photo', 'attachment'")
    content_type: Optional[str] = Field(default=None, description="Cached MIME type, avoids a round-trip for display")
    filename: Optional[str] = Field(default=None, description="Cached original filename")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Free-form extension, same convention as entity-level attributes")

    class Config:
        populate_by_name = True
