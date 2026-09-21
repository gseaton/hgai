---
title: "HypergraphAI — Architecture Overview for Enterprise, Data and AI-System Architects"
description: "Concepts, architecture, MCP integration, features for humans and agents, use cases and reference architectures for semantic knowledge hypergraphs"
generated: "2026-09-21T04:50:25"
audience: "Enterprise architects, data architects, AI system architects"
status: "Draft — reflects the code and documentation in this repository at the generation date"
---

# HypergraphAI
## A Semantic Knowledge Hypergraph Platform — Architecture Overview

**For enterprise architects · data architects · AI system architects**

*How the platform is built, how AI agents integrate through MCP, and how its features fit enterprise and data architectures.*

**Format:** each `---` is one slide. Open in Marp, reveal-md or any Markdown viewer; diagrams are plain-text.

**Status legend used throughout**

| Mark | Meaning |
|:-:|---|
| ✅ | **Implemented** in this repository (exercised by tests or verified live) |
| 🛠️ | **Pattern** — works today using implemented building blocks; not a packaged feature |
| 🗺️ | **Planned** — not built |
| ⚠️ | **Known limitation / caveat** an architect should design around |

This deck deliberately states limitations next to capabilities: an architecture decision needs both.

---

## Agenda

1. **Why and what** — the architectural problem; semantic knowledge hypergraph concepts; when to choose one
2. **System architecture** — context, containers, modules, layers, request flow
3. **Data architecture** — logical and physical model, identity, tenancy, temporal, provenance
4. **Query, inference and federation architecture**
5. **Security architecture** — including exactly where authorization is (and is not) enforced today
6. **MCP integration architecture** — protocol, tools, sequence, patterns, guardrails
7. **HgNexus** — the integrated AI agent chat
8. **Features for humans and for AI agents**
9. **Use cases as architectures** — store, semantic layer, analytics, agent analytics, chat, transient memory, persistent memory, more
10. **Modeling guidance and patterns** — from a real 5.5M-record build
11. **Reference architectures, NFRs, deployment, adoption path**
12. **Appendix** — tool catalog, configuration, collections, SHQL, glossary

---

# Part 1 — Why and What

---

## 1. The Architectural Problem

Enterprise AI moves from copilots to **agents** that read, reason and write across systems. Architects now need a knowledge tier that is:

| Requirement | Why the usual stores fall short |
|---|---|
| **Structured and semantic** | Vector indexes retrieve by similarity, not meaning; tables hide relationships in joins |
| **N-ary faithful** | Real events (a contract, an incident, a transaction with account/card/device/merchant) involve *many* parties at once; binary edges force artificial nodes |
| **Explainable** | "Why did the agent conclude that?" needs provenance and a visible line between stored and *inferred* facts |
| **Temporal** | "What was true on 1 March?" is a first-class question in audit and compliance |
| **Vendor-neutral memory** | Context should outlive any one model, chat product or session |
| **Governable** | Multi-tenant, auditable, self-hostable |
| **Agent-native** | A standard tool interface (MCP) instead of bespoke connectors per model |

HypergraphAI is one system aimed at that whole set. This deck shows how it is built and where it stops.

---

## 2. Concepts — Hypergraph, Semantic, Temporal, Provenance

```
  Binary graph                              Hypergraph
  ──────────────                            ─────────────────────────────────────
  A ─▶ Contract ◀─ B                        ┌ hyperedge  rel:signed-contract ─────┐
  C ─▶ Contract ─▶ Delaware                 │ members: A · B · C · Delaware       │
  (4 edges + 1 synthetic node,              │ attributes: {value, date}           │
   facts scattered)                         │ valid_from/to · provenance · tags   │
                                            └─────────────────────────────────────┘
```

- **Hypernode** = entity · **Hyperedge** = n-ary relationship, a first-class object with its own data (and can be a member of another hyperedge) ✅
- **Flavors:** `hub` (first member is the focal node; each other member is an independent *(hub, spoke)* fact) and `symmetric` (all members mutually equivalent) ✅
- **Semantic:** relation semantics are data — *axiom hyperedges* over relation-type nodes: `owl:inverse-of`, `owl:symmetric`, `owl:transitive`, `skos:broaderTransitive`, `skos:narrowerTransitive` ✅
- **Temporal:** `valid_from` / `valid_to` on every node and edge; queries take `at:` ✅
- **Provenance:** per-record audit trail (who/when/which fields) plus a `provenance` convention for source lineage ✅

---

## 3. Choosing the Right Store — Decision Matrix

| Question | Relational | Property graph | RDF / triple store | Vector DB | **Semantic hypergraph (HypergraphAI)** |
|---|---|---|---|---|---|
| Model an n-ary fact as *one* fact | Join tables | Reify into a node | Reify | — | **Native hyperedge** |
| Relationship carries its own data + validity | Extra columns | Edge properties | Reification | — | **Native (attributes, validity window, audit)** |
| Rules as data (inverse/symmetric/transitive/broader) | Views/code | Plugins/code | **Yes (OWL/RDFS)** | — | **Yes (axiom hyperedges)** |
| "As of" queries | Bitemporal patterns | Manual | Manual | — | **Built-in `at:`** |
| Fuzzy "similar to" retrieval | — | — | — | **Yes** | ⚠️ Not native (pair with a vector store) |
| Extreme-scale, sharded OLTP/analytics | **Yes** | **Yes** | Varies | **Yes** | ⚠️ Envelope below; single MongoDB backend |
| Agent tool interface out of the box | — | Varies | Varies | Varies | **MCP server (30 tools)** |

**Rule of thumb:** choose it when the value is in *relationships with meaning, time and provenance* that must be shared by people **and** agents; keep relational stores for transactions, vector stores for similarity — and connect them.

---

## 4. Benefits in the AI Era — for Architects

| Benefit | Mechanism | Architectural effect |
|---|---|---|
| **Grounded retrieval** | Typed pattern queries (SHQL) return exact facts | Agent answers cite structure, not similarity |
| **Explainable derivation** | Inferred edges carry `_inferred`, `_source_edge`, `_axiom` | Auditable reasoning trail |
| **Lossless modeling** | n-ary hyperedges | Fewer artificial entities; simpler mappings from source systems |
| **Temporal correctness** | Validity windows + `at:` | Historical reproducibility |
| **Decoupled memory** | Knowledge lives in *your* store, reachable by any MCP/REST client | No lock-in to a model or chat product |
| **Governed sharing** | Spaces, note scopes, audit trail | Tenant isolation and traceability (see security caveats) |
| **Federation without ETL** | Mesh queries fan out across servers | Domain-owned graphs, enterprise-wide queries |
| **Evolvable semantics** | Ontology and rules are data | New rules without code deployments |

---

# Part 2 — System Architecture

---

## 5. System Context (C4 Level 1)

```
   ┌────────────┐  ┌──────────────┐  ┌─────────────────────┐  ┌──────────────┐
   │ Analysts / │  │ Data stewards │  │ AI agents & tools    │  │ Applications │
   │ business   │  │ / admins      │  │ (Claude, GPT, Grok,  │  │ / pipelines  │
   │ users      │  │               │  │  Cursor, orchestrators)│ │              │
   └─────┬──────┘  └──────┬───────┘  └──────────┬──────────┘  └──────┬───────┘
     Web UI / HgNexus   Web UI / hgsh          MCP (HTTP)         REST / files
         └────────────────┴──────────┬──────────┴─────────────────────┘
                                     ▼
                       ┌───────────────────────────────┐        ┌──────────────────┐
                       │        HypergraphAI            │◀──────▶│  Other HypergraphAI│
                       │  semantic hypergraph platform  │ mesh    │  servers (mesh)   │
                       └───────┬───────────────┬────────┘        └──────────────────┘
                               │               │ HTTPS (BYO keys)
                      ┌────────▼──────┐   ┌────▼─────────────────────────┐
                      │ MongoDB 7+     │   │ AI vendor APIs (Anthropic,    │
                      │ (+ S3 optional)│   │ OpenAI, xAI) — HgNexus only   │
                      └───────────────┘   └──────────────────────────────┘
```

External dependencies: **MongoDB** (required), **S3-compatible object store** (optional, media blobs), **AI vendor APIs** (only when HgNexus is used). No message bus, cache server or search cluster is required.

---

## 6. Container View (C4 Level 2)

```
┌─────────────────────────────── one FastAPI/uvicorn process ────────────────────────────┐
│  /ui       static single-page Web UI (vanilla JS + Bootstrap, no build step)             │
│  /api/v1   REST routers: auth · graphs · nodes · edges · accounts · spaces · media ·     │
│            inference · notes · parameterized-queries · help                              │
│  /api/v1   module routers: shql · meshes · agent (HgNexus)                               │
│  /mcp/     MCP streamable-HTTP app (FastMCP, stateless) + auth middleware               │
│  /health   /api/docs (OpenAPI)   /api/v1/server/info                                     │
│  ───────────────────────────────── core engine ───────────────────────────────────────  │
│  engine (CRUD, hyperkeys, audit) · inference · space/auth · notes · help · cache · transfer│
│  ───────────────────────────── storage abstraction ───────────────────────────────────  │
│  StorageBackend ABC → 10 store interfaces → MongoDB backend (Motor async driver)         │
└───────────────────────────────────────┬─────────────────────────────────────────────────┘
                                        ▼
                      MongoDB (collections) · GridFS (default) or S3 (media bytes)
```

- **One deployable**, stateless API tier (state is in MongoDB) ✅
- Modules mount at startup; **a module that fails to import logs a warning and is skipped** — the core keeps running ✅
- Default server is a single uvicorn process; scale out by running more instances behind a load balancer (🛠️, shared MongoDB; not load-tested)

---

## 7. Module Architecture and Extension Contract

| Module | Responsibility | Interface |
|---|---|---|
| `hgai` (core) | Models, engine, auth, inference, notes, help, cache, transfer, REST routers | FastAPI routers |
| `hgai_module_storage` | Storage **abstraction**: `StorageBackend`, 10 per-entity store ABCs, typed filters, registry | Python ABCs |
| `hgai_module_storage_mongodb` | The MongoDB implementation (indexes, GridFS/S3 media) | registered as `mongodb` |
| `hgai_module_shql` | SHQL parser, validator, execution engine, history | router `/shql` |
| `hgai_module_mesh` | Server registry, federation, dot-notation, background sync | router `/meshes` |
| `hgai_module_mcp` | MCP server: 30 tools + auth middleware | ASGI app `/mcp` |
| `hgai_module_agentchat` | HgNexus: vendors/models, sessions, engine, toolkits | router `/agent` |

**Contract** (`docs/module-development.md`): a package `hgai_module_<name>` exposing a class with `name/version/description` and `get_router()` (REST) or `get_app()` (mounted ASGI app); module-owned MongoDB collections are allowed; registered in `hgai/main.py`. ✅

**Architectural consequence:** connectors, ontology packs, storage backends and UI additions can be delivered as modules without forking the core. 🗺️ Packaging/distribution (a marketplace) is not built.

---

## 8. Storage Abstraction

All persistence goes through `get_storage()`; nothing outside the storage modules imports MongoDB/Motor. ✅

```
StorageBackend
 ├─ hypergraphs   HypergraphStore        ├─ notes                NoteStore
 ├─ hypernodes    HypernodeStore         ├─ parameterized_queries ParameterizedQueryStore
 ├─ hyperedges    HyperedgeStore         ├─ media                MediaStore
 ├─ accounts      AccountStore           ├─ meshes               MeshStore
 ├─ spaces        SpaceStore             └─ cache                CacheStore
 └─ connect() · close() · ensure_schema()   (typed filter & patch dataclasses)
```

| Property | Detail |
|---|---|
| Selection | `HGAI_STORAGE_BACKEND` (default `mongodb`); custom backends call `register_backend(name, cls)` |
| Media bytes | `HGAI_MEDIA_BACKEND=gridfs` (default, in MongoDB) or `s3` (AWS S3 / MinIO-compatible) ✅ |
| Module-owned data | Some modules (agent chat, SHQL history) own plain collections directly rather than extending the ABC |
| ⚠️ Reality | MongoDB is the **only** implemented backend; the interface enables others, it does not provide them |

---

## 9. Request Flow (REST)

```
Client ──HTTPS──▶ FastAPI
                    │ 1. CORS middleware            (default allow-all; configure for production)
                    │ 2. Dependency: get_current_account
                    │      Bearer token → API-key fast path (synthetic admin)  or  JWT → account lookup
                    │ 3. Dependency: require_graph_access(op) / require_space_role / require_admin
                    │      (the authorization gate — see Security Architecture for coverage)
                    │ 4. Router → core engine (validation via Pydantic models)
                    │ 5. Engine → storage store (async Motor)
                    │ 6. Side effects: hyperkey/de-dup, audit-trail entry, graph counters,
                    │                  media ref-counts, graph-scoped cache invalidation
                    ▼
                 JSON response (paginated lists: {total, skip, limit, items})
```

Design points: async end-to-end; Pydantic models at every boundary; deterministic **SHA-256 hyperkey** prevents duplicate hyperedges at the database level; list endpoints support `skip/limit/sort/search/tags`.

---

# Part 3 — Data Architecture

---

## 10. Logical Data Model

```
Mesh ──has──▶ MeshServer (url, token, known graphs)
Space (tenant) ──owns──▶ Hypergraph ──contains──▶ Hypernode
   │ members(owner/admin/member/viewer)      │ instantiated | logical (composition of graphs)
   ▼                                          └──────────▶ Hyperedge ──members──▶ Hypernode | Hyperedge
Account (roles, permissions)                                (relation, flavor, seq-ordered members, attributes, validity)
Note · ParameterizedQuery · Media · AgentVendor/Model/ChatSession  (outside the hypergraph model)
```

| Entity | Key fields |
|---|---|
| Hypernode | `id`, `label`, `type`, `description`, `attributes` (free-form JSON), `tags`, `status` (active/draft/archived), `valid_from/to`, `media[]`, `mutations[]` |
| Hyperedge | `id`, `relation`, `flavor`, `members[{node_id, seq}]`, `attributes`, `tags`, `status`, `valid_from/to`, `relation_node_id`, `hyperkey`, `mutations[]` |
| Hypergraph | `id`, `label`, `type` (instantiated/logical), `space_id`, `composition[]`, `node_count`, `edge_count`, `attributes` |

**Schema stance:** *schema-on-write is optional.* Structure lives in the data: relation-type nodes, class nodes, concept schemes and axiom hyperedges (an ontology you can query and change at runtime). ✅

---

## 11. Physical Data Model (MongoDB)

| Collection | Notes |
|---|---|
| `hypergraphs`, `hypernodes`, `hyperedges` | Core; nodes/edges carry `hypergraph_id` (composite `space/graph` for tenant graphs) |
| `accounts`, `spaces`, `meshes` | Identity, tenancy, federation registry |
| `notes`, `parameterized_queries`, `media` (+GridFS) | Knowledge work products and files |
| `query_cache` | TTL-indexed result cache with `graph_ids[]` for scoped invalidation |
| `audit_log`, `shql_query_history` | Operational records |
| `agent_vendors`, `agent_models`, `agent_chat_sessions`, `agent_chat_messages`, prompt history, `agentchat_agno_*` | HgNexus (module-owned) |

**Indexes created at startup (idempotent) ✅** — e.g. nodes: unique `(id, hypergraph_id)`, `(hypergraph_id, status)`, `(hypergraph_id, type)`, `tags`, sparse PIT `(hypergraph_id, valid_from, valid_to)`; edges: unique `(id, graph)`, unique **`(hyperkey, graph)`**, `(graph, relation)`, multikey `members.node_id`, PIT; cache: unique key, `graph_ids`, TTL on `expires_at`.

**Identity rules:** ids are unique *within* a hypergraph; hypergraph, mesh and server ids must not contain `.` (reserved for mesh dot-notation); node ids commonly use `type:name` (colon) conventions. Edge members may name nodes **or other edges**.

---

## 12. Time, Provenance and Lifecycle

| Concern | Mechanism | Notes |
|---|---|---|
| Validity | `valid_from` / `valid_to` on nodes and edges | `at:` in SHQL; Visualize filters edges by instant |
| Change history | `mutations[]` per record: `{ts, by, mutation, delta[]}` | No-op or repeated changes are not recorded |
| Source lineage | `attributes.provenance` (convention) | Proven at 5.5M records: source file, CSV line/range, method, run id |
| Lifecycle | `status`: active / draft / archived | Draft as a staging state for agent-proposed facts (🛠️) |
| De-duplication | SHA-256 **hyperkey** = relation + sorted members + graph + validity | Same relation and member set = same hyperedge; merge such facts into one edge with a list property |
| Counters | `node_count` / `edge_count` on the graph | Maintained by the engine on writes |

⚠️ Writes through the **MCP** tools stamp the audit trail with a generic actor (`mcp-agent`); record the real agent identity in `provenance`.

---

# Part 4 — Query, Inference, Federation

---

## 13. SHQL Query Architecture

```
SHQL text (YAML) ──parse_shql──▶ dict ──validate_shql──▶ errors[]
      │
      └─ execute_shql
           1. cache lookup (key = MD5 of query text; TTL) ──hit──▶ result
           2. resolve `from:` → local graphs · logical graphs (expand composition) ·
              dot-notation mesh refs · bare mesh id (federated fan-out)
           3. evaluate `where:` patterns in order over BINDING SETS
                node/edge patterns (Mongo filters + member matching) · filter · optional · union
                shared ?variable = implicit join · `at:` PIT · `infer: true` expansion
           4. project `select` · distinct · aggregate · order_by · offset/limit (default 500)
           5. store in cache (graph-scoped invalidation on writes)
```

| Capability | Status |
|---|---|
| Patterns, joins, OPTIONAL, UNION, FILTER expressions, MongoDB operators in `attributes:` | ✅ |
| Aggregate `count`/`group_by`, multi-key `order_by`, `distinct` | ✅ |
| Parameterized templates (`/$name:type:default$/`) | ✅ |
| ⚠️ Candidate fetch per pattern is bounded (2,000 documents) and results default to 500 rows | design queries to be selective |
| ⚠️ Member patterns bind ids only; constrain a member's own properties with a join to a `node:` pattern | see cheat sheet |

---

## 14. A Query, a Result, and Its Cost

A selective attribute query over a 3.6M-node graph (the generated fraud graph — synthetic data):

```yaml
shql:
  from: alchemy-cyber-fraud-generated-20260920190053
  where:
    - node:
        bind: ?txn
        type: Transaction
        tags: [fraud-detection]
        attributes:
          ip_risk_score: { $gte: 70 }
          velocity_1h: { $gte: 4 }
          amount_vs_avg_ratio: { $gte: 3 }
  select:
    - ?txn.id
    - ?txn.attributes.ip_risk_score
    - ?txn.attributes.amount
  order_by:
    - ?txn.attributes.ip_risk_score desc
  limit: 20
```

**Measured:** 20 rows in ≈ 5 s (attribute predicates scan the 1M-transaction subset selected by `type` + `tags` indexes). A ring-membership lookup on the same graph (`node_id` member index) returned in ≈ 10 ms.

**Architectural guidance:** put selective, *indexed* predicates first (type, tags, ids, member ids); treat unindexed attribute predicates as scans; add an index or promote a hot property to a tag or relation if a scan pattern becomes a workload.

---

## 15. Inference Architecture

Rules are ordinary hyperedges over relation-type nodes; the engine reads them at query time. ✅

| Axiom hyperedge | Effect |
|---|---|
| `owl:inverse-of [R, R′]` | Each (hub, spoke) fact of R implies R′(spoke, hub) |
| `owl:symmetric [R]` | R holds both directions |
| `owl:transitive [R]` | Whole-relation reachability; synthesizes non-adjacent pairs |
| `skos:broaderTransitive [narrow, broad]` / `narrowerTransitive [broad, narrow]` | Superproperty projection through a multi-hop relation hierarchy |

- Expansion runs to a **fixed point** (bounded by `max_iterations`), de-duplicating by atomic (relation, subject, object) facts, so cyclic axiom graphs terminate.
- Every inferred edge carries `_inferred`, `_source_edge`, `_axiom` (and `_transitive_path` for transitive results).
- **Three access paths:** SHQL `infer: true` · REST/MCP *expand one edge* (`/infer/expand`, `hgai_infer_expand_edge`) · REST/MCP *reachability* (`/infer/transitive`, `hgai_infer_check_transitive`: bool / closure / path).
- **Materialization:** *Project Inference* writes derived facts back as ordinary hyperedges (preview first) — the way to make inference results indexable and cheap to query.

⚠️ **Scale:** SHQL `infer: true` starts from a bounded candidate set and expands it; on a 187k-hyperedge test graph a whole-graph inference query did not complete in several minutes. For large graphs use the two targeted endpoints, or materialize.

---

## 16. Federation Architecture (Mesh)

```
                      SHQL: from: my-mesh   or   my-mesh.server-b.space.graph
                                       │
                          ┌────────────▼────────────┐
                          │  Local server (hub)      │  local graphs answered by direct engine call
                          └───┬──────────┬──────────┘
                    HTTPS +   │          │  asyncio.gather (concurrent) — total time ≈ slowest server
                    api_token ▼          ▼
                       Server B        Server C   …  (unreachable servers skipped, reported in `errors`)
```

| Aspect | Detail |
|---|---|
| Registry | Mesh = list of servers (`server_id`, url, `api_token`, known graphs); admin-only CRUD |
| Addressing | `mesh.server.graph`, `mesh.server.space.graph`, `mesh.*.graph`, `mesh.server.*` |
| Transport | One pooled `httpx.AsyncClient` (100 connections, 20 keep-alive, 10 s timeout) |
| Freshness | Background sync of each mesh's graph list (`HGAI_MESH_SYNC_INTERVAL_SECONDS`, default 300 s; 0 = off) |
| Failure model | Partial results with per-server errors — never all-or-nothing |
| ✅ / ⚠️ | ✅ implemented. ⚠️ Trust = a stored token per remote (treat as a credential); no cross-server query planning or pushdown beyond forwarding the query |

---

# Part 5 — Security Architecture

---

## 17. Authentication and Secrets

| Mechanism | Detail | Status |
|---|---|---|
| **JWT** (HS256, default 8 h) | Password login → bearer token for people and the UI | ✅ |
| **API keys** | `HGAI_PRIMARY_API_KEY` / `HGAI_SECONDARY_API_KEY`; bearer value; **maps to a synthetic full-admin account**; two keys allow rotation without downtime | ✅ |
| Accounts | Roles `admin`, `user`, `agent`, `readonly` + `permissions.graphs` / `operations` | ✅ |
| Vendor API keys (HgNexus) | Fernet-encrypted at rest, key derived from `HGAI_SECRET_KEY`; admin-only management | ✅ |
| Agent web access | SSRF-guarded fetch (private/internal addresses refused) | ✅ |
| Federation credentials | Per-server `api_token` in the mesh registry | ✅ (stored as configured) |
| SSO / SAML / OIDC, per-agent tokens, key scoping | — | 🗺️ |

**Hardening checklist:** set a strong `HGAI_SECRET_KEY`; change the default admin password (`pwd357`); restrict `HGAI_CORS_ORIGINS` (default `*`); terminate TLS in front; do not publish MongoDB's port; use a secrets manager for API keys.

---

## 18. Authorization — Exactly What Is Enforced Where ⚠️

Authorization uses global roles, per-graph permissions and **space membership** (for space-owned graphs membership is the *sole* gate; a `*` permission cannot cross tenants). **Coverage today:**

| Surface | AuthN | Per-graph / per-space AuthZ |
|---|:-:|:-:|
| REST: graphs, nodes, edges (incl. space-scoped) | ✅ | ✅ |
| REST: export / import, inference (expand, transitive, project) | ✅ | ✅ |
| REST: spaces, accounts, meshes, agent vendors/models | ✅ | ✅ (role checks: space role / admin) |
| REST: Notes, chat sessions, prompt & query history | ✅ | ✅ (owner / note scope / grants) |
| Help topics (note-backed) | ✅ | ✅ (note visibility) |
| **REST: `POST /shql/query`** | ✅ | ⚠️ **not checked** |
| **MCP endpoint — all 30 tools** | ✅ | ⚠️ **not checked** |

⚠️ **Verified behaviour:** an account with role `readonly` and *no* permissions gets `403` on `GET /graphs/{id}/nodes` but can read every graph through SHQL, and can list, read **and create** nodes through MCP. An API key is a full-admin credential by design. **HgNexus's MCP tools therefore also run unscoped** for any signed-in user.

**Design around it today:** isolate `/mcp/` (network policy or gateway), treat all MCP/SHQL-capable credentials as privileged, give sensitive data its own server and mesh only what should be shared, restrict HgNexus to trusted accounts.
**Planned fix (🗺️, small and well-bounded):** resolve the caller's identity in the MCP middleware and the SHQL router and apply `can_access_graph` / `can_perform` before each engine call.

---

## 19. Multi-Tenancy and Data Governance Options

| Need | Mechanism | Notes |
|---|---|---|
| Tenant isolation | **Spaces** (owner/admin/member/viewer) with space-scoped graph ids (`space/graph`) | Same graph id may exist in two spaces; enforced on REST |
| Domain ownership | One hypergraph (or space) per domain team; mesh for cross-domain queries | Data-mesh style |
| Environment separation | Separate servers/databases (`--server-id`, `--mongo-db`) | Strongest isolation; also the workaround for the MCP/SHQL gap |
| Content sharing | Notes: `private`, `protected`, `protected-edit`, `public`, `public-edit` + per-account viewer/editor grants | Owner/admin control scope and shares |
| Change control | `status: draft` staging; `mutations[]` review; PIT to reconstruct | Convention-based (🛠️) |
| Retention / erasure | Delete records and graphs; MongoDB TTL for cache | No built-in legal-hold or retention engine |
| Audit | Per-record `mutations[]`, `audit_log` collection, provenance convention | ⚠️ MCP writes are stamped `mcp-agent` |

---

# Part 6 — MCP Integration Architecture

---

## 20. What MCP Is, and Why It Matters Architecturally

**Model Context Protocol (MCP):** an open standard for connecting AI models to tools and data — JSON-RPC 2.0 messages (`initialize`, `tools/list`, `tools/call`) over a transport (here **streamable HTTP**). Stewardship moved to the Linux Foundation's Agentic AI Foundation in Dec 2025; major model vendors and IDE/agent hosts support it.

| Architectural value | Consequence |
|---|---|
| **N×M → N+M integration** | One MCP server, many model clients — no per-vendor connector |
| **Typed tool contracts** | Tool name + JSON-schema arguments; agents can discover capabilities at runtime |
| **Transport-simple** | HTTP + bearer token fits existing gateways, proxies and observability |
| **Vendor-neutral** | The knowledge tier can outlive any single model choice |

**In HypergraphAI, MCP is the agent-facing façade over the same engine that serves REST and the UI** — one source of truth, not a parallel data path. ✅

---

## 21. How HypergraphAI Implements MCP

| Aspect | Implementation |
|---|---|
| Server | Python MCP SDK (`FastMCP`), name `hgai`, mounted as an ASGI app at **`/mcp/`** |
| Transport | **Streamable HTTP**, `stateless_http=True` — each request stands alone (no server-side session state), which suits load balancers and horizontal scale-out |
| Framing | JSON-RPC over POST; responses as `event: message` SSE frames or JSON; clients send `Accept: application/json, text/event-stream` |
| Authentication | ASGI middleware: `Authorization: Bearer <API key or JWT>`; missing/invalid → **401** before reaching a tool |
| Tool results | Text content (usually JSON); **errors are returned as tool output** (HTTP 200) so the model can read and recover |
| Tool surface | **30 tools** — hypergraph (4), hypernode (5), hyperedge (4), query (2), inference (2), mesh (5), media (3), space (5) |
| Discovery | `tools/list` returns names, descriptions and JSON-schema inputs; the server also ships usage `instructions` |
| Audit stamp | Writes recorded as actor `mcp-agent` |
| ⚠️ Authorization | Authentication only — see *Authorization — Exactly What Is Enforced Where* |

Client configuration is one JSON block:

```json
{ "mcpServers": { "hgai": { "url": "http://localhost:8357/mcp/",
    "headers": { "Authorization": "Bearer <api-key-or-token>" } } } }
```

---

## 22. MCP Sequence — Discover, Query, Reason, Write Back

```
Agent host (Claude / GPT / IDE / orchestrator)            HypergraphAI  /mcp/          Engine · MongoDB
   │  POST initialize                                            │
   │────────────────────────────────────────────────────────────▶│  auth middleware (Bearer)
   │  POST tools/list                                            │
   │────────────────────────────────────────────────────────────▶│  → 30 tool schemas
   │                                                             │
   │  tools/call hgai_hypergraph_list {status:"active"}          │
   │────────────────────────────────────────────────────────────▶│──▶ engine.list_hypergraphs ──▶ DB
   │◀──── text(JSON: graphs, counts) ────────────────────────────│
   │  tools/call hgai_query_validate {query_yaml}                │
   │────────────────────────────────────────────────────────────▶│  parse + validate (no execution)
   │◀──── {valid:true} ──────────────────────────────────────────│
   │  tools/call hgai_query_execute  {query_yaml, use_cache}     │
   │────────────────────────────────────────────────────────────▶│──▶ SHQL engine ──▶ DB / cache
   │◀──── text(JSON: rows, meta) ────────────────────────────────│
   │  tools/call hgai_infer_expand_edge {graph_id, edge_id}      │  ← "what follows from this fact?"
   │  tools/call hgai_hyperedge_create {… attributes_json:{provenance}}   ← write back a finding
   │  tools/call hgai_hyperedge_get {…}                          │  ← read-back verification
```

**Agent loop that works well:** *discover schema → validate query → execute → inspect `_inferred` → write a finding as a `draft` hyperedge with `provenance` → verify.*

---

## 23. MCP Tool Catalog by Risk Tier

| Tier | Tools | Effect | Suggested gateway policy |
|---|---|---|---|
| **Read** | `hypergraph_list/get/stats`, `hypernode_list/get`, `hyperedge_list/get`, `query_execute`*, `query_validate`, `infer_expand_edge`, `infer_check_transitive`, `mesh_list/get`, `media_download`, `space_list/get/list_graphs` | None (`query_execute` reads only) | Allow broadly to trusted agents |
| **Write (data)** | `hypernode_create/update`, `hyperedge_create`, `media_upload` | Creates/changes knowledge | Allow to designated agents; require `draft` + `provenance` convention |
| **Destructive** | `hypernode_delete`, `hyperedge_delete`, `media_delete` | Deletes records | Human-in-the-loop or deny |
| **Structure / admin** | `hypergraph_create`, `space_create`, `space_add_member` | Creates containers, changes membership | Deny to agents by default |
| **Federation** | `mesh_ping/sync/query` | Outbound calls to other servers | Allow read-only; restrict `sync` |

⚠️ Because authorization is not enforced inside the tools today, **this policy must be applied in front of the endpoint** (an API gateway or MCP proxy with per-tool allow-lists), or by running agents against a dedicated read-only server. 🗺️ Server-side per-caller tool and graph scoping.

---

## 24. Agent Integration Patterns

| # | Pattern | How it connects | Notes |
|---|---|---|---|
| 1 | **Desktop / IDE agent** (Claude Desktop, Cursor, VS Code) | Client config → `/mcp/` with a bearer key | Fastest pilot; treat the key as admin |
| 2 | **In-product agent (HgNexus)** | In-process per-turn agent; MCP client to the same server + help + web tools | Users need no config; admin picks vendors/models |
| 3 | **Orchestrated multi-agent** (LangGraph, Agno, custom) | Any MCP client library over streamable HTTP | Shared graph = shared blackboard |
| 4 | **Service / batch agents** | REST or MCP with API key from a secrets manager | Prefer REST for bulk (`import`, paging) |
| 5 | **Federated agent** | `hgai_mesh_query` or dot-notation in `query_execute` | One call spans domain servers |
| 6 | **GraphRAG hybrid** 🛠️ | Vector store finds candidate entities → agent expands them in the hypergraph via SHQL | HypergraphAI has no vector index; keep entity ids as the join key |

```
  User ─▶ Orchestrator ─▶ LLM ─┬─ MCP tools ─▶ HypergraphAI  (structure, time, provenance)
                                └─ retrieval ─▶ Vector store   (similarity)   ← optional
```

---

## 25. Agent Guardrail Architecture

**Controls available today**

| Control | How |
|---|---|
| Endpoint authentication | Bearer key/JWT at the MCP middleware |
| Least privilege by *topology* | Dedicated server/DB per sensitivity tier; expose read-only data via mesh |
| Safe writes | Convention: `status: draft`, `tags: [proposed-by-agent]`, `attributes.provenance = {agent, run, source, confidence}` |
| Reviewability | `mutations[]` on every record; PIT queries to see state before/after |
| Query safety | `hgai_query_validate` before execute; SHQL result limits; cache |
| Vendor-key protection | Encrypted at rest; never returned to non-admins |
| SSRF protection | Web-fetch tool refuses private/internal addresses |

**Recommended additions outside the platform:** an MCP gateway with per-tool allow-lists and rate limits, request logging with the caller's identity, and periodic review of `mcp-agent`-stamped changes.

**Platform roadmap 🗺️:** per-caller authorization in MCP/SHQL; per-agent identity stamping; per-key scopes; usage metering; approval workflow for draft → active.

---

# Part 7 — HgNexus: Integrated AI Agent Chat

---

## 26. HgNexus Architecture

**HgNexus** is the platform's built-in agent chat (module `hgai_module_agentchat`, UI panel beside every screen). ✅

```
Browser panel ──SSE──▶ /api/v1/agent/sessions/{id}/messages (stream)
                          │
                          ▼  per turn
                  build_agent(vendor, model, account)
                    ├─ model:   Claude | OpenAI | xAI   (BYO key, decrypted server-side)
                    ├─ tools:   • MCP toolkit  → this server's /mcp/  (in-house streamable-HTTP client)
                    │           • Help toolkit → in-process, account-aware (help_search / help_get)
                    │           • Web toolkit  → SSRF-guarded web_fetch
                    ├─ memory:  Agno + MongoDB (agentchat_agno_* ) — last 10 runs replayed to the model
                    └─ instructions: use help tools for platform questions; hgai_* for data
                          │ events (RunContent / RunCompleted)  ▼
              audit records: agent_chat_messages (vendor, model, timing, tokens)
```

| Aspect | Detail |
|---|---|
| Catalog | Admin-managed vendors and models; small seeded default catalog (disabled, no keys) |
| Sessions | Owner-only; persisted; restartable; **pinned to one model** ⚠️ |
| History | Last 50 prompts per account, server-side |
| Export | "Save as Note": Markdown + YAML front matter (prompt, vendor/model, times, duration, tokens) |
| Isolation of the MCP client | Purpose-built client avoids a dependency conflict with the server's pinned MCP SDK |
| ⚠️ | The MCP tools inside a turn are **not** permission-scoped to the user (see Security) |

---

## 27. HgNexus — Roles of Each Actor

| Actor | Does |
|---|---|
| **Admin** | Adds vendors/models, sets API keys (encrypted), enables models; controls who may use the panel |
| **Analyst / user** | Chats about data and about the platform; saves answers as Notes; reuses prompt history |
| **The agent (LLM)** | Calls `help_search`/`help_get` for platform questions, `hgai_*` tools for data, `web_fetch` for a given URL; cites help-topic ids |
| **Platform** | Builds a fresh agent per turn, streams tokens, records vendor/model/tokens/timing, stores the session |

**Architectural notes**

- Model choice is per **session**, not per turn; vendor keys are BYO (no token resale).
- Sessions and history live in *your* MongoDB — portable across vendors; transcripts are not replayed between different models (🗺️ session hand-off).
- Answers exported to Notes carry an audit header, making agent output reviewable like any other document.

---

# Part 8 — Features for Humans and AI Agents

---

## 28. Feature Map

Every capability is reachable by both audiences. ✅

| Capability | Human surface | Agent surface |
|---|---|---|
| Knowledge CRUD (graphs, nodes, edges) | Web UI tables/forms, `hgsh` shell | `hgai_hypergraph_*`, `hgai_hypernode_*`, `hgai_hyperedge_*` |
| Query (SHQL) | Editor, examples, history, validate, cache toggle | `hgai_query_validate`, `hgai_query_execute` |
| Reusable queries | Parameterized Queries screen (typed placeholders) | Same SHQL, parameters rendered by the client |
| Inference | "Show inferred edges", **Project Inference** (preview → materialize) | `hgai_infer_expand_edge`, `hgai_infer_check_transitive`, `infer: true` |
| Time | `at:` in queries, Visualize instant filter | `at:` in SHQL |
| Federation | Meshes admin screen | `hgai_mesh_*`, dot-notation |
| Tenancy | Spaces, Accounts admin | Space tools; REST authorization |
| Media | Upload, attach, embed | `hgai_media_*` |
| Notes & Help | Markdown notes, folders, scopes; 40-topic Help | Help search tool; chat export to Notes |
| Visualization | 3D interactive graph | — |
| Data movement | Export/Import (Hypergraphs screen), seeds | REST `graphs/import`, `graphs/{id}/export` |
| AI chat | HgNexus panel | (HgNexus *is* an MCP-using agent) |

---

## 29. Human Interfaces

| Interface | Best for | Notes |
|---|---|---|
| **Web UI** (`/ui/`) | Stewards, analysts, admins | Dashboard; graph/node/edge CRUD; **Visualize** (3D, PIT slider, inferred edges); SHQL editor; Notes; Help; Project Inference; Media; admin: AI Agent, Spaces, Accounts, Meshes, System |
| **hgsh shell** | Engineers, scripts | connect/use/ls/get/create/update/delete, `shql`, `import -f`, `export -o` |
| **REST + OpenAPI** | Applications, pipelines | `/api/docs`; pagination, sort, search, tags |
| **Files** | Portability | One-file hypergraph export/import (YAML/JSON), seed files, generator pattern |

The UI is served by the same process (no separate front-end deployment); it calls the same REST API any client can.

---

# Part 9 — Use Cases as Architectures

---

## 30. Use Case 1 — Enterprise Semantic Knowledge Hypergraph Store

**Role:** system of record for meaning: entities, n-ary relationships, ontology, history and provenance.

```
 Domain teams ──curate──▶ [ Space: finance ]  [ Space: risk ]  [ Space: ops ]   (graphs per domain)
 Source systems ─import──▶      │  ontology-as-data (types · relations · axioms · concept schemes)
 Agents ─MCP (draft+provenance)─▶ status: draft ──review──▶ active
                                 │
                       consumers: analysts · agents · apps (REST) · other servers (mesh)
```

| Design decision | Guidance |
|---|---|
| Graph granularity | One hypergraph per bounded domain/data product; shared ontology as its own graph referenced by convention |
| Ontology | Class, relation-type and concept-scheme nodes plus axiom hyperedges — versioned via the audit trail |
| Change control | Agent/ETL writes land as `draft`; stewards promote; `at:` reproduces past states |
| Multi-tenancy | Spaces on REST; for stricter isolation, separate servers (see Security) |
| Portability / DR | `mongodump`; per-graph export files (⚠️ export is built in memory — use it for modest graphs; bulk-copy very large graphs at the database level) |

---

## 31. Use Case 2 — Enterprise Semantic Layer Across Systems

**Idea:** one shared vocabulary and relationship model over data that stays in its systems of record.

```
 CRM ─┐                        ┌─ ontology graph (classes · relations · SKOS schemes · axioms)
 ERP ─┼─ mapping/ingest ──────▶│─ entity + relationship graphs per domain (with provenance)
 Logs ┤  (scripts, import      │
 Files┘   files, REST)         └─ mesh ─▶ federated queries across domain servers
                                            ▲                ▲              ▲
                                       BI/analysts     agents (MCP)     apps (REST)
```

| Concern | Approach |
|---|---|
| Ingestion | ✅ REST/`import` files; ✅ generator pattern (below); 🗺️ packaged connectors |
| Entity alignment | Distinct nodes per source + `skos:exactMatch` / `closeMatch` hyperedges (symmetric, transitive) |
| Source lineage | `attributes.provenance` on every record: `{dataset, source_file, source_row, method, run_id}` |
| Query across domains | Mesh dot-notation; `logical` hypergraphs can compose graphs |
| Freshness | Batch reload / incremental merge (`import mode=merge` skips existing); ⚠️ no CDC/streaming ingestion |
| Positioning vs virtualization | This is **materialized** knowledge (a semantic copy), not query pushdown to sources |

**Reference build (real):** six CSV files (~300 MB, 2M transactions) → **3,631,632 hypernodes + 1,872,417 hyperedges** with a generated ontology, 100 % provenance, 0 dangling members, 0 mismatches in 2,000 sampled rows, ≈ 13 min load.

---

## 32. Use Case 3 — Analytics Platform for Human Analysts

| Analyst task | Feature |
|---|---|
| Explore structure | Visualize (3D), tag/type filters, sortable tables |
| Ask precise questions | SHQL editor with examples, history, validation; parameterized templates for repeatable analyses |
| Networks and rings | Symmetric hyperedges (shared card/device/IP), transitive `linked-to` |
| "As of" analysis | `at:` queries, Visualize instant |
| Explain a result | `_inferred` / `_axiom` flags; provenance back to source line |
| Record and share | Notes with YAML front matter, scopes (`private` → `public-edit`) |
| Natural language | HgNexus over the same data |
| Integrate with BI / notebooks | 🛠️ REST + pagination to dataframes; result JSON from `/shql/query` |

**Data-architect view:** the analyst tier is a *thin client* over REST/SHQL — nothing is duplicated into a separate analytics store; heavy aggregations should be materialized (Project Inference) or done in a warehouse and *linked* to graph entities by id.

---

## 33. Use Case 4 — Analytics Platform for AI Agents via MCP

```
 Agent ─MCP─▶ hgai_hypergraph_list      → schema discovery (types, relations, counts)
             hgai_query_validate/execute → typed retrieval  (structure, time, provenance)
             hgai_infer_*               → derived facts with explanation
             hgai_hyperedge_create      → write-back (draft + provenance)
```

| Agent need | Architecture answer |
|---|---|
| Discover what exists | Graph list/stats; ontology nodes (`RelationType.domain/range`, class hierarchy) are queryable |
| Retrieve exactly | SHQL patterns; joins; aggregates; `limit` to protect context windows |
| Multi-hop / temporal / inferred | Joins over shared variables, `at:`, transitive closure and expansion tools |
| Write back safely | Convention-based drafts + provenance; read-back verification |
| Scale across domains | `hgai_mesh_query` |
| ⚠️ Control | Authentication only today: isolate the endpoint; per-agent scoping 🗺️ |

**Token economics (qualitative, unbenchmarked):** typed retrieval returns only matching rows/edges, so the model is not asked to filter large text dumps.

---

## 34. Use Case 5 — HgNexus with AI Vendors and Models

| Architect concern | HgNexus design |
|---|---|
| Vendor neutrality | Any enabled vendor/model (Anthropic, OpenAI, xAI); BYO keys; catalog is data |
| Data residency | Knowledge and history stay in *your* MongoDB; only prompts/tool results go to the chosen vendor |
| Cost control | Per-model enable, per-answer token counts recorded; no token resale |
| Auditability | Every answer stored with vendor, model, timing, tokens; exportable to a Note |
| Extensibility | Toolkits are per-turn objects (MCP, help, web); new toolkits are code changes in the module |
| Failure isolation | Module can be disabled (`HGAI_AGENT_CHAT_ENABLED=false`); core unaffected |
| ⚠️ Security | MCP tools inside a turn are not per-user scoped; restrict access to trusted accounts |
| 🗺️ | Per-session model switching with context hand-off; tool-call trace panel; usage dashboards |

---

## 35. Use Case 6 — Transient Memory / Workspace for Agents

**Goal:** give an agent a structured scratch area while it services one request — intermediate hypotheses, partial results, plans — that other agents can inspect and that can join durable knowledge.

```
 request R ─▶ agent creates scratch graph  ws-<R>   (or tag region  workspace:<R> in a shared graph)
              ├─ nodes: hypotheses, entities under consideration        status: draft
              ├─ edges: supports/contradicts/derived-from (with confidence in attributes)
              ├─ valid_to: time-box            └─ provenance: {agent, run, tool}
              └─ SHQL joins scratch ⨝ durable graph (from: [ws-R, enterprise])
 completion ─▶ promote selected facts (draft → active in the durable graph) · delete scratch graph
```

| Need | Live building block |
|---|---|
| Create/write/read/discard | `hgai_hypergraph_create`, node/edge tools, deletes |
| Provisional state | `status: draft`, tags, `valid_to` |
| Cross-graph reasoning | Multi-graph `from:` in SHQL |
| Hand-off between agents | Shared graph; audit trail |

🛠️ **Pattern, not a feature.** ⚠️ Not built: automatic expiry/cleanup and draft→active promotion (apply with a job or the orchestrator); `hypergraph_create` changes structure — pre-create workspaces or grant it deliberately.

---

## 36. Use Case 7 — Persisted Context Memory Across Vendors, Hosts, Models and Sessions

**Principle:** memory is *data in the customer's knowledge store*, not state inside a model vendor or chat product.

| Memory tier | Modelled as | Status |
|---|---|---|
| Working | scratch graph / draft records | 🛠️ |
| Session | records tagged `session:<id>`; HgNexus sessions stored server-side and restartable | ✅ (HgNexus) · 🛠️ (external agents) |
| Episodic | events/decisions as hyperedges with validity time and provenance | 🛠️ |
| Semantic | the domain knowledge graph itself | ✅ |
| Procedural | runbooks/constraints as nodes; Notes; Help topics | ✅ / 🛠️ |

| Continuity across… | Mechanism |
|---|---|
| **Vendors / models** | Any MCP/REST client reads and writes the same graph; no vendor-specific memory format |
| **Sessions** | Records outlive chats; HgNexus history (50 prompts/account) and sessions persist |
| **Hosting** | Mesh queries across servers; one-file export/import moves a graph between hosts |
| **People and agents** | Spaces, note scopes/grants govern visibility |

⚠️ HgNexus sessions are pinned to one model and transcripts are not replayed to a *different* model; cross-vendor continuity is achieved through the **shared graph**, not chat-log replay. 🗺️ Session hand-off, retention/expiry policies. Design **privacy and consent** explicitly: episodic memory about people is regulated data.

---

## 37. Use Case 8 — Other Compelling Architectures

| Use case | Why this platform | Architecture sketch |
|---|---|---|
| **Fraud / AML / cyber investigation** ✅ (demonstrated on synthetic data) | Rings, shared identifiers, n-ary events, provenance to source | Hub hyperedges per account/device/IP; symmetric "shares-*" edges; ring nodes; SHQL + Visualize |
| **Regulatory audit & explainable AI** | Inferred-vs-stored labelling, PIT reconstruction, audit trail | Provenance convention + `at:` + Note-based evidence packs |
| **Master data / customer 360** | Entity resolution as `exactMatch` hyperedges with lineage | One node per source record, alignment edges, golden-record view by query |
| **Data-mesh data products** | Domain-owned graphs federated by mesh | Server or space per domain; shared ontology graph |
| **Agent skill / runbook registry** 🛠️ | Procedures as versioned, queryable, permissioned knowledge | Procedure nodes + step hyperedges + validity |
| **Contracts, supply chain, clinical** 🛠️ | Inherently n-ary, temporal, multi-party | Event hyperedges with roles by `seq`, validity windows |
| **Knowledge brokering** 🗺️ | Publish curated graphs (ontology + facts + provenance) to other organizations over the mesh | Publisher server + consumer mesh; licensing/metering not built |

---

# Part 10 — Modeling Guidance and Patterns

---

## 38. Modeling Rules of Thumb (From a Real 5.5M-Record Build)

| Rule | Why |
|---|---|
| **Entity → hypernode; data literal → property; reference to another entity → hyperedge** | Keeps semantics queryable; properties stay cheap |
| **Model n-ary facts as one hyperedge** — but remember `hub` semantics: each spoke is an independent *(hub, spoke)* fact under the **same relation** | Distinct roles need distinct relations (or `seq` positions with a documented role order) |
| **Group by hub** (an account and all its transactions in one `rel:initiated` edge) and **chunk hubs at ≤ 250 spokes** | 2M transactions became ~1.87M edges with no loss; keeps documents small |
| **`symmetric` flavor** for peer/shared-attribute relations | Both directions without duplicates |
| **Declare relation types as nodes** with `domain`, `range`, `inverse_of`, characteristics; add axiom hyperedges | Self-describing ontology; inference drivers |
| **SKOS-style concept schemes** for categories, asserted in both `skos:broader` and `skos:narrower` | Closure queries work in either direction |
| **Provenance on everything**: `{run_id, dataset, source_file, source_row, method}`; flag derived or authored content | Auditability; re-verification |
| **IDs:** `type:name`; **never `.`** in graph/mesh/server ids; replace dots in IP-like ids | Dot-notation collision |
| **De-duplication:** identical relation + member set = one hyperkey; merge list-valued facts (e.g. several shared identifiers) into one edge | Uniqueness constraint |
| **Time:** put validity on the *fact* (edge) when the relationship changes, on the node when the entity's existence does | Correct `at:` semantics |

---

## 39. Patterns and Anti-Patterns

| ✅ Pattern | ⚠️ Anti-pattern | Why |
|---|---|---|
| Selective, indexed predicates first (`type`, `tags`, ids, member ids) | Unindexed attribute scans over millions of nodes as a hot path | Each pattern fetches a bounded candidate set |
| Targeted inference (`/infer/expand`, `/infer/transitive`) or **materialized** inference | `infer: true` over a very large graph | Bounded candidate set + expansion cost |
| Bulk load with generated export/import or a batch loader; verify afterwards | One REST call per record for millions | Hours instead of minutes |
| Hub edges with ≤ 250 spokes | One mega-hub edge with 100k+ members | Document size and hyperkey cost |
| Structured provenance object | Free-text lineage in `description` | Not queryable |
| Vector store for similarity + hypergraph for structure | Expecting similarity search from the hypergraph | No embedding index today |
| Separate servers for differently-sensitive data | Relying on MCP/SHQL to enforce tenant boundaries | Authorization gap today |
| Draft → review → active for agent writes | Letting agents write straight to `active` | Reviewability |

---

## 40. Worked Reference — Mapping CSV Datasets to a Hypergraph

Input: two fraud datasets (six CSVs). Output ✅:

| Source field kind | Target |
|---|---|
| Row identity (transaction, account) | Hypernode with literals in `attributes`; `source_row` in provenance |
| Categorical reference (merchant category, country, device type) | **SKOS concept node** + hub hyperedge (concept → transactions), concept hierarchy authored |
| Identifier reference (card, device, IP, merchant) | Entity node + hub hyperedge (entity → transactions) |
| Shared-attribute pairs (network links) | **Symmetric** hyperedge with `connection_count` as a property |
| Group id (fraud ring) | Ring node + hub edges to accounts and to its link hyperedges |
| Aggregates supplied in the source | Kept as supplied; *reconciled* against recomputed values (all matched) |
| Ontology | Class nodes, 55 relation types (inverse, symmetric, transitive, broader/narrower hierarchies), 4 concept schemes |

Loader pattern: stream CSVs → build documents in the engine's own shape → **bulk insert** with unordered batches → finalize graph counters → **verify** (counts, provenance coverage, referential integrity, random-row comparison, ontology queries). Throughput observed: ≈ 7k documents/s end-to-end including generation.

---

# Part 11 — Reference Architectures, NFRs, Deployment

---

## 41. Reference Architecture A — Departmental Knowledge Store

```
 users ─▶ Web UI / HgNexus ─┐
 scripts ─▶ hgsh / REST ─────┼─▶ HypergraphAI (1 container) ─▶ MongoDB (1 node or replica set)
 agents ─▶ MCP ──────────────┘                                    └─ mongodump (nightly)
```
Use for: a team's ontology + data, agent pilots, analyst workbench. Docker Compose ships this topology (`hgai` + `mongo`, health checks, volumes). Harden per the checklist.

## 42. Reference Architecture B — Federated Enterprise Mesh

```
        ┌──────────── mesh registry (hub server) ────────────┐
 Finance server        Risk server        Ops server        Shared-ontology server
   (space per BU)     (graphs per product)  (graphs)          (ontology graph)
        ▲                   ▲                  ▲                    ▲
        └── each with its own MongoDB, own RBAC, own backup ───────┘
 Analysts / agents query the hub:  from: enterprise-mesh   or   enterprise-mesh.risk.aml-graph
```
Use for: data-mesh ownership, regional/regulatory separation, blast-radius control. Pair with a gateway to enforce per-domain access on MCP/SHQL (current gap).

---

## 43. Reference Architecture C — GraphRAG Hybrid Agent Platform

```
 User ─▶ Agent orchestrator ─▶ LLM gateway (vendor abstraction)
              │  tools:
              ├─ retrieval ─▶ Vector store / search   (similarity → candidate entity ids)
              ├─ MCP ───────▶ HypergraphAI            (expand ids: relationships · time · provenance · inference)
              └─ MCP/REST ──▶ operational systems      (actions)
              ▲                    │ write-back: draft findings + provenance
              └── memory: HypergraphAI holds session/episodic/semantic memory (vendor-neutral)
```
The hypergraph is the **memory and grounding tier**; the vector store remains the similarity tier. Entity ids are the join key. 🛠️

## 44. Reference Architecture D — Regulated / Air-Gapped

Self-hosted, no outbound dependencies except optional AI vendor (omit HgNexus, or point it at an on-prem OpenAI-compatible endpoint via the vendor `base_url`); TLS termination and network policy in front; separate server per classification level; mesh only between servers allowed to exchange data; audit review of `mutations[]` and provenance.

---

## 45. Non-Functional Characteristics

| NFR | Today | Notes |
|---|---|---|
| **Scalability** | Verified with 5.5M records (3.6M nodes, 1.9M edges, 13.5M member slots) for load and targeted queries | ⚠️ No sharded backend; whole-graph inference and in-memory export are bounded; API tier scales out statelessly (🛠️, not load-tested) |
| **Performance** | Indexed lookups in ms; selective attribute scans over ~1M docs in seconds; bulk load ≈ 7–20k docs/s | Design queries around indexes; cache repeated queries (TTL 300 s default) |
| **Availability** | Stateless app tier; MongoDB replica set provides DB HA | ⚠️ No HA reference architecture, no leader-elected background tasks (mesh sync runs in every instance) |
| **Consistency** | Per-document atomic writes; counters maintained by the engine | No multi-document transactions across nodes/edges |
| **Durability / DR** | MongoDB backups (`mongodump`), per-graph export files | No built-in PITR beyond MongoDB's |
| **Security** | See Security section | ⚠️ MCP/SHQL authorization gap; no SSO |
| **Observability** | Application logging; health endpoint; per-answer token stats (HgNexus); `mcp-agent` audit stamps | ⚠️ No metrics endpoint, tracing or dashboards |
| **Operability** | One image, environment-variable config, idempotent index creation, seed loader, verify script pattern | Modules fail soft |
| **Portability** | MIT core; Docker; export/import files; MongoDB-compatible stores | Single backend implemented |
| **Extensibility** | Module contract; storage ABC; ontology as data | Marketplace/packaging 🗺️ |

---

## 46. Deployment Topologies

| Topology | How | When |
|---|---|---|
| **Laptop / dev** | `./hgai.sh` (port 8357) + local MongoDB | Evaluation, development |
| **Docker Compose** | `docker-compose up -d` (server on 8000 + MongoDB) | Team pilot, demo |
| **Scaled app tier** 🛠️ | N replicas behind a load balancer, shared MongoDB replica set | Higher concurrency |
| **Federated** | Several servers, each with own DB, joined by a mesh | Domain ownership, regions |
| **Kubernetes** 🛠️ | Deployment (stateless) + managed MongoDB/Atlas + S3 for media | Enterprise platforms |

**Configuration (12-factor):** `HGAI_*` environment variables — storage backend, Mongo URI/DB, secret key, token lifetime, API keys, host/port, log level, cache enable/TTL, server id/name, mesh sync interval, media backend (+S3 settings), help directory, agent-chat switch, admin bootstrap credentials. Defaults are development-grade (default admin credentials, `CORS *`): **override for production.**

---

## 47. Sizing and Performance Envelope (Measured, Not Promised)

| Observation | Value | Context |
|---|---|---|
| Graph size loaded and verified | 3,631,632 nodes · 1,872,417 edges · 13.5M member slots | Synthetic fraud data, single MongoDB |
| End-to-end build + bulk load | ≈ 13 min (≈ 7k docs/s with generation and index maintenance) | Direct bulk insert; a pilot loaded ≈ 20k docs/s |
| Indexed member lookup (ring → accounts) | ≈ 10 ms | `members.node_id` index |
| Selective attribute query, 20 rows | ≈ 5–9 s | Scan of the 1M-node subset selected by `type` + `tags` |
| Tag-scoped aggregate over 282 ontology hyperedges | ≈ 2.5 s | `aggregate`/`group_by` |
| Single-edge inference (`/infer/expand`) | interactive | Targeted path |
| Whole-graph `infer: true`, 187k edges | did not finish in several minutes | Bounded-candidate expansion |
| Whole-graph export | in-memory | Impractical at millions of records |

**Sizing guidance:** treat ~10⁶–10⁷ documents on one MongoDB as the demonstrated envelope; beyond it, federate by domain and materialize derived structure. Run your own benchmark on your data and hardware before committing.

---

## 48. Adoption Path for an Architecture Team

| Phase | Weeks | Activities | Exit criteria |
|---|---|---|---|
| **1 · Frame** | 0–2 | Pick one bounded use case (e.g. agent grounding for one domain); identify sources, ontology seeds, sensitivity | Use-case brief, data-classification decision, topology choice |
| **2 · Prove** | 2–6 | Docker Compose; load a sample (seed + a generated build from one source); connect one MCP client; write 10 SHQL queries; measure | Working demo, provenance conventions, query cookbook |
| **3 · Harden** | 6–10 | Secrets, TLS, CORS, network isolation of `/mcp/`, backups, gateway allow-lists, review process for agent drafts | Security review passed; runbook |
| **4 · Integrate** | 10–16 | Ingestion pipelines (bulk/merge), materialize inference, HgNexus for a pilot group, mesh a second domain | Two domains federated; pilot feedback |
| **5 · Scale** | 16+ | Benchmark; decide consolidate-vs-federate; contribute connectors/ontology packs as modules | Reference architecture ratified |

**Evaluate against your criteria:** n-ary fidelity gain, provenance completeness, agent answer quality with/without the graph, ingestion effort, operational fit — and the gaps listed on the next slide.

---

## 49. Gaps, Roadmap and Decision Guidance

| Gap ⚠️ | Impact | Roadmap 🗺️ |
|---|---|---|
| **MCP and SHQL do not apply per-graph/space authorization** | Any authenticated caller reaches all graphs; API key = admin | Per-caller authorization in both paths (first item) |
| MCP writes stamped `mcp-agent` | Weak agent attribution | Per-agent identity stamping / scoped keys |
| No native vector/embedding search | Pair with a vector store | Embedding attributes + hybrid retrieval module |
| Single storage backend (MongoDB) | Vendor concentration | Additional backends via the storage ABC |
| Bounded `infer: true`; in-memory export | Large-graph limits | Streaming export; incremental / indexed inference |
| No SSO, HA reference, metrics/tracing | Enterprise ops gaps | SSO/OIDC, HA guide, Prometheus/OTel |
| Memory lifecycle is application-side; sessions pinned to one model | Manual hygiene | Lifecycle policies; session hand-off |
| No marketplace or packaged connectors | Build integrations yourself | Module distribution and connector packs |

**Choose HypergraphAI when** relationships with meaning, time and provenance must be shared by people and agents; n-ary fidelity matters; you want an open-core, self-hostable, MCP-native knowledge tier. **Choose something else (or add to it) when** you need proven multi-billion-edge scale, native similarity search, or mature enterprise IAM today.

---

## 50. Summary

- **What:** a semantic knowledge hypergraph platform — n-ary hyperedges, rules-as-data inference, time, provenance — as one FastAPI process over MongoDB with a Web UI, shell, REST and **30 MCP tools**.
- **Architecture:** stateless app tier · module system with fail-soft mounting · storage abstraction (10 store interfaces) · SHQL over binding sets with caching · mesh federation · optional S3 media.
- **MCP:** streamable-HTTP, stateless, bearer-authenticated façade over the same engine; agents follow a discover → validate → query → infer → write-back loop.
- **Security today:** solid REST-level RBAC and tenancy; **MCP and SHQL authenticate but do not authorize per graph** — isolate them or scope by topology until fixed.
- **Use cases:** enterprise store, semantic layer, analyst analytics, agent analytics, HgNexus, transient and persistent memory, fraud/AML and more — each mapped to features and gaps.
- **Evidence:** a 5.5M-record, fully provenanced build with verified fidelity; 346 automated tests.

**Next step:** a 2–6 week proof (Adoption Path, phases 1–2) on one bounded domain.

---

# Appendix

---

## A1. MCP Tool Catalog (30)

| Group | Tools |
|---|---|
| Hypergraph | `hgai_hypergraph_list` `hgai_hypergraph_get` `hgai_hypergraph_stats` `hgai_hypergraph_create` |
| Hypernode | `hgai_hypernode_list` `hgai_hypernode_get` `hgai_hypernode_create` `hgai_hypernode_update` `hgai_hypernode_delete` |
| Hyperedge | `hgai_hyperedge_list` `hgai_hyperedge_get` `hgai_hyperedge_create` `hgai_hyperedge_delete` |
| Query | `hgai_query_execute` `hgai_query_validate` |
| Inference | `hgai_infer_expand_edge` `hgai_infer_check_transitive` |
| Mesh | `hgai_mesh_list` `hgai_mesh_get` `hgai_mesh_ping` `hgai_mesh_sync` `hgai_mesh_query` |
| Media | `hgai_media_upload` `hgai_media_download` `hgai_media_delete` |
| Space | `hgai_space_list` `hgai_space_get` `hgai_space_create` `hgai_space_add_member` `hgai_space_list_graphs` |

Example call (arguments are simple JSON; complex fields are JSON *strings*):

```json
{ "name": "hgai_hyperedge_create",
  "arguments": { "graph_id": "my-graph", "relation": "rel:initiated",
    "members_json": "[{\"node_id\":\"acct:A1\",\"seq\":0},{\"node_id\":\"txn:T1\",\"seq\":1}]",
    "label": "Account A1 initiated T1",
    "attributes_json": "{\"provenance\":{\"agent\":\"triage-bot\",\"run\":\"r-42\",\"confidence\":0.8}}",
    "tags": "proposed-by-agent" } }
```

---

## A2. REST Surface (Selected)

| Area | Endpoints |
|---|---|
| Auth | `POST /auth/token`, `GET /auth/me` |
| Graphs | `GET/POST /graphs`, `GET/PUT/DELETE /graphs/{id}`, `/stats`, `GET` or `POST /graphs/{id}/export?format=yaml`, `POST /graphs/import` (`mode=create` or `merge`), `POST /graphs/{id}/import` |
| Nodes / edges | `/graphs/{g}/nodes`, `/graphs/{g}/edges` (+ `/spaces/{s}/graphs/{g}/…`) |
| Query | `POST /shql/query`, `/shql/validate`, `/shql/cache/invalidate`, `GET /shql/history` |
| Inference | `POST /graphs/{g}/infer/transitive`, `/infer/expand`, `/infer/project` |
| Meshes (admin) | `/meshes`, `/meshes/{id}/ping`, `/sync`, `/query` |
| Spaces / accounts | `/spaces…`, `/accounts…` |
| Notes / Help / Media / Queries | `/notes…`, `/help/…`, `/media…`, `/parameterized-queries…` |
| HgNexus | `/agent/vendors`, `/agent/models`, `/agent/sessions`, messages (SSE), prompt history |
| System | `GET /health`, `GET /api/v1/server/info`, `/api/docs` |

---

## A3. SHQL Cheat Sheet

```yaml
shql:
  from: hello-world              # graph | "space/graph" | [list] | mesh-id | mesh.server.graph
  at: "1940-06-01T00:00:00Z"     # point in time (optional)
  infer: true                    # axiom-driven inference (optional; bounded candidate set)
  where:
    - edge:
        bind: ?e
        relation: rel:member
        members:
          - node_id: group:three-stooges
          - node_id: ?person_id       # a member pattern binds ids only ...
    - node:
        bind: ?person
        id: ?person_id                # ... join to its node to constrain it
        type: Person
    - filter: "CONTAINS(?person.description, 'Howard')"
  select:                         # write ?variables in block style; never inside { } or [ ]
    - ?person.id
    - ?person.label
  order_by: ?person.label
  limit: 20
```

Operators: MongoDB operators inside `attributes:`; filters `= != < > <= >= IN CONTAINS STARTS_WITH ENDS_WITH BOUND IS_TYPE AND OR NOT`; `optional:`, `union:`; `aggregate: {count, group_by}`; `distinct`; multi-key `order_by` with `asc|desc`.

---

## A4. Key Configuration (`HGAI_*`)

| Variable | Purpose |
|---|---|
| `HGAI_STORAGE_BACKEND`, `HGAI_MONGO_URI`, `HGAI_MONGO_DB` | Storage |
| `HGAI_SECRET_KEY`, `HGAI_TOKEN_EXPIRE_MINUTES` | JWT signing; also derives the vendor-key encryption key |
| `HGAI_PRIMARY_API_KEY`, `HGAI_SECONDARY_API_KEY` | Machine credentials (full admin) |
| `HGAI_HOST`, `HGAI_PORT`, `HGAI_LOG_LEVEL`, `HGAI_CORS_ORIGINS` | Server |
| `HGAI_CACHE_ENABLED`, `HGAI_CACHE_TTL_SECONDS` | Query cache |
| `HGAI_SERVER_ID`, `HGAI_SERVER_NAME`, `HGAI_MESH_SYNC_INTERVAL_SECONDS` | Identity and federation |
| `HGAI_MEDIA_BACKEND` (`gridfs`\|`s3`), `HGAI_S3_*`, `HGAI_MAX_MEDIA_SIZE_MB` | Media |
| `HGAI_AGENT_CHAT_ENABLED` | HgNexus on/off |
| `HGAI_HELP_DIR` | Built-in Help content location |
| `HGAI_ADMIN_USERNAME/PASSWORD/EMAIL` | Bootstrap admin (change defaults) |

---

## A5. Glossary

| Term | Meaning |
|---|---|
| **Hyperedge** | A relationship that links any number of nodes and has its own data |
| **Hub / symmetric flavor** | Focal-member vs all-equivalent-members decomposition into facts |
| **Hyperkey** | SHA-256 identity of a hyperedge (relation + members + graph + validity) |
| **Axiom hyperedge** | A hyperedge declaring relation semantics (`owl:*`, `skos:*Transitive`) |
| **SHQL** | Semantic Hypergraph Query Language (YAML, pattern-matching) |
| **PIT** | Point-in-time query (`at:`) |
| **Mesh** | Registry of servers queried together |
| **Space** | Tenant namespace with member roles |
| **MCP** | Model Context Protocol: tool interface for AI models |
| **HgNexus** | The integrated multi-vendor AI agent chat |
| **Provenance** | Source lineage recorded under `attributes.provenance` |
| **GraphRAG** | Retrieval-augmented generation grounded in a knowledge graph |

---

## A6. Where to Read More (in this repository)

- `README.md` — overview, quick start, API and MCP reference, SHQL language and examples
- `docs/api-reference.md` — REST reference (incl. export/import, notes scopes, help)
- `docs/module-development.md` — module contract and custom storage
- `docs/help/notes/` — the 40 in-product Help topics (also searchable by HgNexus)
- `docs/decks/demo-ai-context-memory-20260817/` — agent-memory tiers and lifecycle
- `scripts/seeds/`, `scripts/generators/` — example graphs, the CSV-to-hypergraph generator and its verifier
- `.project/prompts/mutations/` — change records, including the 5.5M-record build and its audit Note
