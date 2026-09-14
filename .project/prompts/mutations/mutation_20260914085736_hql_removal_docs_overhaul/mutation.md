# Mutation Log

## Deleted

- **hgai_module_hql/** (`__init__.py`, `api_router.py`, `engine.py`, `module.py`) — the entire HQL query-language module: parser, executor, and `/api/v1/query*` REST router.
- **tests/test_query.py** — HQL parser/validator unit tests (no longer applicable).
- **docs/decks/demo-alpha/queries/q01–q07.hql** (7 files), **docs/decks/demo-bus-dev-20260817/queries/q01,q02,q03,q05.hql** (4 files), **docs/decks/demo-spec-ops-20260817/queries/q01,q02,q03,q05.hql** (4 files) — 15 HQL demo query files, replaced by SHQL equivalents (see Created).

## Created

- **docs/decks/demo-alpha/queries/q01–q07.shql**, **docs/decks/demo-bus-dev-20260817/queries/q01,q02,q03,q05.shql**, **docs/decks/demo-spec-ops-20260817/queries/q01,q02,q03,q05.shql** (15 files total) — SHQL translations of the deleted `.hql` demo query files, same filename stem, same `as:` result alias, same descriptive header comments where present. `$or` and member-`$in` semantics translated to `union:` branches (no direct SHQL equivalent); `$all`-style "both members present" translated to two member patterns on one edge pattern.

## Modified

### Backend — core removal & relocation
- **hgai/main.py** — removed the HQL module-mount block; `"hql"` dropped from (and `"shql"` was already present in) the `/api/v1/server/info` capabilities list.
- **hgai_module_mesh/engine.py** — `_rewrite_from`/`_query_server`/`execute_dot_refs` simplified to drop the `lang` parameter (SHQL-only now); `federated_hql` function deleted; `federated_shql`'s internal call updated.
- **hgai_module_mesh/api_router.py** — `POST /{mesh_id}/query` simplified to accept only an `shql` body key (was `hql`-or-`shql` dispatch).
- **hgai_module_mesh/module.py** — description string: "federated HQL queries" → "federated SHQL queries".
- **hgai_module_mcp/server.py** — `hgai_query_execute`/`hgai_query_validate`/`hgai_mesh_query` tools rewritten SHQL-only (dropped the `hql:`/`shql:` auto-detect branching, `execute_hql`/`parse_hql`/`validate_hql`/`HQLError`/`federated_hql` imports removed); docstrings/examples rewritten, added an `aggregate:` and an `infer: true` example.
- **hgai_module_mcp/module.py** — description string: "HQL query operations" → "SHQL query operations".
- **hgai_module_shql/api_router.py** — added `POST /shql/cache/invalidate` (relocated from the deleted HQL router; same `invalidate_cache` call, same response shape).
- **hgai_module_shql/engine.py** — `execute_dot_refs` call site updated to the new (no-`lang`) signature; three explanatory comments that referenced HQL by name reworded to stand on their own.
- **pyproject.toml** — removed the now-nonexistent `hgai_module_hql*` entry from `[tool.setuptools.packages.find].include`.
- **scripts/seed_data.py** — the "Example queries to try" block printed after seeding rewritten from HQL to SHQL.
- **shell/hgai_shell.py** — `query`/`validate` client methods, `COMMANDS` entries, `HELP_TEXT` entries, dispatch-table entries, and `cmd_query`/`cmd_validate` functions removed; `cmd_mesh_query` simplified to SHQL-only; module docstring and the SHQL command's "looks like an HQL query" guard message updated.
- **tests/test_mesh.py** — `federated_hql` import (would have raised `ImportError` and failed the whole file's collection) replaced with `federated_shql`; `test_federated_hql_merges_results`/`test_federated_hql_mesh_not_found` renamed and retargeted to `federated_shql`; also fixed a latent bug in the renamed test (mocked `httpx.AsyncClient` directly, which the current shared-`get_http_client()` architecture never calls that way, plus empty `graphs: []` triggering an unmocked `fetch_remote_graphs` HTTP call) — now mocks `get_http_client` and gives the fixture servers a non-empty `graphs` list.
- **hgai/core/inference.py** — two comments referencing HQL (module docstring's "wired into HQL", a dangling-members note) updated to SHQL.
- **hgai_module_storage/backend.py** — one docstring comment ("auth/HQL paths") updated to SHQL.

### UI
- **ui/index.html** — removed the "Query (HQL)" screen (`#screen-query`), its sidebar nav link, and its Examples offcanvas (`#offcanvas-examples`/`#hql-examples-list`); removed the mesh federated-query modal's HQL/SHQL language `<select>` (SHQL-only now).
- **ui/js/app.js** — removed `HQL_EXAMPLES`, `initQueryEditor`, the page-level `runQuery`, and the `btn-query-*` event handlers (~169 lines); removed `query`/`initQueryEditor` entries from the screen-title/loader maps and `editorCM` from `State`; simplified the mesh-query-run handler to always wrap as `shql:`; added an `'Aggregate: count by relation'` entry to `SHQL_EXAMPLES`; renamed the `hql-example-card` CSS class use to `query-example-card`; updated comments in `fetchInferredEdges` and the cross-graph dot-notation helper.
- **ui/js/api.js** — removed `runQuery`/`validateQuery`; `flushCache` repointed from `/query/cache/invalidate` to `/shql/cache/invalidate`.
- **ui/css/hgai.css** — `#query-editor-wrapper .CodeMirror` retargeted to `#shql-editor-wrapper` (the surviving editor); `.hql-example-card` renamed to `.query-example-card`.

### Documentation
- **README.md** — Key Concepts' HQL walkthrough (290 lines) replaced with a condensed SHQL intro + one worked example; Space-scoped Graph References examples converted to SHQL; Architecture directory tree updated (module list, test file list); API Reference `### Query`/`### Meshes` sections updated to `/shql/*` endpoints; MCP Tools table/Tool Reference/Payload Examples converted to SHQL-only; hgai Shell command list and Web UI bullet updated; **Inferencing section fully rewritten** (was describing a superseded `RelationType.attributes.inverse` design and claiming inferencing was unwired — now documents the real axiom-hyperedge mechanism, live and wired into SHQL); SHQL section intro/Mesh HQL section (renamed "Dot-Notation Mesh References")/`### HQL vs SHQL` table (removed) updated; added 3 new worked examples (positional `seq` filter, `aggregate`, `infer: true`) to the SHQL Examples gallery; Module Development space-scoped examples, MongoDB Indexes purpose column, Performance table's `federated_hql` row updated/removed.
- **docs/concepts.md** — PIT example converted to SHQL; **Semantic Inferencing section fully rewritten** (was describing SKOS as a built-in hypernode-level relation set; now documents the axiom-hyperedge control vocabulary); **added a new "## SHQL — Semantic Hypergraph Query Language" section** (this doc previously had zero SHQL coverage, HQL-only); MCP/Spaces query examples converted; RBAC "Access Resolution" order corrected to match README's authoritative model (space membership is the sole gate, checked before `permissions.graphs`).
- **docs/api-reference.md** — `## HQL Query` section replaced with `## SHQL Query` (this doc had no SHQL section at all before); server-info capabilities sample, MCP tool table, error-code table updated.
- **docs/hello-world.md** — all 6 query examples and the shell-session transcript converted to SHQL; closing summary bullet updated.
- **docs/module-development.md** — the "Working with the Core Engine" code example fixed (previously imported nonexistent `hgai.core.query.execute_hql`/`hgai.core.inference.get_skos_closure`; now uses the real `hgai_module_shql.engine.execute_shql` and `hgai.core.inference.expand_edge_closure`).
- **docs/investor-pitch-deck.md** — "Two Query Languages" slide rewritten as one SHQL slide (with an aggregation/inferencing callout); architecture diagram, MCP code snippet, roadmap/certification bullets updated.
- **docs/decks/demo-alpha/deck-demo-alpha.md** — Phase 4 ("HQL: Filter & Aggregate") and Phase 5 (PIT) converted to SHQL; Phase 6 reframed as building on Phase 4 rather than contrasting against HQL; Phase 10 (Inferencing & Roadmap) rewritten to match the real axiom-hyperedge mechanism (was claiming inferencing was unwired); Edge Flavors concept table and all `flavor: direct` mentions corrected to the real two-flavor (`hub`/`symmetric`) model; MCP tool-call snippet, roadmap table, wrap-up bullets updated.
- **docs/decks/demo-alpha/data/acme-eng-import.yaml** (gitignored, not tracked by git but present on disk) — 8 edges' `flavor: direct` (not a valid `EdgeFlavor` value — would fail import validation) corrected to `flavor: hub`, which is semantically equivalent for a 2-member edge; two section comments updated to match.
- **docs/decks/demo-bus-dev-20260817/deck-hgai-defense-bd.md**, **docs/decks/demo-spec-ops-20260817/deck-hgai-specops-bd.md** — `.hql` filename references updated to `.shql` (the files they point at were renamed/converted; see Deleted/Created). Inline narrative and embedded `hql:` query blocks left untouched — see summary.md for why.
- **training/user/hgai-user-fundamentals.md** — Module 6 ("Queries — HQL", ~390 lines, tasks 6.1–6.6) deleted; former Module 7 (SHQL) renumbered to Module 6 (tasks 7.1–7.6 → 6.1–6.6), former Module 8 (Reference Summary) renumbered to Module 7; added a new §6.7 "Inferencing" subsection with a worked example; Edge Flavors table/analogies corrected to the real two-flavor model (was listing `direct`/`transitive`/`inverse-transitive`); sidebar table, SHQL structure block (`infer:`/`aggregate:` added), Reference Summary's "HQL vs SHQL" table (removed) and cheat sheet updated; Table of Contents and closing summary updated to match.
