"""Tests for the Note engine's pure permission-check logic.

create_note/update_note/share_note/etc. are storage-backed (get_storage()),
so per this project's convention they're verified live rather than unit
tested here — see the mutation history for the live verification. What's
pure and worth a real unit test is can_view_note/can_edit_note: given a
NoteInDB and a username, do they correctly read owner_username/acl.
"""

from hgai.core.notes import can_edit_note, can_view_note
from hgai.models.note import NoteGrant, NoteInDB, NoteRole


def _note(owner="alice", acl=None):
    return NoteInDB(
        id="n1", owner_username=owner, label="Test", text="",
        acl=acl or [], mutations=[],
    )


def test_owner_can_view():
    note = _note(owner="alice")
    assert can_view_note(note, "alice") is True


def test_owner_can_edit():
    note = _note(owner="alice")
    assert can_edit_note(note, "alice") is True


def test_stranger_cannot_view():
    note = _note(owner="alice")
    assert can_view_note(note, "mallory") is False


def test_stranger_cannot_edit():
    note = _note(owner="alice")
    assert can_edit_note(note, "mallory") is False


def test_viewer_grant_can_view_not_edit():
    note = _note(owner="alice", acl=[NoteGrant(username="bob", role=NoteRole.viewer)])
    assert can_view_note(note, "bob") is True
    assert can_edit_note(note, "bob") is False


def test_editor_grant_can_view_and_edit():
    note = _note(owner="alice", acl=[NoteGrant(username="carol", role=NoteRole.editor)])
    assert can_view_note(note, "carol") is True
    assert can_edit_note(note, "carol") is True


def test_grant_for_one_user_does_not_affect_another():
    note = _note(owner="alice", acl=[NoteGrant(username="bob", role=NoteRole.editor)])
    assert can_view_note(note, "carol") is False
    assert can_edit_note(note, "carol") is False


def test_multiple_grants_independently_checked():
    note = _note(owner="alice", acl=[
        NoteGrant(username="bob", role=NoteRole.viewer),
        NoteGrant(username="carol", role=NoteRole.editor),
    ])
    assert can_view_note(note, "bob") is True
    assert can_edit_note(note, "bob") is False
    assert can_view_note(note, "carol") is True
    assert can_edit_note(note, "carol") is True
