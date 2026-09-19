# Mutation Summary

## Intent
Begin implementing the "AI Chat Agent Panel" feature (a Claude/Cursor-style collapsible AI chat panel, multi-vendor, MCP-aware, with Note export) per the previously-presented implementation plan. This session covers the plan's Phase 0 (de-risking spike) and Phase 1 (vendor/model CRUD backend) only — no chat sessions, agent engine, or frontend yet.

## Context
The full plan (presented in the prior turn) proposed Agno as the agent framework, with three explicit open decisions the user was asked to resolve:
1. MCP integration approach — custom lightweight toolkit (avoids a dependency conflict) vs. adopting `agno[mcp]` (simpler, but its `mcp>=2.1.0` pin conflicts with this project's `mcp==1.30.0`, itself only just stabilized earlier in this same session after Claude Code's MCP client crashed the old 1.9.0 SDK).
2. Streaming protocol — SSE vs. chunked JSON.
3. Default model catalog — seed a small default catalog vs. ship empty.

The user approved the plan's recommendation on #1 and #2, and explicitly chose to seed a default catalog for #3 (overriding the plan's "ship empty" recommendation).

Before writing any Phase 1 code, a Phase-0 spike empirically validated the two highest-risk architectural bets: (a) installing `agno` without the `mcp` extra has zero dependency conflicts with the pinned `fastapi`/`starlette`/`mcp`/`pymongo`/`motor` versions, and (b) a hand-rolled httpx-based MCP client can list the resident hgai MCP server's tools and wrap them as Agno `Function` objects (using the server's own JSON schema via `parameters=..., skip_entrypoint_processing=True`) that a real `Agent(model=Claude(...))` successfully called end-to-end against the live server. `StreamingResponse`/SSE was also confirmed to compose cleanly with the current FastAPI/Starlette versions via a `TestClient` round-trip.

## What Changed and Why
Phase 1 followed `docs/module-development.md`'s documented pattern for adding an optional module (same shape as the existing `hgai_module_mesh`/`hgai_module_shql`): a self-contained `hgai_module_agentchat` package, mounted conditionally in `hgai/main.py` inside a `try/except` so a broken chat module can never take the whole server down, exactly like Mesh/SHQL/MCP.

Data ownership follows the same reasoning already applied to `hgai_module_shql`'s query-history collection: vendor/model catalog data isn't a hypergraph entity, so it gets its own MongoDB collections (`agent_vendors`, `agent_models`) accessed directly via `hgai_module_storage_mongodb.connection.get_db()`, rather than extending the pluggable `StorageBackend` ABC used by core resources (hypergraphs/nodes/edges/accounts/etc).

Vendor API keys are the one genuinely sensitive addition here (this project hasn't previously stored a third-party secret it needs to *retrieve and use*, only the admin password hash, which only ever needs to be *verified*). They're encrypted at rest via Fernet, keyed by the already-required `HGAI_SECRET_KEY` (no new secret to provision), and the ciphertext field is marked `Field(exclude=True)` on the Pydantic model so it's stripped from *every* serialization path — API responses, any future `.model_dump()` call, accidental logging — rather than relying on a developer remembering to scrub it route-by-route. Only the last 4 characters of a configured key are ever surfaced, for display/confirmation. Vendor CRUD is admin-only end to end (same gating as Meshes); model CRUD is admin-only to write but readable by any authenticated account, since the (not-yet-built) chat panel's model picker needs to list enabled models for every user.

The mutation-audit-trail helpers already used by hypernodes/hyperedges/notes/parameterized-queries (`hgai.core.mutations`) were reused as-is for both vendors and models — with the API key fields deliberately excluded from the tracked-fields list, so a key rotation is recorded as an event but the key material itself (plaintext or ciphertext) never appears in a mutation delta, which the API otherwise returns to clients as part of the resource.

The default catalog (3 vendors: Anthropic/OpenAI/xAI; 4 models: 2 Claude + 1 GPT-5 + 1 Grok) is seeded idempotently on every server startup — it only inserts a vendor for a `name` that doesn't already exist, so it never overwrites or resurrects an admin's own edits (including fully deleting a seeded row). Every seeded vendor starts `enabled=False` with no key, so the chat panel's model picker won't be empty on a fresh install, but nothing is actually callable until an admin configures a real key.

## Key Decisions
- **Custom MCP toolkit over `agno[mcp]`**: chosen specifically to avoid re-triggering the exact class of dependency-pin conflict this same session spent significant effort resolving for `mcp`/`fastapi`/`starlette` a few turns earlier. Empirically validated via the Phase-0 spike before committing any Phase 1 code to the approach.
- **Module-owned Mongo collections over the `StorageBackend` ABC**: matches the project's own documented convention for module-specific, non-hypergraph data, and avoids growing the core storage interface for a feature that may be replaced or removed independently of the rest of the app.
- **`Field(exclude=True)` on the ciphertext field** rather than per-route `response_model_exclude`: a structural guarantee that survives future routes/call sites, not a convention someone has to remember.
- **Optional `api_key` on `AgentVendorCreate`** (not required): enables the idempotent placeholder-seeding path to reuse the exact same `create_vendor()` function real admin-driven creates use, rather than a separate seeding code path with its own risk of drifting out of sync.
