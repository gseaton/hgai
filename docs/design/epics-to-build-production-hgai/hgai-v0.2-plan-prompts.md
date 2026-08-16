# HypergraphAI v2 — Phase Prompts

Ready-to-submit prompts for Claude Code (or an equivalent agentic coding assistant) to execute `build-plan.md` phase by phase in a greenfield repository.

## Setup (do this once, before Prompt 0)

1. Create the new empty repository, initialize git.
2. Copy `build-plan.md` (from this directory) into the new repo at `docs/design/build-plan.md`. Every prompt below assumes that exact path.
3. Submit prompts **in order, one per session**. Each prompt is self-contained — it re-states its phase's scope so the agent doesn't need memory of prior sessions, only the repo state they left behind (commits/files on disk are the continuity mechanism, not chat history).
4. Do not submit Prompt *N+1* until Prompt *N*'s session reports its exit criteria met and you've spot-checked the result (run the tests yourself, or at minimum read the diff).
5. If an agent reports a phase blocked or ambiguous, resolve it yourself against `build-plan.md` §1–§3 before resubmitting — don't let the agent guess past a real ambiguity.

Each prompt below is a single fenced block — copy the whole block as one message.

---

## Prompt 0 — Workspace scaffold

```
Read docs/design/build-plan.md in full before doing anything else. This repo is empty — you are starting Phase 0 of the HypergraphAI v2 build plan (§14).

Build a uv workspace skeleton:
- Workspace root pyproject.toml (uv workspace mode) at repo root.
- Empty package stubs for every package listed in build-plan.md §4's repository layout under packages/*, each with its own src/<pkg>/ and pyproject.toml (name matches the directory, depends on nothing yet except what's needed to import cleanly).
- apps/web-ui/ placeholder (empty, populated in a later phase — do not build UI now).
- Dockerfile that does `COPY . .` + `uv sync --frozen` (no hand-maintained per-package COPY lines — this structurally avoids the packaging bug described in §2 row 2).
- docker-compose.yml with services: mongo (community image, replica-set-capable — transactions are required later, see §11), qdrant, and the app (depends_on mongo healthy).
- .env.example matching the HGAI_ prefix convention implied by §3/§8 (secrets, mongo URI, qdrant URL — no default values for secrets).
- .github/workflows/ci.yml running ruff + mypy (strict) only for now — no test job yet, there's nothing to test.

Exit criteria (verify before reporting done): `uv sync` succeeds from repo root. `docker compose up` boots a FastAPI app (hgai-core, minimal app factory only) that responds 200 on GET /healthz. `docker compose up` also proves the Dockerfile actually includes every workspace package (this is the specific failure mode this phase must not reproduce — confirm by checking each package is importable inside the built container, not just present in the workspace).

Do not implement any domain models, storage, auth, or query logic yet — that's later phases. Stay scoped to scaffold + a trivial /healthz route.
```

---

## Prompt 1 — Storage core

```
Read docs/design/build-plan.md in full, especially §2 row 1, §3 (storage/vector rows), §4, §6.3, and §14 Phase 1. The repo already has the Phase 0 workspace scaffold (uv workspace, empty package stubs, working Dockerfile/compose, /healthz). You are now implementing Phase 1.

Implement in packages/hgai-storage:
- Storage ABCs per the pattern in §2 row 9 (this pattern is confirmed good in the reference implementation, carry it forward as-is): HypergraphStore, HypernodeStore, HyperedgeStore, AccountStore, SpaceStore, MeshStore, CacheStore, plus a top-level StorageBackend owning connect/close/ensure_schema and typed accessors to each store.
- Typed filter/patch dataclasses per entity (mirror the ABCs).
- The Filter IR from §6.3 exactly as specified: FilterExpr union (Eq, Ne, In, Gt, Gte, Lt, Lte, Exists, And, Or, Not, ElemMatch) as frozen dataclasses. This IR is the fix for the single most important defect in the reference implementation (§2 row 1) — no MongoDB-specific syntax may appear anywhere in hgai-storage.

Implement in packages/hgai-storage-mongodb:
- Motor-based connection lifecycle (connect/close/get_db).
- ensure_indexes(): partial unique indexes distinguishing org/space-scoped vs. unowned ids, PIT-related sparse indexes on valid_from/valid_to, TTL index for query cache.
- Store implementations for every ABC against Motor collections.
- The IR→Mongo translator: the ONLY place in the entire codebase allowed to import pymongo/motor query operators or construct $elemMatch/etc. Translate the full FilterExpr union.

Write the contract test suite under tests/contract/: a fixture set of FilterExpr trees run against the Mongo backend via testcontainers (real MongoDB, not mocks), asserting expected result sets. This suite is written to run against ANY registered backend, not hardcoded to Mongo, per §13.

Exit criteria: contract test suite passes against the Mongo backend via testcontainers. Grep the diff yourself for "pymongo" or "motor" imports outside hgai-storage-mongodb before reporting done — zero should exist.
```

---

## Prompt 2 — Core models & config

```
Read docs/design/build-plan.md in full, especially §1, §5, §4's HgaiModule Protocol, §8, and §14 Phase 2. Phases 0–1 are complete (workspace, storage ABCs + Mongo backend + Filter IR, contract tests passing). You are now implementing Phase 2.

Implement in packages/hgai-core:
- Every entity from §5's table as Pydantic v2 models, *Base/*Create/*Update/*InDB/*Response pattern: Hypernode, Hyperedge, Hypergraph, Organization, Space, Account, RelationType, Event, Mesh/MeshServer. Include the common base fields (tags, status, attributes, timestamps) exactly as described. Note the deliberate v2 changes from v1: Hyperedge does NOT carry skos_broader/narrower fields (that moves to RelationType/axiom in a later phase); Space gains org_id; Account gains api_keys: [{key_hash, label, created_at, last_used}] replacing any notion of global static keys.
- hyperkey generation for Hyperedge (SHA-256 of relation + sorted members) — deterministic, order-insensitive, matching the property tested in the reference implementation.
- Settings (pydantic-settings, HGAI_ env prefix, case-insensitive). Settings MUST fail closed: missing SECRET_KEY or MONGO_URI at startup raises immediately, no defaults, no silent fallback. This directly avoids §2 row 4's defect.
- The HgaiModule Protocol exactly as specified in §4 (name, version, description, get_api_router, get_mcp_tools, on_startup, on_shutdown) — defined once here, real code, not a doc-only convention. This is the fix for §2 row 8.

Exit criteria: unit tests for every model covering id-format validation (e.g. Hypergraph id rejects "."), temporal field constraints, hyperkey determinism/order-insensitivity/uniqueness, and a Settings test proving startup fails without required secrets (no default admin password path exists anywhere — grep for hardcoded credentials before reporting done).
```

---

## Prompt 3 — Auth & REST CRUD

```
Read docs/design/build-plan.md in full, especially §2 rows 3–4, §7, §8, and §14 Phase 3. Phases 0–2 are complete (storage, Filter IR, all models, Settings, HgaiModule Protocol). You are now implementing Phase 3.

Implement in packages/hgai-core:
- JWT auth (password flow: POST /auth/token, GET /auth/me).
- Scoped, hashed per-account API keys as an alternate auth path (never a static global key — this is the fix for the API-key design smell noted alongside §2 row 4).
- Admin bootstrap: first boot with no accounts generates a random admin password, prints it once, forces a rotation flag. No default credential ships in code, config, or docs.
- REST routes per §7's table, ONE canonical tree — do not build a parallel /spaces/{id}/graphs/... tree, this is the direct fix for §2 row 3: /orgs, /spaces (+ /spaces/{id}/members), /graphs (+ stats/export/import), /graphs/{graph_id}/nodes, /graphs/{graph_id}/edges, /accounts (admin only, includes API-key issuance). A graph's space_id is a field set on create, never a URL segment.
- RBAC exactly as §8 describes: global Role × per-account {graphs, operations} grants × per-Space SpaceRole nested under Organization. Preserve the deliberate v1 design decision verbatim: space membership is the SOLE gate for space-scoped graphs — an account's global graphs: ["*"] must NOT cross tenant boundaries. Write a test that proves this explicitly (a global-wildcard account denied access to another org's space-scoped graph).

Exit criteria: integration tests (httpx ASGITransport + testcontainers Mongo) cover every route in this phase with at least one happy-path and one RBAC-denial case. Confirm via test that omitting SECRET_KEY prevents app startup. Confirm via test that no two accounts share a bootstrap password across runs (i.e. it's actually random, not a fixed "generated" placeholder).
```

---

## Prompt 4 — Eventing

```
Read docs/design/build-plan.md in full, especially §1's new tenets, §5's Event model, §11, and §14 Phase 4. Phases 0–3 are complete (auth, RBAC, full CRUD REST surface). You are now implementing Phase 4.

Implement in packages/hgai-events:
- The Event envelope per §5 (entity_type, entity_id, op, actor_account_id, before, after, graph_id, ts).
- Wire every mutation from Phase 3's CRUD routes (Hypernode/Hyperedge/Hypergraph create/update/delete) to append an Event in the SAME MongoDB transaction as the state change — not a best-effort side write, an atomic one. This requires mongo running as a (single-node is fine) replica set; confirm docker-compose.yml from Phase 0 already supports this, fix it if not.
- GET /events (filterable by entity, graph, actor, time range) as the audit-trail read path. This REPLACES any notion of a separate inert audit_log collection — events ARE the audit log, per §1.
- A minimal in-process asyncio worker queue that mutation events are published to, for later consumers (embedding worker in Phase 8, closure-cache invalidation in Phase 7) — build the queue and a no-op subscriber now, real subscribers come later. Do not stand up Kafka/RabbitMQ (explicitly out of scope, §15).

Exit criteria: integration test proving a mutation and its event write succeed or fail together (simulate an event-write failure and confirm the state mutation rolls back). Integration test for GET /events filtering.
```

---

## Prompt 5 — HQL

```
Read docs/design/build-plan.md in full, especially §6.1, §6.3, and §14 Phase 5. Phases 0–4 are complete (storage/IR, models, auth/CRUD, eventing). You are now implementing Phase 5.

Implement in packages/hgai-query-hql:
- Full HQL parser/planner/executor per §6.1's grammar: top-level hql: key, from (graph id / list / space/graph / mesh dot-ref — dot-ref resolution can stub/defer to Phase 9's mesh module, just leave the hook), match (type, node_type, relation, flavor, id, nodes), where (attribute equality, tags, dot-paths, members.*), return, as, limit/skip, distinct, at (PIT timestamp), aggregate (count, group_by).
- HQL where/match clauses compile to hgai_storage's Filter IR (§6.3) — do NOT construct MongoDB syntax directly in this package, that's exactly the defect §2 row 1 exists to prevent. Verify by grepping this package for pymongo/motor imports — must be zero.
- Query result caching keyed by a hash of the normalized query.
- POST /query and /query/validate REST routes (mount via HgaiModule).
- Leave match.flavor: transitive as a recognized-but-not-yet-inference-backed field for now (raises NotImplementedError or returns raw unexpanded edges with a TODO comment referencing Phase 7) — full transitive semantics land in Phase 7.

Exit criteria: integration tests reproduce every query shape in §6.1 against seeded fixture data, including a PIT query verified against valid_from/valid_to. Unit tests for the where/match → FilterExpr compilation step in isolation.
```

---

## Prompt 6 — SHQL

```
Read docs/design/build-plan.md in full, especially §2 row 1 and the SHQL-specific note, §6.2, §6.3, §13's mocking note, and §14 Phase 6. Phases 0–5 are complete (HQL working end-to-end). You are now implementing Phase 6 — this is historically the trickiest phase; read §6.2 twice before writing code.

Implement in packages/hgai-query-shql:
- Full SHQL pattern engine per §6.2: top-level shql: key, from, where (list of patterns: node, edge with members sub-patterns, filter, optional, union), select, limit, offset.
- ?var binding resolution left-to-right. Member-pattern anchor resolution: a member sub-pattern is an anchor if it has a literal id OR references an already-bound ?var — implement this correctly from the start, do not regress to treating only literal id: as an anchor (that was a real, previously-fixed bug in the reference implementation; get it right here rather than reproducing then re-fixing it).
- filter: expressions need a REAL small grammar (Lark, or a hand-written recursive-descent parser) — do not hand-roll a string-scanning evaluator, that was fragile in the reference implementation. Keep the same filter: expression syntax a user would expect (comparisons, boolean and/or/not over bound variables and literals).
- Same Filter IR compilation discipline as Phase 5 — zero MongoDB syntax in this package.
- POST /shql/query and /shql/validate REST routes.

Exit criteria: integration tests covering multi-hop node+edge+optional+union patterns. A DEDICATED regression test for member-anchor resolution: an edge with two unbound-looking member sub-patterns where one has already been bound by an earlier pattern in the same query — assert it binds to the correct member, not the first available slot. This is the single most important test in this phase.
```

---

## Prompt 7 — Inferencing

```
Read docs/design/build-plan.md in full, especially §1, §2 row 5, §5's RelationType/Event entries, §9, and §14 Phase 7. Phases 0–6 are complete (HQL and SHQL both working, including match.flavor: transitive left as a stub in HQL from Phase 5). You are now implementing Phase 7.

Implement in packages/hgai-inference:
- RelationType hypernode handling: a hypernode of type "RelationType" carries axioms: list[str] like "owl:transitive", "owl:symmetric", "owl:inverse-of:<relation-id>", "skos:broader-of:<relation-id>" — exactly the vocabulary in §9, do not invent additional axiom syntax.
- expand_edge(edge) -> list[Hyperedge]: for edges whose relation has inverse-of/symmetric axioms, synthesize implied edges tagged _inferred: true, _source_edge: <id>. Computed at read time, never persisted.
- check_transitive(start_id, end_id, relation, graph_ids, max_depth=10) -> bool | path: BFS over hyperedges filtered by relation.
- Materialized closure cache: a transitive_closures collection, populated by a background job (or on-write trigger via the Phase 4 event queue) for RelationTypes flagged cache: true, invalidated on relevant edge writes. check_transitive checks cache first, falls back to live BFS.
- Wire this into HQL: replace Phase 5's match.flavor: transitive stub with a real call into this package. Wire equivalent evaluation into SHQL pattern matching for edge patterns constrained by an inferable relation.
- POST /infer/transitive and /infer/expand REST routes.

This phase is the direct fix for §2 row 5 — the single most important thing to prove before reporting done is that this logic is actually CALLED from HQL and SHQL, not just unit-tested in isolation with no caller. Grep the codebase for call sites of expand_edge/check_transitive from outside hgai-inference before reporting done.

Exit criteria: end-to-end integration tests running actual HQL and actual SHQL queries against fixture data with transitive/symmetric/inverse-of RelationTypes declared, asserting inferred results come back through the normal query path (not a special test-only code path).
```

---

## Prompt 8 — Retrieval

```
Read docs/design/build-plan.md in full, especially §1, §3 (vector/lexical rows), §10, §14 Phase 8, and §15 (note what's explicitly deferred here — no learned ranker, no Meilisearch). Phases 0–7 are complete (inferencing wired in). You are now implementing Phase 8.

Implement in packages/hgai-retrieval:
- EmbeddingProvider interface (pluggable — implement ONE concrete provider, keep the interface swappable per §3/§10, don't hardcode a specific vendor API into the rest of the system).
- Qdrant client, one collection per hypergraph (per §10's default choice).
- An embedding worker that subscribes to the Phase 4 event queue: on Hypernode/Hyperedge create/update, computes an embedding from label + description + attributes text representation and upserts to Qdrant asynchronously (must not block the write path — the whole point of routing this through events).
- MongoDB text index on label/description/attributes.* (configurable per hypergraph) for lexical search.
- Hybrid ranker: weighted-sum scorer blending semantic similarity + lexical relevance + graph proximity (hop distance from an optional seed node) + freshness (system_updated recency) + optional confidence field. Explicitly do NOT build a learned ranker (§15) — a simple weighted sum is the v1 target.
- POST /search/semantic, POST /search/hybrid REST routes; also add a lexical search path (either a dedicated route or a HQL $text where-operator — pick one, document the choice).

Exit criteria: integration test with a timeout-bounded poll proving write -> async embedding appears in Qdrant -> semantic search returns it. Integration test for the hybrid ranker against a fixture set with a known-similar/known-dissimilar pair, asserting correct relative ordering.
```

---

## Prompt 9 — Mesh federation

```
Read docs/design/build-plan.md in full, especially §1, §2 row 10, §11's note on transaction requirements, §13's async-mocking note, and §14 Phase 9. Phases 0–8 are complete. You are now implementing Phase 9.

Implement in packages/hgai-mesh:
- Mesh/MeshServer models (server_id, server_name, url, optional api_token, cached graphs list) per §5.
- ping_server/ping_mesh (reachability), fetch_remote_graphs/sync_mesh_graphs (refresh cache) driven by a periodic background scheduler at a configurable interval.
- Dot-ref resolution and execution: mesh.server.graph and mesh.server.space.graph notation, fanning a query out to specific remote servers/graphs and merging results. Wire this into the Phase 5/6 from: field resolution that was left as a stub.
- federated_hql/federated_shql: broadcast a query across all servers in a mesh, merge items.
- Generic authenticated HTTP proxy passthrough to a named server.
- CRUD + /ping + /sync + /query + proxy REST routes under /meshes.

Per §2 row 10, the underlying design here is known-correct from a prior implementation — port the shape faithfully rather than redesigning it. The thing to get right that was previously gotten WRONG is test infrastructure: any test mocking httpx.AsyncClient must correctly wire __aenter__/__aexit__ (use respx, or AsyncMock with explicit async-context-manager setup) — never a bare MagicMock standing in for an async context manager, that produced 3 silently-broken tests in the reference implementation.

Exit criteria: integration tests using a REAL second in-process server instance (not mocks) for at least the ping/sync/federated-query paths. Any remaining mocked httpx paths pass under proper AsyncMock wiring — run the full suite and confirm zero "MagicMock can't be used in await expression" style failures.
```

---

## Prompt 10 — MCP server

```
Read docs/design/build-plan.md in full, especially §2 row 6, §12, and §14 Phase 10. Phases 0–9 are complete (full REST surface: CRUD, HQL, SHQL, inference, retrieval, mesh). You are now implementing Phase 10.

Implement in packages/hgai-mcp:
- FastMCP server mounted at /mcp, tools per §12's table: Hypergraph (list/get/stats/create), Hypernode (list/get/create/update/delete), Hyperedge (list/get/create/update/delete — note update is included here, it was a gap in the reference implementation), Query (query_hql_execute, query_hql_validate, query_shql_execute, query_shql_validate), Inference (infer_check_transitive, infer_expand_edge), Retrieval (search_semantic, search_hybrid), Space/Org (list/get/create/add_member/list_graphs), Mesh (list/get/ping/sync/query).
- Auth middleware shared with hgai-core (accepts JWT or scoped API key) — do not reimplement auth per-module.
- A CI script (scripts/check_mcp_parity.py or similar) that diffs the REST route table against the MCP tool registry and FAILS THE BUILD if a query/search/infer capability exists in one but not the other. Wire this into .github/workflows/ci.yml. This script is the structural fix for §2 row 6 — SHQL tools being silently absent from MCP must become a CI failure, not a silent gap, in this codebase.

Exit criteria: every tool in §12's table has a passing end-to-end test (MCP tool call -> real result, via testcontainers-backed fixtures, not mocked storage). The parity-check script passes in CI and, when you temporarily comment out one MCP tool locally to test the check itself, it correctly fails — verify this, then restore the tool.
```

---

## Prompt 11 — CLI shell & Web UI

```
Read docs/design/build-plan.md in full, especially §2's UI-related notes, §3 (CLI/UI rows), and §14 Phase 11. Phases 0–10 are complete (full REST + MCP surface functional). You are now implementing Phase 11.

Implement in packages/hgai-shell:
- prompt_toolkit REPL, rich for output rendering (tables, colored status — replace any hand-rolled ANSI approach with rich primitives from the start).
- Commands: connect/login, graph/node/edge CRUD verbs, query (HQL), shql (SHQL), help, up/down history navigation (prompt_toolkit gives this by default, confirm it's on).

Implement in apps/web-ui:
- TypeScript + Vite + Preact + Tailwind CSS, feature parity with the reference implementation's UI: login, Organization/Space/Graph management, Hypernode/Hyperedge CRUD (including a dynamic member-row editor for hyperedges), an HQL query editor (syntax highlighting, example queries, validate/run), an SHQL query editor (same treatment), Accounts admin (roles, space assignment), Meshes admin.
- Fetch layer with JWT storage and 401 handling, mirroring the reference implementation's api.js pattern but typed.

This phase is explicitly UI/UX — automated tests alone don't verify it. After building, actually run both: start the full stack via docker-compose, use the shell to log in/create a graph/create nodes+edges/run an HQL query and an SHQL query, then do the same walkthrough in the web UI. Report specifically that you did this walkthrough and what you saw, not just that the build compiled.

Exit criteria: manual smoke-test walkthrough (described above) completed and reported for both shell and web UI. Basic component/unit tests for the UI's query editors and CRUD forms.
```

---

## Prompt 12 — Observability, docs, CI hardening

```
Read docs/design/build-plan.md in full, especially §2 row 8, §12's parity script, §13, and §14 Phase 12. This is the final phase — Phases 0–11 are complete, the full system works end-to-end. You are now implementing Phase 12.

Implement:
- structlog for JSON structured logging across all packages; OpenTelemetry SDK + OTLP exporter for traces and metrics.
- /readyz with real dependency checks (Mongo ping, Qdrant ping) distinct from the existing /healthz liveness check.
- Full CI pipeline in .github/workflows/ci.yml: lint (ruff) + typecheck (mypy strict) + unit + contract + integration test jobs on every PR; build+push a container image on tag. Confirm the coverage gates from §13's table are enforced (≥90% on hgai-storage, hgai-query-hql, hgai-query-shql, hgai-inference; every route has happy-path + auth-denial coverage).
- Generate docs/module-development.md FROM the actual HgaiModule Protocol defined in Phase 2 (introspect the real interface, don't hand-write a description that can drift — this is the direct fix for §2 row 8, where the reference implementation's docs described a base class that didn't exist in code).
- Write/finalize docs/api-reference.md, docs/concepts.md, docs/hello-world.md (a full walkthrough building a small example hypergraph via UI, shell, and REST API in parallel).

As a final verification step, spot-check every documented endpoint and every documented MCP tool against the actual route table and tool registry — list any doc that has drifted from code and fix it before reporting done. This project has a specific documented history of docs describing things that don't exist in code; treat that as a known risk class for this final review pass, not a generic reminder.

Exit criteria: CI pipeline green end-to-end on a clean PR from a fresh clone. All coverage gates met. Docs spot-check complete with zero drift remaining.
```

---

## Prompt 13 — 3D interactive hypergraph visualization *(optional)*

```
Read docs/design/build-plan.md in full, especially §1 (hyperedges are first-class, referenceable like hypernodes), §6.1 (HQL members.* filtering), §7 (REST list endpoints, edge hydration via ?hydrate=n), and §14 Phase 13. Phases 0–12 are complete — the platform is fully functional without this phase. You are now implementing Phase 13, which is OPTIONAL: only proceed if you were explicitly asked to build this phase. It is purely additive to apps/web-ui — do not modify any backend/API package, this phase consumes the existing REST surface and HQL unmodified.

Implement in apps/web-ui:
- A new "Visualize" view using a WebGL 3D force-directed graph component (recommend the `3d-force-graph` library, Three.js-based, self-hostable via the Vite bundle — no CDN/external service dependency), mounted alongside the existing Phase 11 views.
- Rendering mapping: each Hypernode is a scene node; each Hyperedge is ALSO a scene node (visually distinct — smaller radius, color/shape keyed by relation/flavor), with one link per member connecting the hyperedge-node to that member in seq order (directional arrow for hub/transitive/inverse-transitive flavors, undirected for symmetric/direct). Do not render hyperedges as plain lines between two nodes — hyperedges are N-ary and first-class, per §1.
- Initial scene load: parallel GET /graphs/{id}/nodes + GET /graphs/{id}/edges (§7), transformed client-side into the {nodes, links} shape per the mapping above. Bound the default load — warn and require narrowing via the filter panel above roughly 2000 combined nodes+edges rather than attempting to render an unbounded scene.
- Rotation: manual orbit via pointer-drag using the library's default Three.js OrbitControls — no custom camera-control implementation.
- Auto-rotation: a toggle enabling continuous slow camera orbit when idle. It must pause immediately on user drag and resume automatically after a short idle timeout (~3s) once the user releases control.
- Filtering: a filter panel using the same query params as the list endpoints (tags, status, node_type for nodes; relation, flavor for edges — §7). Changing a filter re-fetches nodes/edges with those params and rebuilds the scene graph server-side — do not implement this as client-side show/hide over an unbounded in-memory dataset.
- Hypernode double-click focus: double-clicking a hypernode-typed scene node (not a hyperedge-node) must (1) run an HQL query via POST /query with match: {type: hyperedge}, where: {members.node_id: <id>} to find every hyperedge incident to that node (this member sub-field filtering is already supported per §6.1, do not build a new backend endpoint for it); (2) fetch each incident edge with GET .../{edge_id}?hydrate=1 (§7) to pull full member documents for anything not already present in the loaded scene, merging new nodes/links in; (3) animate the camera to center/zoom on the focused node; (4) highlight the focused node plus its one-hop neighborhood (incident hyperedge-nodes and their other members), dimming everything else. Provide a "clear focus" control (button, or double-click on empty space) that restores the default full-brightness view and camera position.

This is explicitly a UI/UX phase — after building it, run the full stack and actually use the feature: load a seeded graph in the Visualize view, drag to rotate, toggle auto-rotate, apply a filter and confirm the scene rebuilds correctly, double-click a hypernode and confirm the camera focuses with its neighborhood highlighted and any not-yet-loaded neighbors appear correctly hydrated. Report specifically that you did this walkthrough and what you observed, not just that the build compiled.

Exit criteria: manual smoke-test walkthrough (described above) completed and reported. Component tests for the filter-params-to-fetch logic and the scene-graph transform function (hypernode/hyperedge/member → nodes/links) in isolation.
```
