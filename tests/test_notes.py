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


# ── Scopes: private / protected / protected-edit / public / public-edit ──────

import itertools

import pytest

from hgai.core.notes import note_access
from hgai.models.note import NoteCreate, NoteScope
from hgai_module_storage_mongodb.stores.notes import _scope_clause, _visibility_clause

SCOPES = ["private", "protected", "protected-edit", "public", "public-edit"]


def _scoped(scope, acl=None, owner="alice"):
    return NoteInDB(id="n1", owner_username=owner, label="T", text="", scope=scope, acl=acl or [], mutations=[])


# (scope, viewer-grant holder "bob", editor-grant holder "carol", stranger "mallory")
EXPECTED = {
    "private":        ("none",   "none",   "none"),
    "protected":      ("viewer", "editor", "none"),
    "protected-edit": ("editor", "editor", "none"),
    "public":         ("viewer", "editor", "viewer"),
    "public-edit":    ("editor", "editor", "editor"),
}


@pytest.mark.parametrize("scope", SCOPES)
def test_scope_access_matrix(scope):
    note = _scoped(scope, acl=[NoteGrant(username="bob", role=NoteRole.viewer), NoteGrant(username="carol", role=NoteRole.editor)])
    bob, carol, mallory = EXPECTED[scope]
    assert (note_access(note, "alice"), can_view_note(note, "alice"), can_edit_note(note, "alice")) == ("owner", True, True)
    for user, want in (("bob", bob), ("carol", carol), ("mallory", mallory)):
        got = note_access(note, user)
        assert (got or "none") == want, f"{scope}/{user}"
        assert can_view_note(note, user) is (want != "none")
        assert can_edit_note(note, user) is (want == "editor")


def test_a_note_without_a_stored_scope_behaves_as_it_always_did():
    """Notes saved before scopes existed read as 'protected': owner + share list."""
    legacy = NoteInDB(id="n1", owner_username="alice", label="T", acl=[NoteGrant(username="bob")], mutations=[])
    assert legacy.scope == "protected"
    assert can_view_note(legacy, "bob") and not can_edit_note(legacy, "bob")
    assert not can_view_note(legacy, "mallory")


def test_new_notes_start_private_but_the_model_default_is_protected():
    assert NoteCreate(label="x").scope == "private"
    assert NoteCreate(label="x", scope="public-edit").scope == "public-edit"
    with pytest.raises(ValueError):
        NoteCreate(label="x", scope="everyone")


# The Mongo visibility query must agree with note_access for every combination.
def _matches(doc, query):
    for key, cond in query.items():
        if key == "$or":
            if not any(_matches(doc, c) for c in cond):
                return False
        elif key == "$and":
            if not all(_matches(doc, c) for c in cond):
                return False
        elif key == "acl.username":
            if cond not in [g["username"] for g in doc.get("acl", [])]:
                return False
        else:
            present, value = key in doc, doc.get(key)
            if isinstance(cond, dict):
                for op, arg in cond.items():
                    if op == "$in" and value not in arg:
                        return False
                    if op == "$ne" and value == arg:
                        return False
                    if op == "$exists" and present != arg:
                        return False
            elif value != cond:
                return False
    return True


@pytest.mark.parametrize("scope", SCOPES + [None])
def test_visibility_query_matches_note_access(scope):
    acls = [[], [NoteGrant(username="bob")], [NoteGrant(username="bob", role=NoteRole.editor), NoteGrant(username="carol")]]
    for acl, user in itertools.product(acls, ["alice", "bob", "carol", "mallory"]):
        note = _scoped(scope, acl=acl) if scope else NoteInDB(id="n", owner_username="alice", label="T", acl=acl, mutations=[])
        doc = note.model_dump()
        if scope is None:
            doc.pop("scope")           # exactly what a pre-scope document looks like
        assert _matches(doc, _visibility_clause(user)) is can_view_note(note, user), (scope, acl, user)


def test_scope_filter_treats_a_missing_scope_as_protected():
    legacy = {"owner_username": "a"}
    assert _matches(legacy, _scope_clause("protected"))
    assert not _matches(legacy, _scope_clause("private"))
    assert _matches({"scope": "public"}, _scope_clause("public"))
    assert not _matches({"scope": "public"}, _scope_clause("protected"))
