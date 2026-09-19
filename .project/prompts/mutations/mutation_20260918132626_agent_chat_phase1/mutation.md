# Mutation Log

## Created
- **hgai_module_agentchat/__init__.py** — Re-exports `AgentChatModule`.
- **hgai_module_agentchat/module.py** — Module descriptor (name/version/description + `get_router()`), following `docs/module-development.md`.
- **hgai_module_agentchat/models.py** — Pydantic models: `AgentVendorName` enum (anthropic/openai/xai/custom), `AgentVendor{Base,Create,Update,InDB,Response}`, `AgentModel{Base,Create,Update,InDB,Response}`. `AgentVendorInDB.api_key_encrypted` is `Field(exclude=True)` so it can never leak through serialization.
- **hgai_module_agentchat/crypto.py** — Fernet symmetric encryption for vendor API keys at rest, keyed by `sha256(settings.secret_key)`; `encrypt_api_key`/`decrypt_api_key`/`last4`.
- **hgai_module_agentchat/store.py** — Raw Mongo CRUD (`agent_vendors`, `agent_models` collections, via `hgai_module_storage_mongodb.connection.get_db()`) with tag/search/pagination filtering, mutation-audit-trail tracking (`hgai.core.mutations`), and `seed_defaults()` — idempotent seeding of 3 vendors (Anthropic/OpenAI/xAI) and 4 models, all `enabled=False` with no key.
- **hgai_module_agentchat/api_router.py** — REST endpoints under `/agent`: vendor CRUD (admin-only end to end) and model CRUD (write admin-only, read any authenticated account).
- **tests/test_agent_chat.py** — 13 tests: encryption round-trip, key masking/never-leaked assertion, vendor/model CRUD, tag/search filtering, key rotation vs. preserve-on-update, mutation-audit-trail correctness (rotated key never appears in a delta), and seeding idempotency (re-seeding never overwrites an admin's edits). Uses an in-memory fake Motor-like collection (same pattern as `tests/test_shql_history.py`), patched via `hgai_module_agentchat.store._db`.

## Modified
- **hgai/config.py** — Added `agent_chat_enabled: bool` setting (`HGAI_AGENT_CHAT_ENABLED`), default `True`.
- **hgai/main.py** — Registered the AI Agent Chat module (mounted conditionally in a `try/except`, matching the Mesh/SHQL/MCP pattern) and added a startup call to `seed_defaults()` (also non-fatal on failure).
- **pyproject.toml** — Added `agno>=3.0.10`, `anthropic>=0.77.0`, `openai>=1.106.0`, `cryptography>=3.4.0`.
- **requirements.txt** — Added `agno==3.0.10`, `anthropic==1.7.0`, `openai==3.16.0`, `cryptography>=3.4.0`, with a comment explaining the deliberate avoidance of the `agno[mcp]` extra (its `mcp>=2.1.0` pin would conflict with this project's own `mcp==1.30.0`).

No files were deleted. Two scratch spike scripts (`spike_mcp_toolkit.py`, `spike_sse.py`) were written to the session scratchpad directory (outside the repo) to validate the architecture before this implementation and are not part of the repo.
