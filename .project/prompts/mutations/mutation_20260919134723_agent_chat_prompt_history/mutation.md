# Mutation Log

## Created
- **hgai_module_agentchat/prompt_history.py** — `add_history_entry(username, prompt)`, `list_history(username, limit=50)`, `clear_history(username)`. Owns its own `agent_chat_prompt_history` Mongo collection directly, capped at `HISTORY_MAX_PER_ACCOUNT = 50` per account, with resubmission-of-identical-text moving the entry to the top instead of duplicating it. Near-verbatim structural copy of `hgai_module_shql/history.py` (same dedup/eviction/scoping semantics), since this is the same kind of feature for a different screen.
- **tests/test_agent_chat_prompt_history.py** — 7 tests (add/list roundtrip, newest-first ordering, dedup-on-resubmit, blank-prompt-not-recorded, max-50 eviction, per-account scoping, clear-only-affects-caller), mirroring `tests/test_shql_history.py`'s own fake-Motor-collection test structure.

## Modified
- **hgai_module_agentchat/api_router.py** — Added `GET/POST/DELETE /agent/prompt-history`, mirroring `hgai_module_shql/api_router.py`'s `/shql/history` endpoints exactly (including a small dedicated `AgentPromptHistoryEntryRequest` body model rather than reusing `AgentChatSendRequest`, for the same request/response decoupling reason the SHQL router already established).
- **ui/js/api.js** — Added `listAgentPromptHistory`, `addAgentPromptHistoryEntry`, `clearAgentPromptHistory`.
- **ui/js/app.js** — Added `addToAgentChatHistory(prompt)` (fire-and-forget, best-effort — mirrors `addToShqlHistory`'s call site and error-swallowing exactly) called at the top of `sendAgentChatMessage()`, right when a prompt is submitted, independent of whether the turn succeeds. Added `loadAgentChatPromptHistory()` to populate a new collapsible list in the chat panel; clicking an entry fills the composer (does not auto-send, matching the SHQL screen's own "copy from history into the query box" behavior) and closes the list. Added a `btn-agent-chat-history-toggle` click handler with mutual exclusion against the existing sessions-list toggle (opening one closes the other).
- **ui/index.html** — Added a "Prompt history" toggle button (`bi-list-ul` icon) to the chat panel header, and `#agent-chat-prompt-history-list` (reusing the existing `.agent-chat-sessions-list` CSS class — no new styles needed).

No files were deleted.
