"""Tests for media models and mesh-qualified media_id parsing."""

import pytest

from hgai.core.media import parse_media_id, _extract_local_ids
from hgai.models.media import Media, MediaRef


# ─── parse_media_id ────────────────────────────────────────────────────────────

def test_parse_media_id_local():
    server_id, local_id = parse_media_id("a1b2c3")
    assert server_id is None
    assert local_id == "a1b2c3"


def test_parse_media_id_remote():
    server_id, local_id = parse_media_id("bauhaus-strix/a1b2c3")
    assert server_id == "bauhaus-strix"
    assert local_id == "a1b2c3"


def test_parse_media_id_only_splits_on_first_slash():
    """A local id is constructed to never contain '/', but this guards against
    any accidental extra segments being swallowed into the server id instead
    of silently mis-parsing the local id."""
    server_id, local_id = parse_media_id("server-a/nested/looking-id")
    assert server_id == "server-a"
    assert local_id == "nested/looking-id"


# ─── _extract_local_ids ─────────────────────────────────────────────────────────

def test_extract_local_ids_skips_remote():
    refs = [
        MediaRef(media_id="local-1"),
        MediaRef(media_id="remote-server/local-2"),
    ]
    assert _extract_local_ids(refs) == {"local-1"}


def test_extract_local_ids_accepts_plain_dicts():
    """Patch data coming through .model_dump() is plain dicts, not MediaRef
    instances — the helper must handle both."""
    refs = [{"media_id": "local-1"}, {"media_id": "server/local-2"}]
    assert _extract_local_ids(refs) == {"local-1"}


def test_extract_local_ids_empty():
    assert _extract_local_ids(None) == set()
    assert _extract_local_ids([]) == set()


# ─── Model defaults ──────────────────────────────────────────────────────────

def test_media_ref_defaults():
    ref = MediaRef(media_id="abc123")
    assert ref.role is None
    assert ref.content_type is None
    assert ref.attributes == {}


def test_media_defaults():
    media = Media(
        id="abc123",
        content_type="image/png",
        size_bytes=1024,
        checksum="deadbeef",
        uploaded_by="admin",
    )
    assert media.ref_count == 0
    assert media.filename is None
    assert media.status == "active"
