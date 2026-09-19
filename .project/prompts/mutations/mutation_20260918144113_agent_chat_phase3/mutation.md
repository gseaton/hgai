# Mutation Log

## Created
- **hgai_module_agentchat/notes_export.py** — `generate_note_id()` (`hgai-note-chat-<yymmddhhmmss>-<4-digit-random>`), `build_note_markdown()` (YAML frontmatter with `id`/`source_prompt`/`vendor`/`model`/`started_at`/`ended_at`/`duration_seconds`/`tokens_input`/`tokens_output`/`tokens_total`, then the response body), `_yaml_scalar()`/`_yaml_block()` (minimal safe YAML value/block-scalar formatting), `_find_preceding_user_message()` (pairs an assistant message with the user prompt that produced it, by adjacency in creation order), and `export_message_to_note()` (the orchestrating function; raises `NoteExportError` for an unknown message, a message from a different session, or a non-assistant message).

## Modified
- **hgai/core/notes.py** — `create_note()` gained an optional `id: Optional[str] = None` parameter (defaults to the existing `uuid.uuid4().hex` behavior when omitted), so a caller can supply a custom id instead. This is the only change to core Notes code; `NoteCreate`'s public schema is untouched.
- **hgai_module_agentchat/api_router.py** — Added `POST /agent/sessions/{session_id}/messages/{message_id}/save-note` (owner-gated via the existing `_get_owned_session`), returning the created `NoteResponse`.
- **tests/test_agent_chat.py** — Added 9 tests for `notes_export.py`: note-id format, frontmatter/body construction (including special-character escaping in the prompt), message-pairing logic, and all three `NoteExportError` paths. Following this project's own established convention (see `tests/test_notes.py`'s docstring: storage-backed `create_note` logic is verified live, not unit tested), the happy path that actually calls `create_note` was verified live instead (see summary.md) rather than added as a mocked unit test.

No files were deleted.
