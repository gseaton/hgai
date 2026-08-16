# HypergraphAI v2 — Greenfield Build Plan

**Audience:** an AI coding agent (Claude Code or equivalent) building this system from an empty repository, with no access to the original `hgai` codebase. This document is self-contained.

**Goal:** a production-grade semantic knowledge hypergraph platform — hyperedges as first-class N-ary relationships, composable hypergraphs, two declarative query languages, MCP-native agent access, multi-tenant RBAC, and (new) hybrid retrieval + real inferencing + event sourcing.

---

## 0. How to use this document

1. Execute **Build Phases** (§14) in order. Each phase lists goal, deliverables, and exit criteria — do not start phase *N+1* until phase *N*'s exit criteria pass.
2. §1–§13 are the specs each phase implements against. Read the relevant spec section before starting a phase.
3. Where this doc gives a schema/interface, treat field names and types as binding; treat prose rationale as context, not instruction.
4. §2 encodes lessons from a prior implementation of this same system — a list of defects to not reintroduce. Treat it as a checklist during code review of each phase.
5. When a decision isn't covered here, prefer: fewer moving parts > more moving parts; explicit config > implicit magic; a working vertical slice > a complete horizontal layer.

---

## 1. Product definition

HypergraphAI stores knowledge as a **hypergraph**: hypernodes (entities) connected by hyperedges (N-ary, first-class, independently-attributed relationships — not just edges with two endpoints). This is deliberately not a property graph and not a vector store; it is a semantic substrate that both can be layered onto.

Non-negotiable tenets (carried from v1, keep these):

- Hyperedges are first-class citizens — they carry their own attributes, tags, status, temporal validity, and can themselves be referenced like hypernodes.
- Hypergraphs compose: an *instantiated* hypergraph holds data directly; a *logical* hypergraph composes other hypergraphs (local or remote) for querying without copying data.
- Every artifact (node, edge, graph) carries `tags: [str]` and `status` (active/draft/archived); `active` is the default operational visibility.
- Everything is a module. Core function ships as modules under one naming convention; third parties can add modules the same way.
- Two query languages: **HQL** (Mongo-filter-style, fast/direct) and **SHQL** (SPARQL-style pattern matching with `?var` bindings, multi-hop joins, FILTER/OPTIONAL/UNION) — both YAML-first, JSON accepted.
- Temporal qualifiers (`valid_from`/`valid_to`) support point-in-time (PIT) queries.
- RBAC: global roles (admin/user/agent/readonly) layered with per-tenant space membership roles (owner/admin/member/viewer).
- Federation: independent HypergraphAI servers combine into a **mesh**; queries can target `mesh.server.graph` dot-refs and fan out.
- MCP is a first-class API surface, not an afterthought bolted onto REST.

New tenets for v2 (not in v1, added deliberately — see §2's "Add" column for why):

- **Meaning is retrievable three ways**: structural (HQL/SHQL traversal), lexical (exact/keyword), semantic (embeddings). All three are native query modes, not app-layer bolt-ons.
- **Mutations are events.** Every create/update/delete on a node, edge, or graph appends an immutable event record before/alongside the state change. This is the audit log — not a separate, weaker parallel system.
- **Provenance and confidence are optional fields on the data itself**, not external metadata: a hyperedge can say where it came from and how sure the system is, when that matters.
- **Inferencing is real, not aspirational.** SKOS/OWL-style relation semantics (broader/narrower, inverse-of, transitive, symmetric) are declared as data (RelationType hypernodes + axiom hyperedges) and actually evaluated at query time.

---

## 2. Lessons from the reference implementation

A prior implementation of this exact system exists and was audited. Its concepts are sound — reuse the design; **do not** reuse these specific defects. This table is the single most load-bearing part of this document for code-review purposes.

| # | Defect in reference impl | Fix in v2 |
|---|---|---|
| 1 | Query engines (HQL/SHQL) construct raw MongoDB operators (`$elemMatch`, etc.) directly — storage abstraction is backend-agnostic in name only, leaks Mongo syntax into the query layer. | Query engines compile to a backend-neutral **Filter IR** (§6.3). Only the storage backend translates IR → native query. A second backend must be pluggable without touching HQL/SHQL code. |
| 2 | `Dockerfile` never copies the local sub-packages (only `hgai/`, `ui/`, `shell/`, `scripts/`); `pyproject.toml`'s package-find include list is missing two of the modules entirely. Docker image is broken at runtime for anyone who doesn't notice. | Single `uv` workspace, `Dockerfile` does `COPY . .` + `uv sync --frozen`. No hand-maintained include lists that can drift from the actual module set (§4, §14 Phase 0). |
| 3 | Two full CRUD surfaces exist for the same resources: `/graphs/...` and `/spaces/{id}/graphs/...`, hand-duplicated. | One canonical REST surface; tenant scoping resolved from the resource's own `space_id`, not the URL shape (§7). |
| 4 | Admin bootstrap credentials default to a static, weak, checked-in value (`admin`/`pwd357`) used for both DB root and app admin. | No default admin password ships. First boot generates a random password, prints it once to stdout/log, and requires rotation via a forced-change flag. Secrets fail closed (missing `SECRET_KEY` = refuse to start), never fall back to a default. |
| 5 | `hgai/core/inference.py` implements SKOS/transitive inference logic but has **zero call sites** anywhere — dead code behind a "planned" docstring, while the data model (`EdgeFlavor.transitive`, `skos_broader/narrower`) implies it works. | Inferencing is wired into the query layer from day one (§9) or the corresponding model fields don't ship until it is. Never expose a schema field whose semantics nothing implements. |
| 6 | No SHQL tools in the MCP server — only HQL is agent-reachable, despite SHQL being the more expressive language for the multi-hop questions agents actually ask. | MCP tool coverage is generated/audited against the REST+query surface (§10, §14 Phase 6); both query languages get parity tools. |
| 7 | Test suite covers isolated tricky functions (hyperkey generation, filter building, member-matching) but has **zero coverage** of REST routers, auth/RBAC, the storage backend, or MCP tools. Mesh tests mock `httpx.AsyncClient` incorrectly and fail (`MagicMock` used where `AsyncMock` was needed). | Testing pyramid is specified per-layer with minimum coverage gates (§13), including real integration tests via Testcontainers, not just unit tests of pure functions. |
| 8 | `docs/module-development.md` describes an `HgaiModule` base class that doesn't exist — every module is independently duck-typed. Docs and code drift silently. | Define the module interface as an actual ABC/Protocol in code first (§4.2); docs are generated from it, not hand-written in parallel (§14 Phase 12). |
| 9 | Storage abstraction is solid where it isn't leaking Mongo syntax (typed filter/patch dataclasses, clean `get_storage()`/`init_storage()` indirection) — worth keeping as-is. | Carry this pattern forward unchanged; it's the one part of the storage layer that was done right. |
| 10 | Federation (mesh) engine itself (ping, sync, dot-ref resolution, federated query fan-out/merge) is fully implemented and works; only its tests were broken. | Reuse this design (§11) — it doesn't need rethinking, just correct test doubles. |

---

## 3. Technology stack decisions

Keep the same technology family as the reference implementation (per product requirement); improve specific weak points. One decision per row — do not introduce alternatives mid-build.

| Area | v1 (reference) | v2 (this build) | Why |
|---|---|---|---|
| Language | Python 3.11 | Python 3.12+ | Faster, better error messages, still same ecosystem. |
| Packaging/env | pip + requirements.txt + hand-maintained setuptools include list | **uv** workspace, `src/` layout per package | Structurally eliminates defect #2 above; one lockfile, one `uv sync`. |
| Web framework | FastAPI + uvicorn | FastAPI + uvicorn (unchanged) | Already correct for this workload. |
| Validation | Pydantic v2 | Pydantic v2 (unchanged) | Already correct. |
| Primary store | MongoDB (motor/pymongo) | MongoDB (motor/pymongo), self-hostable | Keep — document model fits flexible-attribute hypernodes/hyperedges well. Community edition is fine; no Atlas lock-in. |
| Storage abstraction | ABCs + dataclass filters, but leaks Mongo operators (defect #1) | Same ABC pattern + a backend-neutral **Filter IR** compiled by query engines, translated only inside the backend package | Fixes defect #1; keeps what worked. |
| Vector/semantic search | none | **Qdrant** (self-hosted, Docker-composable, open source) | Adds the "semantic retrieval" tenet without Atlas-only lock-in or a heavy polyglot stack. One new service, clearly justified. |
| Lexical/keyword search | none | MongoDB text indexes (v1 of this feature); Meilisearch as a later swap-in if text index relevance proves insufficient | Ship something in-stack first; don't add a fourth service before it's proven necessary. |
| Auth | JWT (python-jose) + bcrypt, 2 static global API keys, default admin password | JWT (python-jose) + bcrypt (unchanged libs), per-account scoped+hashed API keys, no default secrets | Same libraries, closes defect #4 and the global-superuser-API-key design smell. |
| Query engines | HQL + SHQL, hand-rolled expression evaluator, Mongo-leaky | HQL + SHQL (unchanged languages/semantics), compiled through Filter IR | Same user-facing languages; internal correctness fix. |
| Inferencing | Dead code, unused schema fields | Declarative RelationType/axiom model, evaluated at query time, cached transitive closures | Closes defect #5; see §9. |
| MCP | FastMCP / official MCP SDK, HQL-only tools | FastMCP / official MCP SDK, full HQL+SHQL+inference+retrieval tool parity | Closes defect #6. |
| CLI shell | prompt_toolkit REPL | prompt_toolkit REPL (unchanged) + `rich` for output rendering | Same tool, nicer tables/output than hand-rolled ANSI. |
| Web UI | Vanilla JS SPA + Bootstrap 5, no build step | TypeScript + Vite + Preact, Tailwind CSS | Same "SPA talking to REST/MCP" shape; adds type safety and a real build pipeline without adopting a heavy framework. |
| Testing | pytest, unit-only, broken async mocks | pytest + pytest-asyncio + **testcontainers** (real Mongo/Qdrant in CI) + httpx `ASGITransport` for API tests | Closes defect #7. |
| Type checking | none enforced | mypy (strict) or pyright, ruff (lint+format) in CI | Wasn't present before; cheap to add, catches a large class of bugs before runtime. |
| CI/CD | none | GitHub Actions: lint + typecheck + test on PR; build+push image on tag | Wasn't present before. |
| Observability | basic `/health` | structlog (JSON logs) + OpenTelemetry (traces/metrics) + `/healthz` + `/readyz` | Needed for anything beyond a demo deployment. |
| Deployment | docker-compose (mongo + app), Dockerfile missing local packages | docker-compose (mongo + qdrant + app [+ otel-collector optional]), Dockerfile fixed via workspace `COPY . .` | Closes defect #2. |
| Multi-tenancy | Account → Space (2 tiers) | Account → **Organization** → Space (3 tiers) | Was designed but never built in v1 (`docs/design/prompt-gen-plan-orgs.md`); build it this time. |
| Eventing | `audit_log` collection exists but nothing writes to it in a structured, replayable way | Append-only `events` collection is the audit log; state mutations and event writes happen in the same Mongo transaction | New tenet (§1); see §11. |

---

## 4. Repository layout

```
hgai/
  pyproject.toml                 # uv workspace root
  uv.lock
  README.md
  docker-compose.yml
  Dockerfile
  .env.example
  .github/workflows/ci.yml
  packages/
    hgai-core/         src/hgai_core/         # FastAPI app factory, config, lifespan, auth, models, api routers
    hgai-storage/       src/hgai_storage/       # storage ABCs, Filter IR, filter/patch dataclasses
    hgai-storage-mongodb/ src/hgai_storage_mongodb/ # Mongo backend: connection, indexes, stores/, IR translator
    hgai-query-hql/     src/hgai_query_hql/     # HQL parser + planner + executor (emits Filter IR)
    hgai-query-shql/    src/hgai_query_shql/    # SHQL parser + pattern engine (emits Filter IR)
    hgai-inference/     src/hgai_inference/     # RelationType/axiom evaluation, transitive closure cache
    hgai-retrieval/     src/hgai_retrieval/     # embedding provider, Qdrant client, hybrid ranker
    hgai-mesh/          src/hgai_mesh/          # federation: ping/sync/dot-ref resolution/fan-out
    hgai-mcp/           src/hgai_mcp/           # FastMCP server + tool registrations
    hgai-events/         src/hgai_events/        # event envelope, append + replay helpers
    hgai-shell/          src/hgai_shell/         # prompt_toolkit REPL + rich output
  apps/
    web-ui/               # TypeScript + Vite + Preact SPA
  scripts/                 # mongo-init.js, seed_data.py, qdrant-init
  tests/
    unit/                  # pure-function tests, per package
    contract/               # storage backend ABC compliance suite, run against every backend
    integration/             # full-stack API tests via testcontainers + ASGITransport
  docs/
    concepts.md, hello-world.md, module-development.md, api-reference.md
```

**Module interface (fixes defect #8):** define once in `hgai-core`:

```python
class HgaiModule(Protocol):
    name: str
    version: str
    description: str
    def get_api_router(self) -> APIRouter | None: ...
    def get_mcp_tools(self) -> list[MCPTool] | None: ...
    async def on_startup(self, app: FastAPI) -> None: ...
    async def on_shutdown(self, app: FastAPI) -> None: ...
```

Every module (`hgai_query_hql`, `hgai_mesh`, `hgai_mcp`, etc.) implements this Protocol concretely — no duck typing. `hgai_core.main.create_app()` discovers and mounts modules from an explicit registry list (not silent `try/except BaseException` — a module that fails to load **fails the app startup** with a clear error, unless explicitly marked optional in config).

---

## 5. Canonical data model

All models are Pydantic v2, `*Base` / `*Create` / `*Update` / `*InDB` / `*Response` pattern. Every model inherits `tags: list[str]`, `status: Literal["active","draft","archived"] = "active"`, `attributes: dict[str, Any]`, and timestamps (`system_created`, `system_updated`, `created_by`, `version: int`).

| Entity | Key fields (beyond common base) | Notes |
|---|---|---|
| **Hypernode** | `id`, `label`, `type` (default `"Entity"`), `description`, `valid_from`/`valid_to`, `hypergraph_id`, `provenance?`, `confidence?` | `provenance`/`confidence` optional — only set when the node was derived/extracted rather than authored directly. |
| **Hyperedge** | `id`, `relation`, `label`, `flavor: hub\|symmetric\|direct\|transitive\|inverse-transitive`, `members: list[{node_id, seq}]`, `valid_from`/`valid_to`, `hypergraph_id`, `hyperkey` (SHA-256 of relation+sorted members, dedup key), `provenance?`, `confidence?` | `skos_broader`/`narrower`/inverse fields from v1 are **removed** from the edge itself — semantics now live in RelationType/axiom hypernodes (§9), not ad hoc fields on every edge. |
| **Hypergraph** | `id` (no `.` — reserved for mesh dot-notation), `label`, `type: instantiated\|logical`, `space_id`, `composition: list[str]` (for logical graphs), `remote_refs: list[RemoteGraphRef]`, `node_count`, `edge_count` | Unchanged from v1. |
| **Organization** *(new)* | `id`, `name`, `owner_account_id` | Top tenancy tier. Space `id` uniqueness becomes scoped within an org (was global in v1). |
| **Space** | `id`, `name`, `org_id` *(new FK)*, `members: [{account_id, role: owner\|admin\|member\|viewer}]` | Adds `org_id`; role semantics unchanged. |
| **Account** | `username`, `role: admin\|user\|agent\|readonly`, `password_hash`, `permissions: {graphs: [str], operations: [str]}`, `api_keys: [{key_hash, label, created_at, last_used}]` *(new, replaces 2 static global keys)* | Global role + per-account graph/operation grants, same as v1. |
| **RelationType** *(new)* | `id`, `name`, `axioms: [str]` (e.g. `owl:transitive`, `owl:symmetric`, `owl:inverse-of:<other-relation-id>`, `skos:broader-of:<other-relation-id>`) | A hypernode of `type: "RelationType"`. See §9. |
| **Event** *(new)* | `id`, `entity_type`, `entity_id`, `op: create\|update\|delete`, `actor_account_id`, `before: dict\|null`, `after: dict\|null`, `graph_id`, `ts` | Append-only, written in the same transaction as the mutation. This *is* the audit log. |
| **Mesh / MeshServer** | unchanged from v1 | `server_id`, `server_name`, `url`, `api_token?`, `graphs: []` cache. |

---

## 6. Query layer

### 6.1 HQL (unchanged surface, from v1)

YAML-first, top-level `hql:` key. `from` (graph id / list / `space/graph` / mesh dot-ref), `match` (type, node_type, relation, flavor, id, nodes), `where` (attribute equality, `tags`, dot-paths, `members.*`), `return`, `as`, `limit`/`skip`, `distinct`, `at` (PIT timestamp), `aggregate` (`count`, `group_by`). Query result caching by hash of normalized query; PIT filters against `valid_from`/`valid_to`.

**Result shape.** HQL is single-entity-type, direct filtered retrieval — not pattern matching. A query returns a flat list of documents, all of the same kind (`match.type: hypernode` or `hyperedge`), each either the full matched document or a `return:` field projection of it. There is no binding-table/multi-variable result like SHQL (§6.2) — a query needing to correlate several related entities in one result row is a SHQL query, not an HQL one.

**Attribute access is same-document-only.** `where:`/`return:` dot-paths (e.g. `attributes.foo.bar`) resolve against the single matched document only. A hyperedge's `members:` field supports where-filtering on member sub-fields (`node_id`, `seq` — via `Eq`/`ElemMatch` in the Filter IR, §6.3, so two sub-fields filtered together correctly constrain the *same* array element), but member results are always returned as bare `{node_id, seq}` — HQL never hydrates a member's node document. Fetching a member's `label`/`attributes` requires SHQL (§6.2), or a follow-up HQL bulk `id` lookup (below). This is a deliberate boundary, kept from v1: HQL optimizes for fast single-collection retrieval; SHQL owns joins/traversal. Don't add cross-document joins to HQL — that's scope creep into what SHQL already does.

**`id` supports multi-value match.** `match.id` / `where.id` accepts either a single literal or a list, compiled to the Filter IR's `In` (§6.3), for bulk lookup by id — e.g. hydrating a batch of member `node_id`s gathered from a prior query. Include a dedicated test for this: the reference implementation had `where: {id: {$in: [...]}}` against hypernodes silently match zero rows, because unrecognized `where` keys fell through to an `attributes.<key>` filter instead of erroring — it failed silently rather than loudly, which is the worse failure mode.

**v2 addition:** `match.flavor: transitive` (or `inverse-transitive`) triggers the inference engine (§9) instead of returning raw unexpanded edges.

Worked examples:

```yaml
# Direct filtered retrieval + projection
hql:
  from: org-graph
  match: { type: hypernode, node_type: Employee }
  where: { attributes.department: "engineering", tags: { $in: ["fte"] } }
  return: [id, label, attributes.title]
  limit: 50
```

```yaml
# Bulk hydration by id — the HQL-side half of "get member ids from a
# hyperedge (HQL or SHQL), then hydrate the node docs (HQL)"
hql:
  from: org-graph
  match: { type: hypernode, id: [emp-014, emp-042, emp-091] }
  return: "*"
```

```yaml
# PIT + aggregate
hql:
  from: org-graph
  match: { type: hyperedge, relation: reports-to }
  at: "2025-01-01T00:00:00Z"
  aggregate: { group_by: attributes.department, op: count }
```

### 6.2 SHQL (unchanged surface, from v1)

YAML-first, top-level `shql:` key: `from`, `where` (list of patterns: `node`, `edge` w/ `members` sub-patterns, `filter`, `optional`, `union`), `select`, `limit`, `offset`. `?var` bindings resolved left-to-right; a member sub-pattern is an *anchor* if it has a literal `id` **or** references an already-bound `?var` (v1 fixed this correctly late in its life — keep that behavior, don't regress to the old "only `id:` counts as anchor" bug). `filter:` expressions need a real small grammar (Lark or a hand-written recursive-descent parser) — v1's string-scanning evaluator is fragile; replace it, keep the same `filter:` expression syntax users already write.

**What "SPARQL-esque" means concretely — results are binding tables.** A query does not return a flat list of matched hypernodes/hyperedges; it returns rows of `{?var: resolved_value, ...}` — one row per satisfying assignment of every `?var` bound anywhere in `where:`, same as a SPARQL `SELECT`. `select:` picks which bindings (or sub-fields of them) appear in each row; it does not change what was matched.

**Attribute access on any bound variable, at any hop.** Any `?var` bound by *any* pattern — a `node:` pattern, an `edge:` pattern, or a `members:` sub-pattern, regardless of how many hops from the first pattern — resolves to its full underlying document (hypernode or hyperedge dict) and is addressable by dot-path in both `select:` and `filter:`: `?var.label`, `?var.attributes.<nested.path>`, `?member.attributes.skill_level`, etc. There is no separate mechanism for "the initial match" vs. "later matches" — every bound variable is equally queryable.

**Multi-hop chaining is just anchor reuse, not a path operator.** To walk a second hop, add another `edge:`/`node:` pattern whose member sub-pattern (or `id:`) references a `?var` already bound by an earlier pattern — that reference is what makes it an anchor (per the anchor rule above) and joins the new pattern to the existing bindings. There is no dedicated "path"/"traverse" keyword; chaining depth is just how many patterns in sequence reuse a prior binding.

Worked example — two hops, selecting an attribute from the hop-2 node:

```yaml
shql:
  from: org-graph
  where:
    - node: { bind: "?person", type: Employee, id: emp-042 }
    - edge: { relation: reports-to, members: [{ bind: "?person" }, { bind: "?manager" }] }
    - edge: { relation: member-of, members: [{ bind: "?manager" }, { bind: "?team" }] }
  select: [?person.label, ?manager.label, ?team.attributes.department]
```

`?manager` is bound by hop 1 (as the unconstrained member of the `reports-to` edge) and reused as the anchor of hop 2's `member-of` edge; `?team` is a hop-2 binding. All three variables' attributes are selectable in the same `select:` regardless of which pattern first bound them.

### 6.3 Filter IR (new — fixes defect #1)

```python
# hgai_storage/filter_ir.py
FilterExpr = Eq | Ne | In | Gt | Gte | Lt | Lte | Exists | And | Or | Not | ElemMatch

@dataclass(frozen=True)
class Eq:  field: str; value: Any
@dataclass(frozen=True)
class In:  field: str; values: list[Any]
@dataclass(frozen=True)
class ElemMatch:  field: str; sub: FilterExpr   # e.g. members array, multiple sub-fields must match same element
@dataclass(frozen=True)
class And:  clauses: list[FilterExpr]
# ... Ne/Gt/Gte/Lt/Lte/Exists/Or/Not mirror the above
```

HQL/SHQL compile `where:`/pattern clauses to `FilterExpr` trees. `hgai_storage_mongodb` is the **only** package allowed to import `pymongo`/`motor` operators and translate `FilterExpr → dict`. A second backend (e.g. Postgres+JSONB, deferred — see §15) would translate the same IR to SQL without touching either query engine. Contract test (§13): run the same `FilterExpr` fixtures against every registered backend, assert identical result sets.

---

## 7. API surface (fixes defect #3 — one CRUD tree, not two)

Base: `/api/v1`. All graph-scoped resources resolve tenancy from the graph's own `space_id`/`org_id` — no duplicated `/spaces/{id}/graphs/...` tree.

| Route | Methods | Notes |
|---|---|---|
| `/auth/token`, `/auth/me` | POST, GET | JWT password flow |
| `/orgs` | CRUD | admin/org-owner only |
| `/spaces` | CRUD, `/spaces/{id}/members` | scoped within org |
| `/graphs` | CRUD, `/graphs/{id}/stats`, `/graphs/{id}/export`, `/graphs/{id}/import` | `space_id` is a field on create, not a URL segment |
| `/graphs/{graph_id}/nodes` | CRUD | |
| `/graphs/{graph_id}/edges` | CRUD | `GET .../{edge_id}` supports `?hydrate=<n>`, see below |
| `/query` (HQL), `/shql/query` | POST, `/validate` variants | |
| `/search/semantic`, `/search/hybrid` *(new)* | POST | embedding-based and blended retrieval (§10) |
| `/infer/transitive`, `/infer/expand` *(new)* | POST | direct REST access to the inference engine, mirrors MCP tools |
| `/accounts` | CRUD (admin only) | includes scoped API-key issuance |
| `/meshes` | CRUD, `/ping`, `/sync`, `/query`, proxy passthrough | unchanged from v1 |
| `/events` *(new)* | GET (filterable by entity/graph/time range) | read path over the append-only event log |
| `/healthz`, `/readyz` | GET | liveness vs. readiness (DB + Qdrant ping) |

**Request/response conventions.** Every route above except `/auth/token` and `/healthz` requires `Authorization: Bearer <jwt-or-api-key>` — one shared auth dependency (§8), not reimplemented per router. List endpoints return a pagination envelope: `{items: [...], total: int, limit: int, offset: int}`; single-resource endpoints (get/create/update) return the resource document directly, no envelope. Errors return one consistent shape regardless of which router raised them — `{error: {code: str, message: str, details?: any}}` — paired with the matching HTTP status: `400` malformed request, `401` unauthenticated, `403` unauthorized, `404` not found, `409` conflict (e.g. duplicate id), `422` semantic validation (e.g. a hyperedge referencing a nonexistent member `node_id`). List endpoints accept `limit`/`offset` plus common filters `tags`, `status`, and entity-specific filters (`node_type` on nodes; `relation`/`flavor` on edges).

**Edge hydration — the REST analogue of SHQL's member-attribute access (§6.2).** A single-edge `GET` accepts `?hydrate=<n>` (default `0`): at `0`, `members` returns bare `{node_id, seq}` (matches HQL's same-document-only boundary, §6.1); at `1`, each member is replaced by its full hypernode document (or hyperedge document, if that member is itself an edge); at `n > 1`, hydration recurses through hyperedge members up to `n` levels — hypernode leaves populate at whatever depth they're reached, hyperedge documents populate at each intermediate level. This gives the common "fetch this edge and its members' attributes" case a one-call REST path without requiring SHQL. Cap `n` server-side (e.g. max `5`) to bound response size and query cost — reject larger values with `400`, don't silently clamp.

Worked examples:

```json
// GET /api/v1/graphs/org-graph/edges/edge-team-x?hydrate=1  (200)
{
  "id": "edge-team-x",
  "relation": "member-of",
  "flavor": "hub",
  "members": [
    { "seq": 0, "node": { "id": "team-x", "label": "Team X", "attributes": { "department": "engineering" } } },
    { "seq": 1, "node": { "id": "emp-042", "label": "Dana", "attributes": { "title": "SRE" } } }
  ]
}
```

```json
// GET /api/v1/graphs/org-graph/nodes?node_type=Employee&limit=2  (200)
{ "items": [ { "id": "emp-014", "label": "Alex" }, { "id": "emp-042", "label": "Dana" } ], "total": 37, "limit": 2, "offset": 0 }
```

```json
// POST /api/v1/graphs/org-graph/edges  with a members[].node_id that doesn't exist  (422)
{ "error": { "code": "invalid_reference", "message": "member node_id 'emp-999' does not exist in graph 'org-graph'", "details": { "field": "members[1].node_id" } } }
```

---

## 8. Security model

- JWT (HS256 or better) for user sessions; per-account **scoped, hashed** API keys for machine/agent access (replaces v1's two global superuser keys — closes a real privilege-escalation smell).
- No default secrets ship. Missing `SECRET_KEY` at startup = refuse to boot with a clear error. First-run admin bootstrap generates a random password, prints once, forces rotation.
- RBAC: global `Role` × per-account `{graphs, operations}` grants × per-Space `SpaceRole`, now nested under `Organization`. Space membership remains the sole gate for space-scoped graphs (a deliberate, tested v1 design decision — preserve it: an account's global `graphs: ["*"]` does not cross tenant boundaries).
- Optional per-artifact `policy` field (deferred to post-v1, see §15) is the extension point for "this fact may be summarized but not disclosed externally" style constraints from the retrieval-layer design goals — don't build it in v1, but don't design the model in a way that blocks adding it later (a `policy: dict | None` field reserved on Hypernode/Hyperedge is enough for now).

---

## 9. Inferencing engine (fixes defect #5 — make it real)

Relation semantics are declared as data, evaluated at query time, not hardcoded per-relation logic:

1. A **RelationType** hypernode declares axioms: `axioms: ["owl:transitive"]`, `["owl:symmetric"]`, `["owl:inverse-of:rel:contains"]`, `["skos:broader-of:rel:sibling"]`.
2. `hgai_inference` exposes two operations, called from both HQL (`match.flavor: transitive`) and SHQL (pattern evaluation) and as direct MCP/REST tools:
   - `expand_edge(edge) -> list[Hyperedge]` — for edges whose relation has `inverse-of`/`symmetric` axioms, synthesizes the implied edge(s), tagged `_inferred: true`, `_source_edge: <id>`, `_axiom: <axiom-string>` (e.g. `"owl:inverse-of:rel:contains"` — kept for traceability, so a caller can tell *why* an edge was inferred, not just that it was). Never persisted — computed at read time.
   - `check_transitive(start_id, end_id, relation, graph_ids, max_depth=10) -> {reachable: bool, path: list[str] | None}` — BFS over hyperedges filtered by relation, bounded by `max_depth`. `path` is the ordered list of *hyperedge ids* forming the chain (not node ids) — consistent with hyperedges being first-class, this lets a caller hydrate/select attributes on each hop the same way as any other edge (§6.2, §7).
3. **Materialized closure cache** for hot transitive relations: a background job (or on-write trigger) precomputes reachability for `owl:transitive` relations flagged `cache: true` on the RelationType, stored in a `transitive_closures` collection, invalidated on relevant edge writes. Query-time `check_transitive` checks the cache first, falls back to live BFS.
4. This is a resurrection of a real, previously-designed-but-never-wired spec — do not redesign the axiom vocabulary from scratch; the table above is the full syntax needed for v1 of this feature.

**When inference fires — explicit, never implicit.** Per §0's "explicit config over implicit magic": queries return literal stored edges only unless inference is explicitly requested. Two triggers, both opt-in: HQL/SHQL `match.flavor: transitive` (or `inverse-transitive`) triggers `check_transitive`-backed expansion, as already stated in §6.1; a query- or pattern-level `infer: true` flag triggers `expand_edge`-based inverse-of/symmetric expansion for edges matched by that query/pattern. A plain query with neither never calls into `hgai_inference` at all — no silent expansion.

**Inferred edges are first-class results, not a side channel — this is what makes them chainable.** When `infer: true` expands an edge inline during SHQL pattern evaluation, the synthesized edge is bound to `?var` exactly like a stored edge: it can anchor a later hop (§6.2's anchor-reuse rule), and its attributes (and its `_inferred`/`_source_edge`/`_axiom` fields) are selectable via the same dot-path mechanism as any other bound variable. Inference does not stop the chain — a multi-hop SHQL query can walk from a real edge, across an inferred one, into a further real edge, in one query. The same applies to REST: a `hydrate=n` fetch (§7) on an edge that was itself synthesized by `check_transitive`'s `path` follows the same hydration rules as a stored edge.

Worked examples:

```yaml
# HQL — does A transitively contain B? (flavor triggers inference, no separate call needed)
hql:
  from: org-graph
  match: { type: hyperedge, relation: contains, flavor: transitive, nodes: [warehouse-1, pallet-042] }
  return: "*"
```

```yaml
# SHQL — chain a real edge into an inferred inverse-of edge, then a further real edge,
# selecting attributes at every hop including the inferred one
shql:
  from: org-graph
  where:
    - node: { bind: "?item", id: pallet-042 }
    - edge: { infer: true, relation: contained-by, members: [{ bind: "?item" }, { bind: "?container" }] }
    - edge: { relation: located-in, members: [{ bind: "?container" }, { bind: "?zone" }] }
  select: [?item.label, ?container.label, ?container.attributes._inferred, ?zone.attributes.zone_code]
```

```json
// POST /api/v1/infer/transitive  { "start_id": "warehouse-1", "end_id": "pallet-042", "relation": "contains" }  (200)
{ "reachable": true, "path": ["edge-wh1-rack3", "edge-rack3-pallet042"] }
```

---

## 10. Retrieval layer (new capability, not in v1)

Three retrieval modes, one query surface:

- **Structural** — HQL/SHQL, unchanged.
- **Lexical** — MongoDB text index on `label`/`description`/`attributes.*` (configurable per hypergraph). `/search/lexical` or as a HQL `where` operator (`$text`).
- **Semantic** — embeddings stored in Qdrant, one collection per hypergraph (or per org, TBD at implementation time — default to per-hypergraph for isolation). `hgai_retrieval` owns an `EmbeddingProvider` interface (pluggable: local model or hosted API) so the embedding backend isn't hardcoded into the rest of the system.
- **Hybrid** — `/search/hybrid`: blended rank of semantic similarity + lexical relevance + graph proximity (hop distance from a seed node, if provided) + freshness (`system_updated` recency) + optional confidence. Start with a simple weighted-sum scorer; don't build a learned ranker in v1.

Embeddings are computed for hypernode/hyperedge `label + description + attributes` text representation on write (async, non-blocking — queue via the event log: an `EmbeddingWorker` subscribes to `Event` writes and upserts vectors). This is the first real consumer of the eventing layer (§11) beyond audit.

---

## 11. Eventing & audit (new capability, replaces v1's inert `audit_log`)

- Every create/update/delete on Hypernode/Hyperedge/Hypergraph writes an `Event` document in the **same MongoDB transaction** as the state mutation (Mongo multi-document ACID transactions, single replica set is sufficient — document this as a deployment requirement, a standalone `mongod` without a replica set cannot do transactions).
- `GET /events` is the audit trail — filterable by entity, graph, actor, time range.
- Event writes are also the trigger point for async consumers (embedding worker, transitive-closure cache invalidation, future webhook/subscription features). v1 of this: an in-process asyncio queue drained by workers at startup; do not stand up Kafka/RabbitMQ for this — it's not justified at this system's scale yet.

---

## 12. MCP server (fixes defect #6)

FastMCP, mounted at `/mcp`, tools organized by domain, full parity with REST:

| Domain | Tools |
|---|---|
| Hypergraph | list, get, stats, create |
| Hypernode | list, get, create, update, delete |
| Hyperedge | list, get, create, update *(added — v1 was missing edge update)*, delete |
| Query | `query_hql_execute`, `query_hql_validate`, **`query_shql_execute`, `query_shql_validate`** *(added)* |
| Inference | **`infer_check_transitive`, `infer_expand_edge`** *(new)* |
| Retrieval | **`search_semantic`, `search_hybrid`** *(new)* |
| Space/Org | list, get, create, add_member, list_graphs |
| Mesh | list, get, ping, sync, query |

Auth: Bearer token, accepts either a valid JWT or a scoped API key (same as REST) — one middleware, shared with `hgai-core`, not reimplemented per-module.

**Enforcement mechanism for defect #6 not recurring:** a CI check (script in `scripts/`) diffs the REST route table against the MCP tool registry and fails the build if a query/search/infer capability exists in one but not the other.

---

## 13. Testing strategy & quality gates

| Layer | Tooling | Scope | Gate |
|---|---|---|---|
| Unit | pytest | Pure functions per package (hyperkey gen, filter compilation, member-pattern matching, expression parsing) | ≥90% coverage on `hgai_storage`, `hgai_query_hql`, `hgai_query_shql`, `hgai_inference` |
| Contract | pytest + testcontainers (real Mongo) | Every storage backend implementation runs the same ABC-compliance suite | 100% of ABC methods covered, all registered backends pass |
| Integration | pytest + testcontainers (Mongo, Qdrant) + httpx `ASGITransport` | Full REST request/response cycles, auth/RBAC enforcement, MCP tool calls end-to-end | Every route in §7's table has ≥1 happy-path + ≥1 auth-denial test |
| Type checking | mypy strict (or pyright) | All packages | Zero errors, CI-blocking |
| Lint/format | ruff | All packages | Zero errors, CI-blocking |

`httpx.AsyncClient` mocking (the specific thing that broke in v1's mesh tests): use `respx` or `AsyncMock` with explicit `__aenter__`/`__aexit__` wiring, never a bare `MagicMock` on an async context manager — this is worth a one-line lint/review note since it silently produced 3 failing tests in the reference implementation.

---

## 14. Build phases

Execute in order. Each phase's exit criteria must pass (tests green, or explicitly stated manual check) before starting the next.

**Phase 0 — Workspace scaffold**
Deliverables: `uv` workspace root, all `packages/*` stubs with empty `src/` + `pyproject.toml`, `Dockerfile`, `docker-compose.yml` (mongo + qdrant + app), `.env.example`, CI skeleton (lint+typecheck job only, no tests yet).
Exit: `uv sync` succeeds; `docker compose up` boots an empty FastAPI app that responds on `/healthz`.

**Phase 1 — Storage core**
Deliverables: `hgai_storage` (ABCs, Filter IR, filter/patch dataclasses), `hgai_storage_mongodb` (connection, indexes incl. partial-unique org/space-scoped ids, PIT sparse indexes, IR→Mongo translator).
Exit: contract test suite passes against Mongo backend via testcontainers.

**Phase 2 — Core models & config**
Deliverables: `hgai_core` models (§5 — Hypernode, Hyperedge, Hypergraph, Organization, Space, Account, RelationType, Event, Mesh), `Settings` (pydantic-settings, `HGAI_` prefix, fail-closed on missing secrets), `HgaiModule` Protocol.
Exit: unit tests for model validation (id format rules, temporal field constraints, hyperkey determinism).

**Phase 3 — Auth & REST CRUD**
Deliverables: JWT auth, scoped API keys, `/orgs`, `/spaces`, `/graphs`, `/graphs/{id}/nodes`, `/graphs/{id}/edges` per §7 (single tree, no duplication), admin bootstrap with generated-password flow.
Exit: integration tests cover every route's happy path + RBAC denial path; no default credentials anywhere in code or config.

**Phase 4 — Eventing**
Deliverables: `hgai_events` envelope, transactional event-write on every mutation from Phase 3, `/events` read endpoint, in-process async worker queue.
Exit: mutation → event round-trip integration test; event write failure rolls back the state mutation (transaction correctness).

**Phase 5 — HQL**
Deliverables: `hgai_query_hql` parser/planner/executor compiling to Filter IR, `/query` + `/query/validate`, query result caching.
Exit: HQL example queries from §6.1 pass integration tests against seeded data; PIT queries verified.

**Phase 6 — SHQL**
Deliverables: `hgai_query_shql` (pattern engine, real expression-grammar parser for `filter:`, anchor resolution per §6.2), `/shql/query` + `/shql/validate`.
Exit: multi-hop pattern queries (node+edge+optional+union) pass; member-anchor resolution regression tests included (this is where v1's subtlest bug lived).

**Phase 7 — Inferencing**
Deliverables: `hgai_inference` (RelationType/axiom model, `expand_edge`, `check_transitive`, materialized closure cache), wired into HQL `flavor: transitive` and SHQL pattern evaluation, `/infer/*` REST routes.
Exit: transitive/symmetric/inverse-of scenarios from §9 pass end-to-end through both query languages, not just unit-tested in isolation (this is the direct fix for defect #5).

**Phase 8 — Retrieval**
Deliverables: `hgai_retrieval` (`EmbeddingProvider` interface + one concrete implementation, Qdrant client, hybrid ranker), embedding worker consuming the event queue from Phase 4, `/search/semantic`, `/search/hybrid`, lexical text-index search.
Exit: write a node → embedding appears in Qdrant asynchronously (poll-with-timeout test) → semantic search returns it; hybrid ranker integration test with a known-similar fixture set.

**Phase 9 — Mesh federation**
Deliverables: `hgai_mesh` (ping, sync scheduler, dot-ref resolution, federated HQL/SHQL fan-out/merge, proxy) — port the v1 design (§2 row 10) faithfully, it worked.
Exit: integration tests with a real second in-process server instance (not just mocks) for at least the ping/sync/federated-query paths; correct async mocking per §13 for any remaining mocked paths.

**Phase 10 — MCP server**
Deliverables: `hgai_mcp`, full tool table from §12, shared auth middleware, CI route/tool-parity check.
Exit: every REST route with a query/search/infer/CRUD counterpart has a passing MCP tool test; parity-check script passes in CI.

**Phase 11 — CLI shell & Web UI**
Deliverables: `hgai_shell` (prompt_toolkit + rich, HQL/SHQL/CRUD commands, `help`), `apps/web-ui` (TS+Vite+Preact+Tailwind: login, org/space/graph management, node/edge CRUD, HQL editor, SHQL editor, accounts admin, mesh admin — feature parity with v1's UI, listed in §2 row as worth keeping functionally).
Exit: manual smoke test of both against a running server (login → create graph → create nodes/edges → run HQL and SHQL query → see results) — this phase is explicitly UI/UX, verify by actually using it, not just unit tests.

**Phase 12 — Observability, docs, CI hardening**
Deliverables: structlog + OpenTelemetry wiring, `/readyz` with real dependency checks, full GitHub Actions pipeline (lint+typecheck+unit+contract+integration on PR, build+push on tag), generated `docs/module-development.md` from the actual `HgaiModule` Protocol (fixes defect #8), `docs/api-reference.md`, `docs/concepts.md`, `docs/hello-world.md` walkthrough.
Exit: CI pipeline green end-to-end on a clean PR; docs reviewed for drift against actual code (spot-check every documented endpoint/tool against the route table).

**Phase 13 — 3D interactive hypergraph visualization *(optional)***
Optional: the platform is complete and usable without this phase (Phase 11 already ships a working 2D UI). Start only after Phase 12's exit criteria pass. Purely additive to `apps/web-ui` — no backend/API changes, it consumes the existing REST surface (§7) and HQL (§6.1) unmodified. This is new functionality, not present in any prior version of this system.

*Rendering mapping (hypergraph → binary-link scene graph):* 3D graph-rendering libraries render binary node-links; hyperedges are N-ary. Map each **Hypernode** to a scene node, and each **Hyperedge** to a scene node too (visually distinct — smaller radius, color/shape keyed by `relation`/`flavor`), with one link per member connecting the hyperedge-node to that member (`seq`-ordered; directional arrow for `hub`/`transitive`/`inverse-transitive` flavors, undirected for `symmetric`/`direct`). This is a direct application of §1's "hyperedges are first-class, referenceable like hypernodes" tenet — no separate hyperedge-rendering model needed.

Deliverables:
- A WebGL 3D force-directed graph component — recommend `3d-force-graph` (Three.js-based, self-hostable via the Vite bundle, no CDN/external service dependency, consistent with this plan's self-hosted-first choices elsewhere, e.g. §3's Qdrant decision) — mounted as a new "Visualize" view in `apps/web-ui` alongside the Phase 11 views.
- Initial scene load: parallel `GET /graphs/{id}/nodes` + `GET /graphs/{id}/edges` (§7, both paginated/filterable) transformed client-side into the library's `{nodes, links}` shape per the mapping above. Bound the default load (e.g. warn/require narrowing via filters above ~2000 combined nodes+edges) rather than attempting to render an unbounded scene.
- **Rotation**: manual orbit via pointer-drag — the library's default Three.js `OrbitControls`, no custom implementation.
- **Auto-rotation**: a toggle enabling continuous slow camera orbit when idle; pauses immediately on user drag, resumes after a short idle timeout (e.g. 3s) after the user releases control.
- **Filtering**: a filter panel using the same query params as the list endpoints (`tags`, `status`, `node_type` for nodes; `relation`, `flavor` for edges — §7); changing filters re-fetches nodes/edges with those params and rebuilds the scene graph server-side, rather than show/hiding over an unbounded client-side dataset.
- **Hypernode double-click focus**: double-clicking a hypernode-typed scene node (not a hyperedge-node) — (1) runs an HQL query (`POST /query`, §7) with `match: { type: hyperedge }, where: { members.node_id: <id> }` (member sub-field filtering, already spec'd in §6.1) to find every hyperedge incident to that node; (2) fetches each with `GET .../{edge_id}?hydrate=1` (§7) to pull full member documents for anything not already in the loaded scene, merging new nodes/links in; (3) animates the camera to center/zoom on the focused node; (4) highlights the focused node plus its one-hop neighborhood (incident hyperedge-nodes and their other members), dimming everything else. A "clear focus" control (button, or double-click on empty space) restores the default full-brightness view/camera.

Exit: manual smoke test (UI/UX phase, verify by using it, same standard as Phase 11) — load a seeded graph; confirm drag-to-rotate and the auto-rotate toggle both work; apply a filter and confirm the scene rebuilds to match; double-click a hypernode and confirm the camera focuses with its neighborhood highlighted and any not-yet-loaded neighbors appear correctly hydrated. Component tests for the filter-params-to-fetch logic and the scene-graph transform function (hypernode/hyperedge/member → nodes/links) in isolation.

---

## 15. Explicitly deferred (not v1 of this rebuild)

- Second storage backend (Postgres/JSONB) — Filter IR is designed to make this possible later; don't build it now.
- Per-artifact `policy` enforcement engine — reserve the field (§8), don't implement enforcement logic yet.
- Kafka/message-bus-based eventing — in-process async queue is sufficient at current scale.
- Learned/ML-based hybrid retrieval ranker — weighted-sum scorer is sufficient for v1.
- Meilisearch or other dedicated lexical engine — Mongo text indexes first; revisit only if relevance proves inadequate.
- Kubernetes manifests/Helm chart — docker-compose is the supported deployment target for v1.
- Provenance manifest signing (C2PA-style) — `provenance` field exists (§5) as freeform data; cryptographic signing is out of scope.

---

## 16. Glossary

- **Hypernode**: entity document (person, system, policy, anything nounlike).
- **Hyperedge**: first-class N-ary relationship between hypernodes (or other hyperedges), with its own attributes.
- **Hypergraph**: a named collection of hypernodes/hyperedges; *instantiated* (owns data) or *logical* (composes others).
- **HQL**: Hypergraph Query Language — Mongo-filter-style, YAML-first.
- **SHQL**: Semantic Hypergraph Query Language — SPARQL-style pattern matching, YAML-first, `?var` bindings.
- **PIT**: point-in-time query, filtered against `valid_from`/`valid_to`.
- **Mesh**: a set of federated HypergraphAI servers queryable via `mesh.server.graph` dot-refs.
- **Flavor**: relationship shape of a hyperedge — `hub`, `symmetric`, `direct`, `transitive`, `inverse-transitive`.
- **Filter IR**: backend-neutral query expression tree that HQL/SHQL compile to; storage backends translate IR to native queries.
- **RelationType/axiom**: declarative data (not code) describing a relation's inference semantics (transitive, symmetric, inverse-of).
