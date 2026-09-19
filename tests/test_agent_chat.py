"""Tests for AI Agent vendor/model CRUD (hgai_module_agentchat).

Uses a small in-memory fake Motor-like database — same approach as
tests/test_shql_history.py — general enough to support the query operators
this module's store.py actually issues ($and/$or/$all/$regex, $set/$inc).
"""

import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from hgai_module_agentchat import engine, store
from hgai_module_agentchat.crypto import decrypt_api_key, encrypt_api_key, last4
from hgai_module_agentchat.models import (
    AgentChatSessionCreate,
    AgentModelCreate,
    AgentModelUpdate,
    AgentVendorCreate,
    AgentVendorName,
    AgentVendorUpdate,
)


def _matches(doc, query):
    if not query:
        return True
    for key, cond in query.items():
        if key == "$and":
            if not all(_matches(doc, c) for c in cond):
                return False
        elif key == "$or":
            if not any(_matches(doc, c) for c in cond):
                return False
        elif isinstance(cond, dict) and "$all" in cond:
            if not set(cond["$all"]).issubset(set(doc.get(key, []))):
                return False
        elif isinstance(cond, dict) and "$regex" in cond:
            flags = re.IGNORECASE if cond.get("$options") == "i" else 0
            if not re.search(cond["$regex"], str(doc.get(key, "")), flags):
                return False
        else:
            if doc.get(key) != cond:
                return False
    return True


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)
        self._skip = 0
        self._limit = None

    def skip(self, n):
        self._skip = n
        return self

    def limit(self, n):
        self._limit = n
        return self

    def sort(self, spec):
        for field, direction in reversed(spec):
            self._docs.sort(key=lambda d: d.get(field), reverse=(direction < 0))
        return self

    async def to_list(self, length=None):
        docs = self._docs[self._skip:]
        if self._limit is not None:
            docs = docs[: self._limit]
        return [dict(d) for d in docs]


class _FakeCollection:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def find_one(self, query):
        for d in self.docs:
            if _matches(d, query):
                return dict(d)
        return None

    def find(self, query):
        return _FakeCursor([d for d in self.docs if _matches(d, query)])

    async def count_documents(self, query):
        return sum(1 for d in self.docs if _matches(d, query))

    async def delete_one(self, query):
        for i, d in enumerate(self.docs):
            if _matches(d, query):
                self.docs.pop(i)
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    async def delete_many(self, query):
        before = len(self.docs)
        self.docs = [d for d in self.docs if not _matches(d, query)]
        return SimpleNamespace(deleted_count=before - len(self.docs))

    async def find_one_and_update(self, query, update, return_document=True):
        for d in self.docs:
            if _matches(d, query):
                if "$set" in update:
                    d.update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        d[k] = d.get(k, 0) + v
                return dict(d)
        return None


@pytest.fixture
def fake_db():
    db = {
        "agent_vendors": _FakeCollection(),
        "agent_models": _FakeCollection(),
        "agent_chat_sessions": _FakeCollection(),
        "agent_chat_messages": _FakeCollection(),
    }
    with patch("hgai_module_agentchat.store._db", return_value=db):
        yield db


# ─── crypto ─────────────────────────────────────────────────────────────────

def test_encrypt_decrypt_roundtrip():
    ciphertext = encrypt_api_key("sk-super-secret-key")
    assert ciphertext != "sk-super-secret-key"
    assert decrypt_api_key(ciphertext) == "sk-super-secret-key"


def test_last4():
    assert last4("sk-abcd1234") == "1234"
    assert last4("ab") == "ab"


# ─── vendors ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_vendor_encrypts_key_and_never_returns_plaintext(fake_db):
    vendor = await store.create_vendor(
        AgentVendorCreate(name=AgentVendorName.anthropic, label="Anthropic", api_key="sk-real-key-9999"),
        created_by="admin",
    )
    assert vendor.api_key_last4 == "9999"
    assert vendor.api_key_encrypted != "sk-real-key-9999"
    # Field(exclude=True) must actually strip it from any serialization.
    assert "api_key_encrypted" not in vendor.model_dump()

    fetched = await store.get_decrypted_api_key(vendor.id)
    assert fetched == "sk-real-key-9999"


@pytest.mark.asyncio
async def test_create_vendor_without_key_is_a_placeholder(fake_db):
    vendor = await store.create_vendor(
        AgentVendorCreate(name=AgentVendorName.openai, label="OpenAI", enabled=False),
        created_by="system",
    )
    assert vendor.api_key_last4 == ""
    assert await store.get_decrypted_api_key(vendor.id) is None


@pytest.mark.asyncio
async def test_list_vendors_search_and_tags(fake_db):
    await store.create_vendor(AgentVendorCreate(name=AgentVendorName.anthropic, label="Anthropic", tags=["prod"]), created_by="admin")
    await store.create_vendor(AgentVendorCreate(name=AgentVendorName.openai, label="OpenAI", tags=["dev"]), created_by="admin")

    total, items = await store.list_vendors(search="anthro")
    assert total == 1
    assert items[0].label == "Anthropic"

    total, items = await store.list_vendors(tags=["dev"])
    assert total == 1
    assert items[0].label == "OpenAI"


@pytest.mark.asyncio
async def test_update_vendor_rotates_key_and_tracks_mutation(fake_db):
    vendor = await store.create_vendor(
        AgentVendorCreate(name=AgentVendorName.xai, label="xAI", api_key="sk-old-0001"),
        created_by="admin",
    )
    updated = await store.update_vendor(
        vendor.id, AgentVendorUpdate(label="xAI (Grok)", api_key="sk-new-2222"), updated_by="admin",
    )
    assert updated.label == "xAI (Grok)"
    assert updated.api_key_last4 == "2222"
    assert await store.get_decrypted_api_key(vendor.id) == "sk-new-2222"
    assert updated.version == 2
    assert len(updated.mutations) == 2  # create + this mutate
    assert updated.mutations[-1]["mutation"] == "mutate"
    # The rotated key must never appear in the audit trail.
    delta_fields = {d["field"] for d in updated.mutations[-1]["delta"]}
    assert "api_key" not in delta_fields
    assert "api_key_encrypted" not in delta_fields


@pytest.mark.asyncio
async def test_update_vendor_without_api_key_leaves_existing_key_untouched(fake_db):
    vendor = await store.create_vendor(
        AgentVendorCreate(name=AgentVendorName.anthropic, label="Anthropic", api_key="sk-keep-me-0001"),
        created_by="admin",
    )
    updated = await store.update_vendor(vendor.id, AgentVendorUpdate(enabled=False), updated_by="admin")
    assert updated.enabled is False
    assert await store.get_decrypted_api_key(vendor.id) == "sk-keep-me-0001"


@pytest.mark.asyncio
async def test_delete_vendor(fake_db):
    vendor = await store.create_vendor(AgentVendorCreate(name=AgentVendorName.anthropic, label="Anthropic"), created_by="admin")
    assert await store.delete_vendor(vendor.id) is True
    assert await store.get_vendor(vendor.id) is None
    assert await store.delete_vendor(vendor.id) is False


# ─── models ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_list_models_by_vendor(fake_db):
    vendor = await store.create_vendor(AgentVendorCreate(name=AgentVendorName.anthropic, label="Anthropic"), created_by="admin")
    other_vendor = await store.create_vendor(AgentVendorCreate(name=AgentVendorName.openai, label="OpenAI"), created_by="admin")

    await store.create_model(AgentModelCreate(vendor_id=vendor.id, model_id="claude-sonnet-5", label="Claude Sonnet 5"), created_by="admin")
    await store.create_model(AgentModelCreate(vendor_id=other_vendor.id, model_id="gpt-5", label="GPT-5"), created_by="admin")

    total, items = await store.list_models(vendor_id=vendor.id)
    assert total == 1
    assert items[0].model_id == "claude-sonnet-5"


@pytest.mark.asyncio
async def test_list_models_enabled_only(fake_db):
    vendor = await store.create_vendor(AgentVendorCreate(name=AgentVendorName.anthropic, label="Anthropic"), created_by="admin")
    await store.create_model(AgentModelCreate(vendor_id=vendor.id, model_id="on", label="On", enabled=True), created_by="admin")
    await store.create_model(AgentModelCreate(vendor_id=vendor.id, model_id="off", label="Off", enabled=False), created_by="admin")

    total, items = await store.list_models(enabled_only=True)
    assert total == 1
    assert items[0].model_id == "on"


@pytest.mark.asyncio
async def test_update_and_delete_model(fake_db):
    vendor = await store.create_vendor(AgentVendorCreate(name=AgentVendorName.anthropic, label="Anthropic"), created_by="admin")
    model = await store.create_model(AgentModelCreate(vendor_id=vendor.id, model_id="m1", label="M1"), created_by="admin")

    updated = await store.update_model(model.id, AgentModelUpdate(label="M1 Renamed", default_temperature=0.7), updated_by="admin")
    assert updated.label == "M1 Renamed"
    assert updated.default_temperature == 0.7

    assert await store.delete_model(model.id) is True
    assert await store.get_model(model.id) is None


# ─── default catalog seeding ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seed_defaults_creates_disabled_placeholder_catalog(fake_db):
    await store.seed_defaults()

    total, vendors = await store.list_vendors(limit=100)
    assert total == 3
    names = {v.name for v in vendors}
    assert names == {AgentVendorName.anthropic, AgentVendorName.openai, AgentVendorName.xai}
    assert all(v.enabled is False for v in vendors)
    assert all(v.api_key_last4 == "" for v in vendors)

    total, models = await store.list_models(limit=100)
    assert total == 4  # 2 anthropic + 1 openai + 1 xai
    assert all(m.enabled is False for m in models)


@pytest.mark.asyncio
async def test_seed_defaults_is_idempotent_and_preserves_admin_edits(fake_db):
    await store.seed_defaults()
    total, vendors = await store.list_vendors(limit=100)
    anthropic = next(v for v in vendors if v.name == AgentVendorName.anthropic)

    # Admin enables it and adds a real key.
    await store.update_vendor(anthropic.id, AgentVendorUpdate(enabled=True, api_key="sk-real-9999"), updated_by="admin")

    # Re-running seeding (as happens on every server restart) must not
    # touch the now-configured vendor or duplicate any rows.
    await store.seed_defaults()
    total, vendors = await store.list_vendors(limit=100)
    assert total == 3
    anthropic_again = await store.get_vendor(anthropic.id)
    assert anthropic_again.enabled is True
    assert await store.get_decrypted_api_key(anthropic.id) == "sk-real-9999"


# ─── chat sessions/messages (store) ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_and_get_session(fake_db):
    session = await store.create_session(AgentChatSessionCreate(model_id="m1", title="My chat"), owner_username="alice")
    assert session.owner_username == "alice"
    assert session.title == "My chat"
    assert session.message_count == 0
    assert session.last_message_at is None

    fetched = await store.get_session(session.id)
    assert fetched.id == session.id


@pytest.mark.asyncio
async def test_list_sessions_scoped_per_owner(fake_db):
    await store.create_session(AgentChatSessionCreate(model_id="m1"), owner_username="alice")
    await store.create_session(AgentChatSessionCreate(model_id="m1"), owner_username="bob")

    total, items = await store.list_sessions("alice")
    assert total == 1
    assert items[0].owner_username == "alice"


@pytest.mark.asyncio
async def test_touch_session_updates_count_and_timestamp(fake_db):
    session = await store.create_session(AgentChatSessionCreate(model_id="m1"), owner_username="alice")
    await store.touch_session(session.id)
    await store.touch_session(session.id)
    updated = await store.get_session(session.id)
    assert updated.message_count == 2
    assert updated.last_message_at is not None


@pytest.mark.asyncio
async def test_delete_session_also_deletes_its_messages(fake_db):
    session = await store.create_session(AgentChatSessionCreate(model_id="m1"), owner_username="alice")
    await store.create_message(session_id=session.id, role="user", content="hi")
    await store.create_message(session_id=session.id, role="assistant", content="hello")

    assert await store.delete_session(session.id) is True
    assert await store.get_session(session.id) is None
    assert await store.list_messages(session.id) == []


@pytest.mark.asyncio
async def test_list_messages_ordered_oldest_first(fake_db):
    session = await store.create_session(AgentChatSessionCreate(model_id="m1"), owner_username="alice")
    await store.create_message(session_id=session.id, role="user", content="first")
    await store.create_message(session_id=session.id, role="assistant", content="second")
    messages = await store.list_messages(session.id)
    assert [m.content for m in messages] == ["first", "second"]


# ─── engine (mocked Agent — no real vendor calls) ───────────────────────────

class _FakeAgent:
    """Mirrors the real Agno Agent.arun dual-dispatch: called plainly it
    returns a coroutine (await it for the RunOutput); called with
    stream=True it returns an async generator directly (no await needed) —
    exactly the calling convention hgai_module_agentchat.engine relies on."""

    def __init__(self, run_output=None, stream_events=None, stream_error=None):
        self._run_output = run_output
        self._stream_events = stream_events or []
        self._stream_error = stream_error

    def arun(self, input, session_id=None, user_id=None, stream=False, stream_events=False):
        if stream:
            return self._stream()
        return self._run()

    async def _run(self):
        return self._run_output

    async def _stream(self):
        if self._stream_error:
            raise self._stream_error
        for e in self._stream_events:
            yield e


def _fake_account():
    from hgai.models.account import AccountInDB, AccountPermissions
    return AccountInDB(
        username="alice", email=None, description="", roles=["user"],
        permissions=AccountPermissions(graphs=["*"], operations=["read"]),
        password_hash="", tags=[], status="active",
    )


@pytest.mark.asyncio
async def test_run_turn_persists_user_and_assistant_messages_with_metrics(fake_db):
    vendor = await store.create_vendor(AgentVendorCreate(name=AgentVendorName.anthropic, label="Anthropic", api_key="sk-1"), created_by="admin")
    model = await store.create_model(AgentModelCreate(vendor_id=vendor.id, model_id="claude-sonnet-5", label="Sonnet"), created_by="admin")
    session = await store.create_session(AgentChatSessionCreate(model_id=model.id), owner_username="alice")

    fake_agent = _FakeAgent(run_output=SimpleNamespace(
        content="Hi there!", metrics=SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15),
    ))
    with patch("hgai_module_agentchat.engine.build_agent", AsyncMock(return_value=fake_agent)):
        assistant_msg = await engine.run_turn(session, vendor, model, _fake_account(), "hello")

    assert assistant_msg.role == "assistant"
    assert assistant_msg.content == "Hi there!"
    assert assistant_msg.tokens_input == 10
    assert assistant_msg.tokens_output == 5
    assert assistant_msg.tokens_total == 15
    assert assistant_msg.vendor_name == "anthropic"
    assert assistant_msg.model_id == "claude-sonnet-5"

    stored = await store.list_messages(session.id)
    assert [m.role for m in stored] == ["user", "assistant"]
    assert stored[0].content == "hello"

    touched = await store.get_session(session.id)
    assert touched.message_count == 1
    assert touched.last_message_at is not None


@pytest.mark.asyncio
async def test_run_turn_stream_yields_deltas_and_persists_final_completed_content(fake_db):
    from agno.run.agent import RunCompletedEvent, RunContentEvent

    vendor = await store.create_vendor(AgentVendorCreate(name=AgentVendorName.anthropic, label="Anthropic", api_key="sk-1"), created_by="admin")
    model = await store.create_model(AgentModelCreate(vendor_id=vendor.id, model_id="claude-sonnet-5", label="Sonnet"), created_by="admin")
    session = await store.create_session(AgentChatSessionCreate(model_id=model.id), owner_username="alice")

    fake_agent = _FakeAgent(stream_events=[
        RunContentEvent(content="Hel"),
        RunContentEvent(content="lo"),
        RunCompletedEvent(content="Hello", metrics=SimpleNamespace(input_tokens=1, output_tokens=2, total_tokens=3)),
    ])
    frames = []
    with patch("hgai_module_agentchat.engine.build_agent", AsyncMock(return_value=fake_agent)):
        async for frame in engine.run_turn_stream(session, vendor, model, _fake_account(), "count"):
            frames.append(frame)

    delta_frames = [f for f in frames if '"delta"' in f]
    assert len(delta_frames) == 2
    assert frames[-1].startswith("event: done")

    stored = await store.list_messages(session.id)
    assert [m.role for m in stored] == ["user", "assistant"]
    # The final content comes from RunCompletedEvent, not concatenated deltas.
    assert stored[1].content == "Hello"
    assert stored[1].tokens_total == 3


@pytest.mark.asyncio
async def test_run_turn_stream_emits_error_frame_and_persists_nothing_on_failure(fake_db):
    vendor = await store.create_vendor(AgentVendorCreate(name=AgentVendorName.anthropic, label="Anthropic", api_key="sk-1"), created_by="admin")
    model = await store.create_model(AgentModelCreate(vendor_id=vendor.id, model_id="claude-sonnet-5", label="Sonnet"), created_by="admin")
    session = await store.create_session(AgentChatSessionCreate(model_id=model.id), owner_username="alice")

    fake_agent = _FakeAgent(stream_error=RuntimeError("vendor exploded"))
    frames = []
    with patch("hgai_module_agentchat.engine.build_agent", AsyncMock(return_value=fake_agent)):
        async for frame in engine.run_turn_stream(session, vendor, model, _fake_account(), "count"):
            frames.append(frame)

    assert len(frames) == 1
    assert frames[0].startswith("event: error")
    assert "vendor exploded" in frames[0]
    assert await store.list_messages(session.id) == []


@pytest.mark.asyncio
async def test_build_agent_raises_when_vendor_has_no_key(fake_db):
    vendor = await store.create_vendor(AgentVendorCreate(name=AgentVendorName.anthropic, label="Anthropic"), created_by="admin")
    model = await store.create_model(AgentModelCreate(vendor_id=vendor.id, model_id="claude-sonnet-5", label="Sonnet"), created_by="admin")
    with pytest.raises(ValueError, match="no API key configured"):
        await engine.build_agent(vendor, model, _fake_account())


# ─── notes export ────────────────────────────────────────────────────────────
# export_message_to_note()'s happy path ends in hgai.core.notes.create_note,
# which is storage-backed (get_storage()) — per this project's convention
# (see tests/test_notes.py's docstring), that's verified live rather than
# unit tested. What's pure and worth testing here: id format, frontmatter
# construction/escaping, message pairing, and the error paths that raise
# before ever reaching create_note.

import re as _re

from hgai_module_agentchat import notes_export


def test_generate_note_id_format():
    note_id = notes_export.generate_note_id()
    assert _re.fullmatch(r"hgai-note-chat-\d{12}-\d{4}", note_id)


def test_build_note_markdown_frontmatter_and_body():
    from hgai_module_agentchat.models import AgentChatMessageInDB

    msg = AgentChatMessageInDB(
        id="m1", session_id="s1", role="assistant", content="The answer is 42.",
        vendor_name="anthropic", model_id="claude-sonnet-5",
        started_at=None, ended_at=None, duration_ms=1234,
        tokens_input=100, tokens_output=20, tokens_total=120,
    )
    md = notes_export.build_note_markdown("hgai-note-chat-260918143207-4821", "What is the answer?", msg)

    assert md.startswith("---\n")
    assert "id: hgai-note-chat-260918143207-4821" in md
    assert "source_prompt: |\n  What is the answer?" in md
    assert "vendor: anthropic" in md
    assert "model: claude-sonnet-5" in md
    assert "duration_seconds: 1.234" in md
    assert "tokens_input: 100" in md
    assert "tokens_output: 20" in md
    assert "tokens_total: 120" in md
    # Frontmatter block closes before the response body.
    assert md.count("---") == 2
    assert md.rstrip().endswith("The answer is 42.")


def test_build_note_markdown_escapes_special_characters_in_prompt():
    from hgai_module_agentchat.models import AgentChatMessageInDB

    msg = AgentChatMessageInDB(id="m1", session_id="s1", role="assistant", content="ok", duration_ms=0)
    prompt = "line one\nline two: with a colon"
    md = notes_export.build_note_markdown("id1", prompt, msg)
    # A literal block scalar needs no escaping — colons/newlines are safe as-is.
    assert "source_prompt: |\n  line one\n  line two: with a colon" in md


def test_yaml_scalar_quotes_values_needing_it():
    assert notes_export._yaml_scalar(None) == "null"
    assert notes_export._yaml_scalar(True) == "true"
    assert notes_export._yaml_scalar(42) == "42"
    assert notes_export._yaml_scalar("plain") == "plain"
    assert notes_export._yaml_scalar("has: colon") == '"has: colon"'
    assert notes_export._yaml_scalar("") == '""'


@pytest.mark.asyncio
async def test_find_preceding_user_message_pairs_adjacent_turn(fake_db):
    session = await store.create_session(AgentChatSessionCreate(model_id="m1"), owner_username="alice")
    await store.create_message(session_id=session.id, role="user", content="first prompt")
    assistant1 = await store.create_message(session_id=session.id, role="assistant", content="first reply")
    await store.create_message(session_id=session.id, role="user", content="second prompt")
    assistant2 = await store.create_message(session_id=session.id, role="assistant", content="second reply")

    paired1 = await notes_export._find_preceding_user_message(session.id, assistant1)
    paired2 = await notes_export._find_preceding_user_message(session.id, assistant2)
    assert paired1.content == "first prompt"
    assert paired2.content == "second prompt"


@pytest.mark.asyncio
async def test_export_message_to_note_rejects_user_role(fake_db):
    session = await store.create_session(AgentChatSessionCreate(model_id="m1"), owner_username="alice")
    user_msg = await store.create_message(session_id=session.id, role="user", content="hi")
    with pytest.raises(notes_export.NoteExportError, match="Only an assistant message"):
        await notes_export.export_message_to_note(session.id, user_msg.id, _fake_account())


@pytest.mark.asyncio
async def test_export_message_to_note_rejects_unknown_message(fake_db):
    session = await store.create_session(AgentChatSessionCreate(model_id="m1"), owner_username="alice")
    with pytest.raises(notes_export.NoteExportError, match="not found"):
        await notes_export.export_message_to_note(session.id, "does-not-exist", _fake_account())


@pytest.mark.asyncio
async def test_export_message_to_note_rejects_message_from_another_session(fake_db):
    session_a = await store.create_session(AgentChatSessionCreate(model_id="m1"), owner_username="alice")
    session_b = await store.create_session(AgentChatSessionCreate(model_id="m1"), owner_username="alice")
    assistant_in_b = await store.create_message(session_id=session_b.id, role="assistant", content="reply")
    with pytest.raises(notes_export.NoteExportError, match="not found"):
        await notes_export.export_message_to_note(session_a.id, assistant_in_b.id, _fake_account())
