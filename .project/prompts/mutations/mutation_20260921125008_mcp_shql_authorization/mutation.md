# Mutation Log

## Created
- **tests/test_authz.py** — 95 tests: shared auth helpers (graph/space/token), SHQL authorization incl. cache-ordering and logical/mesh rules, REST route mappings, every MCP tool (classification completeness, per-operation guards, caller attribution, no-caller refusal), and an end-to-end run through the real MCP ASGI app (401s, identity per request, concurrency).

## Modified
- **hgai/core/auth.py** — Added `authenticate_token` (shared API-key/JWT -> active account resolution; `get_current_account` now uses it), `unowned=` flag on `can_access_graph`/`can_perform`, and shared enforcement helpers `PermissionDeniedError`, `check_graph_permission`, `require_admin_role`, `check_space_role`, `filter_accessible_graphs`, plus `SPACE_ROLE_RANK`.
- **hgai/api/deps.py** — `require_graph_access` / `require_space_role` now delegate to the shared helpers (same 403 messages); removed the local role-rank table.
- **hgai_module_mcp/module.py** — Replaced the API-key/JWT-signature-only middleware with `_AuthMiddleware`, which resolves the full active account (401 for invalid/expired/inactive) and publishes it for the request.
- **hgai_module_mcp/server.py** — Added per-request caller context (`ContextVar`, `set_caller`/`reset_caller`) and guards; every graph/admin/space tool now authorizes as the caller; `hgai_hypergraph_list` and `hgai_space_list` filter to what the caller may see; `hgai_query_execute`/`hgai_mesh_query` run as the caller; audit stamps use the caller's username instead of `mcp-agent`; docstring/instructions updated.
- **hgai_module_shql/engine.py** — `execute_shql` now requires `account=`; new `_authorize_query` runs before the result cache (per-`from:` graph `query` permission, logical-graph member access, mesh refs admin-only) and the account is threaded to federation calls.
- **hgai_module_shql/parser.py** — Added `SHQLPermissionError(SHQLError)`.
- **hgai_module_shql/api_router.py** — `/shql/query` passes the caller and maps `SHQLPermissionError` to 403.
- **hgai/core/parameterized_queries.py**, **hgai/api/routers/parameterized_queries.py** — Parameterized-query execution runs as the caller; 403 mapping.
- **hgai_module_mesh/engine.py**, **hgai_module_mesh/api_router.py** — `federated_shql`, `execute_dot_refs`, `_query_server` take `account`; federation entry points enforce the admin role; the mesh query route passes the admin account.
- **hgai_module_agentchat/mcp_toolkit.py**, **hgai_module_agentchat/engine.py** — Replaced the "known gap" comments with the actual guarantee (agent runs with the signed-in user's permissions).
- **tests/test_mesh.py** — Two `federated_shql` calls pass an admin account.
- **docs/help/notes/integration/mcp-server.md**, **mcp-tools.md**, **authentication.md**, **docs/help/notes/admin/accounts-roles.md**, **meshes.md**, **docs/help/notes/shql/shql-advanced.md**, **docs/help/notes/web-ui/ai-chat.md** — Replaced the "not enforced" caveats with the authorization rules (per-tool permission table, SHQL permissions section, mesh admin-only, API keys remain full-admin, audit attribution).
- **README.md**, **docs/api-reference.md** — Added MCP authorization section, SHQL/parameterized-query authorization note, and unified access-resolution note.
- **docs/marketing/hypergraphai-overview-investor-20260921043558.md**, **docs/marketing/hypergraphai-overview-enterprise-20260921045025.md** — Removed/rewrote statements that MCP and SHQL are unauthorized or that MCP writes are stamped `mcp-agent`; the remaining honest gap is unscoped API keys.
