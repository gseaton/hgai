"""Export one chat turn (a user prompt + its assistant response) to a Note.

Reuses hgai.core.notes.create_note as-is — the custom note id and its YAML
frontmatter (source prompt, vendor/model, timing, tokens) are the only new
logic here; see hgai/core/notes.py's optional `id` parameter, added
specifically so a caller here can supply this module's own id format
instead of the default UUID4.
"""

import random
from typing import Optional

from hgai.core.notes import create_note
from hgai.models.account import AccountInDB
from hgai.models.common import now_utc
from hgai.models.note import NoteCreate, NoteInDB

from . import store
from .models import AgentChatMessageInDB


class NoteExportError(Exception):
    """Raised when a message can't be exported — not found in the given
    session, or not an assistant message (there's nothing meaningful to
    pair a user message with as "the response")."""


def generate_note_id() -> str:
    """hgai-note-chat-<yymmddhhmmss>-<4-digit-random>, per the requested
    format — timestamp for natural chronological sorting/uniqueness, plus a
    short random suffix to avoid a same-second collision if two turns in
    different sessions are exported at once (the Notes collection also has
    a unique index on `id`, so a collision would surface as a clear error
    rather than silently overwriting another note)."""
    now = now_utc()
    return f"hgai-note-chat-{now.strftime('%y%m%d%H%M%S')}-{random.randint(0, 9999):04d}"


def _yaml_scalar(value) -> str:
    """Minimal YAML-safe scalar quoting. Only ever sees short field values
    here (id/vendor/model/ISO timestamps/numbers) — the prompt text itself
    goes through `_yaml_block` instead, since it may be arbitrarily long or
    multi-line."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or text.strip() != text or any(c in text for c in ":#[]{}\"'\n"):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def _yaml_block(key: str, text: str) -> str:
    """A YAML literal block scalar ('|') for the source prompt — safe
    regardless of what punctuation, quotes, or newlines it contains,
    without needing to escape any of it."""
    lines = (text or "").splitlines() or [""]
    body = "\n".join(f"  {line}" for line in lines)
    return f"{key}: |\n{body}"


async def _find_preceding_user_message(
    session_id: str, assistant_message: AgentChatMessageInDB
) -> Optional[AgentChatMessageInDB]:
    """The user prompt that produced `assistant_message` is, by construction
    (see engine.run_turn/run_turn_stream: always insert user then assistant
    as an adjacent pair), the message immediately before it in creation
    order within the same session."""
    messages = await store.list_messages(session_id, limit=1000)
    for i, m in enumerate(messages):
        if m.id == assistant_message.id:
            if i > 0 and messages[i - 1].role == "user":
                return messages[i - 1]
            return None
    return None


def build_note_markdown(note_id: str, prompt: str, assistant_message: AgentChatMessageInDB) -> str:
    duration_seconds = round((assistant_message.duration_ms or 0) / 1000, 3)
    lines = [
        "---",
        f"id: {_yaml_scalar(note_id)}",
        _yaml_block("source_prompt", prompt),
        f"vendor: {_yaml_scalar(assistant_message.vendor_name)}",
        f"model: {_yaml_scalar(assistant_message.model_id)}",
        f"started_at: {_yaml_scalar(assistant_message.started_at.isoformat() if assistant_message.started_at else None)}",
        f"ended_at: {_yaml_scalar(assistant_message.ended_at.isoformat() if assistant_message.ended_at else None)}",
        f"duration_seconds: {_yaml_scalar(duration_seconds)}",
        f"tokens_input: {_yaml_scalar(assistant_message.tokens_input)}",
        f"tokens_output: {_yaml_scalar(assistant_message.tokens_output)}",
        f"tokens_total: {_yaml_scalar(assistant_message.tokens_total)}",
        "---",
        "",
        assistant_message.content,
    ]
    return "\n".join(lines)


async def export_message_to_note(session_id: str, message_id: str, account: AccountInDB) -> NoteInDB:
    assistant_message = await store.get_message(message_id)
    if not assistant_message or assistant_message.session_id != session_id:
        raise NoteExportError(f"Chat message '{message_id}' not found in session '{session_id}'")
    if assistant_message.role != "assistant":
        raise NoteExportError("Only an assistant message can be saved as a Note")

    prompt_message = await _find_preceding_user_message(session_id, assistant_message)
    prompt = prompt_message.content if prompt_message else ""

    note_id = generate_note_id()
    label = (prompt or assistant_message.content or "Chat export").strip().replace("\n", " ")
    if len(label) > 200:
        label = label[:197] + "..."

    text = build_note_markdown(note_id, prompt, assistant_message)
    return await create_note(NoteCreate(label=label, text=text), owner_username=account.username, id=note_id)
