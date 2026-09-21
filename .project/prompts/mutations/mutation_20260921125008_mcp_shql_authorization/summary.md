# Mutation Summary

## Intent
Close the security gap found while writing the marketing decks: the MCP endpoint and `POST /shql/query` authenticated callers but never applied `can_access_graph` / `can_perform`, so any signed-in account (including a `readonly` one with no permissions) could read, and via MCP write, every graph — and HgNexus's MCP tools inherited that.

## Context
REST enforced permissions through `require_graph_access` / `require_space_role` in `hgai/api/deps.py`. MCP and SHQL bypassed them. HgNexus already minted a per-account JWT for its MCP calls (documented as "not yet a security boundary"), so once MCP honoured the caller, the agent became scoped without changes to the chat engine. The SHQL result cache is keyed by query text only, so it could not be consulted before authorization.

## What Changed and Why
1. **One rule, three surfaces.** The enforcement logic moved into `hgai/core/auth.py` (`check_graph_permission`, `check_space_role`, `filter_accessible_graphs`, `authenticate_token`), and the REST dependencies now call it. MCP and SHQL use the same helpers, so they cannot drift from REST.
2. **MCP** — the ASGI middleware now resolves the full active account (previously only the JWT signature was checked, so a disabled account's token still worked) and publishes it in a `ContextVar` for the request; each tool guards on it. Mapping mirrors REST: graph tools need read/write/delete on the graph, SHQL needs `query` on each `from:` graph, space tools need a space role, mesh tools are admin-only, list tools filter to what the caller may see, and creation/media tools stay open to any authenticated account as on REST. Denials are normal tool results `{"error", "type": "PermissionDenied"}` so agents can report them. Audit stamps now carry the caller's username rather than `mcp-agent`.
3. **SHQL** — `execute_shql` requires an `account`; `_authorize_query` runs after parse/validate and before the cache. A refused graph refuses the whole query (403), it is never partially filtered. Logical graphs require their members; mesh references (dot-notation or a bare mesh id) require admin because federation uses the mesh's stored server credentials. Parameterized queries run as the caller too.
4. **Docs** — every place that documented the gap (help topics, README, API reference, both marketing decks, code comments) now states the enforced behaviour; the remaining caveat is that API keys are full-admin.

## Key Decisions
- **`account` is a required keyword** on `execute_shql`, `federated_shql` and `execute_dot_refs` (fail closed) rather than an optional parameter defaulting to "trusted"; there are no internal system callers, and the two mesh tests were updated.
- **SHQL needs the `query` operation**, not `read`. `query` is already in the default account permissions and every space role that can read; requiring it makes the existing operation meaningful. Accounts configured with only `read` lose SHQL.
- **`unowned=True`** on the permission helpers: MCP graph tools and SHQL know whether a graph is unowned, and the id-only space lookup is ambiguous when a space holds a same-named graph (it could admit a space member to an unowned graph). Existing REST behaviour is unchanged.
- **Mesh = admin-only** matches REST (all `/meshes` routes are admin-only) and prevents a wildcard-permission user from borrowing a mesh's remote credentials.
- **Context var over a per-tool parameter** to keep tool schemas unchanged; verified through the real ASGI app that identities do not bleed between concurrent requests (`stateless_http=True`).
- **Verification**: 95 new tests (mutation-checked: removing a guard or the pre-cache check makes them fail); full suite 440 passed (2 pre-existing mesh ping tests excluded); live check on a second instance with a real restricted account confirmed 403/PermissionDenied on other graphs, write/delete without the operation, mesh tools and mesh refs, filtered graph list, and admin unaffected. The probe account was removed afterwards.
- **Not changed**: the REST `GET /graphs` list still uses its older filter (a non-admin with `["*"]` also sees other tenants' space graphs in the *list*, though not their contents); MCP uses the stricter shared filter.
