---
title: "HypergraphAI — Technical Architecture Deck for Enterprise AI Architects"
description: "Reference architecture, security model, query surface, operations, and adoption path for evaluating HypergraphAI as the context/memory store for AI agentic systems"
---

# HypergraphAI

### Reference Architecture for AI Agent Context & Memory

*A technical adoption deck for enterprise AI/platform architects — no funding
narrative, no market sizing. Every claim below is checked against the
codebase, not the marketing copy.*

**Format:** each `---` is one slide. Open in Marp/reveal-md/Slidev, or read
top-to-bottom — every command and query is copy-pasteable either way.

---

## Slide 1 — The Architectural Problem

# Why Agent Memory Needs a Different Data Model

An agentic AI system needs a knowledge store that answers four questions a
typical store answers poorly or not at all:

| Question | RDBMS | Property graph | Vector store | Document store |
|---|---|---|---|---|
| Who/what was involved, as one atomic fact? | Needs a join table | Binary edges only | No structure | No relationships |
| What *kind* of relationship is this? | FK, untyped | Edge label only | N/A | Attribute, untyped |
| Was this true at time T? | Usually not | Usually not | No | No |
| Why did the agent believe this? | No native trail | No native trail | No | No |

A contract with a buyer, seller, witness, and jurisdiction is **one fact**
with four participants — not four rows to reassemble via joins, and not
four separate 2-node edges an agent has to infer are related.

---

## Slide 2 — Core Data Model

# Three Primitives, Fully Attributed

**Hypernode** (`hgai/models/hypernode.py`) — an entity:
```
id, label, type, description, attributes: {...}, tags: [...],
status: active|draft|archived, valid_from, valid_to
```

**Hyperedge** (`hgai/models/hyperedge.py`) — an *n*-ary, first-class
relationship, not a pointer:
```
id, relation, label, flavor, members: [{node_id, seq}, ...],
attributes: {...}, tags, status, valid_from, valid_to,
skos_broader/narrower/related, relation_node_id,
hyperkey  (SHA-256 of normalized relation+members+graph — dedup key)
```

**Hypergraph** — a named container, either an **instantiated** physical
MongoDB-backed collection, or a **logical** composition of other
hypergraphs (local or remote) with zero data duplication.

Every hypernode and hyperedge carries `valid_from`/`valid_to` — temporal
validity is a first-class field on every entity, not a bolt-on audit table.

---

## Slide 3 — Hyperedge Flavors & Positional Semantics

# Relationship Shape Is Declared, Not Inferred

| Flavor | Semantics |
|---|---|
| `hub` | One focal member, others relate to it (teams, contracts, group membership) |
| `symmetric` | All members equivalent — A↔B (siblings, peers) |
| `direct` | Directed, first member → last, no transitivity implied |
| `transitive` | A→B, B→C implies A→C |
| `inverse-transitive` | Transitive closure walked in reverse |

Members carry an explicit `seq` (sequence position), queryable positionally
— e.g. "the *first* member of this edge is node X," not just "X is a
member somewhere in this edge":

```yaml
hql:
  where:
    members:
      seq: 0
      node_id: "team:platform"
```

Internally this compiles to a MongoDB `$elemMatch` so `seq` and `node_id`
are guaranteed to bind to the *same* array element — a single member
sub-field (e.g. just `node_id`) stays a simple "contains" filter, unaffected.

---

## Slide 4 — Reference Architecture

# Layered, Modular, Nothing Load-Bearing Is a Black Box

```
┌--------------------------------------------------------------┐
│                      HypergraphAI Platform                   │
├--------------┬---------------┬--------------┬----------------┤
│  Web UI      │  REST API     │  MCP Server  │  hgai Shell    │
│  (Browser)   │  (FastAPI)    │  (25 tools)  │  (CLI, prompt_toolkit) │
├--------------┴---------------┴--------------┴----------------┤
│                      Pluggable Modules                       │
│  hgai_module_hql   — YAML filter/aggregate query engine      │
│  hgai_module_shql  — SPARQL-style pattern-matching engine    │
│  hgai_module_mesh  — federated multi-server query fan-out    │
│  hgai_module_mcp   — Model Context Protocol tool surface     │
├--------------------------------------------------------------┤
│              Core Engine (hgai/core/)                        │
│  engine.py (CRUD+hyperkey) │ auth.py (JWT/API-key/RBAC)      │
│  cache.py (graph-scoped)   │ space_engine.py (multi-tenancy) │
├--------------------------------------------------------------┤
│    hgai_module_storage — backend-agnostic interface/registry │
│    hgai_module_storage_mongodb — MongoDB implementation      │
└--------------------------------------------------------------┘
```

Every module here is independently importable and mounts conditionally at
startup (`hgai/main.py`) — a missing/broken module logs a warning and the
server still starts, rather than hard-failing the whole platform.

---

## Slide 5 — Storage Backend: Pluggable, Not Hardcoded

# The Query Engines Don't Know They're Talking to MongoDB

`hgai_module_storage/registry.py` implements a backend registry
(`register_backend(name, cls)` / `get_backend_class(name)`); HQL, SHQL, and
the core engine all talk to `get_storage()` — an interface, not a MongoDB
client directly. `hgai_module_storage_mongodb` is the current (only
shipping) implementation.

**What this buys an architect today:**
- A defined seam for adding a second backend without touching query-engine
  code — this is a real abstraction boundary in the code, not aspirational
- Storage backend selectable via `HGAI_STORAGE_BACKEND` env var

**What it does *not* mean today:** only MongoDB is implemented and tested.
Treat backend portability as "the door is built," not "walk through it" —
if a non-Mongo backend is a hard requirement, that's new engineering work,
not a config flag.

---

## Slide 6 — Query Surface: HQL

# YAML Filter/Aggregate, MongoDB-Flavored Semantics

```yaml
hql:
  from: engineering-org
  at: "2026-01-01T00:00:00Z"          # point-in-time, optional
  match:
    type: hyperedge
    relation: "rel:member"
  where:
    members:
      seq: 0
      node_id: "team:platform"
    status: active
  return:
    - id
    - relation
    - members
    - attributes
  aggregate:
    count: true
    group_by: relation
  limit: 500
  as: platform_team_edges
```

Supports `$gt/$lt/$in/$all/$regex`-style operators, boolean `AND/OR` in
`where`, `distinct`, `skip`/`limit`, and multi-graph `from:` lists that
compose transparently with logical-graph expansion.

---

## Slide 7 — Query Surface: SHQL

# SPARQL-Style Pattern Matching, Multi-Hop Joins

```yaml
shql:
  from: engineering-org
  where:
    - node: ?person
      node_type: Person
    - edge: ?membership
      relation: "rel:member"
      members:
        - node_id: ?person
        - bind: ?team_id
          seq: 0
    - filter:
        CONTAINS: [?person.label, "Lee"]
  select:
    - ?person.label
    - ?team_id
    - ?membership.id
  order_by: ?person.label
  limit: 50
```

Variables (`?var`) act as implicit join keys across `node`/`edge`
patterns. Also supports `OPTIONAL` (left-outer-join semantics) and `UNION`
(branch alternatives) — the two patterns most SQL-native teams reach for
first when modeling "give me X, and Y if it exists."

---

## Slide 8 — Federation: Mesh Queries

# One Query, Many Servers, No ETL

A **mesh** is a registered set of HypergraphAI servers. A single HQL/SHQL
query can address a local graph, a specific remote graph, or fan out
across an entire mesh — via dot-notation in `from:`:

```yaml
hql:
  from: alpha-bravo-mesh.*.stooges-graph   # this graph, on every server in the mesh
  match:
    type: hypernode
  return: [id, label, "_mesh_server_id"]
```

**This is concurrent, not sequential** — every mesh fan-out uses
`asyncio.gather`:

| Operation | Sequential cost | Actual cost |
|---|---|---|
| `ping_mesh` | N servers × 10s timeout | ~10s regardless of N |
| `federated_hql` / `federated_shql` | N servers × query time | ~1× query time |

Unreachable servers are skipped and reported in an `errors` field —
one down server doesn't fail the whole query. The local server is always
served by a direct in-process engine call, not a loopback HTTP request.

---

## Slide 9 — MCP Integration: The Agent-Facing Surface

# 25 Tools, Grouped by Domain

```
hgai_hypergraph_*  list · get · stats · create
hgai_hypernode_*   list · get · create · update · delete
hgai_hyperedge_*   list · get · create · delete
hgai_query_*       execute (HQL/SHQL) · validate
hgai_mesh_*        list · get · ping · sync · query
hgai_space_*       list · get · create · add_member · list_graphs
```

**How an agent uses this as memory:**
- **Write path** — the agent asserts a fact by creating a hyperedge (e.g.
  "I recommended X because of Y, at time T") via `hgai_hyperedge_create`,
  with the reasoning captured in `attributes`, not lost after the turn ends
- **Read path** — the agent queries via `hgai_query_execute` (HQL/SHQL) to
  recall structured context before reasoning, instead of re-deriving it
  from raw transcript history
- **Provenance** — because edges are first-class and temporal, "why did
  the agent do that" is answerable by querying the edge trail `at:` the
  decision time, not by re-reading logs

**Known gap:** there is no `hgai_hyperedge_update` MCP tool — hypernodes
have full CRUD via MCP, hyperedges do not (create/delete only, today).
Plan around this if agent workflows need to *revise* an existing edge's
attributes via MCP rather than delete-and-recreate.

---

## Slide 10 — Security Model: Authentication

# Two Methods — Know Their Difference Before You Design Around Them

**JWT tokens** (`POST /api/v1/auth/token`) — for interactive users and the
Web UI. Username/password → bearer token, `HGAI_TOKEN_EXPIRE_MINUTES`
lifetime (default 480 min), roles embedded in the token claims.

**API keys** (`HGAI_PRIMARY_API_KEY` / `HGAI_SECONDARY_API_KEY`) — for AI
agents, MCP clients, and machine-to-machine callers. Stateless, no login
step, two-key rotation supported.

> **Architecturally important, not a minor detail:** API keys currently
> **grant full admin access** — there is no per-key role or scope
> restriction today. An MCP-connected agent authenticated via API key has
> the same authority as a human admin. If your threat model requires an
> agent to have narrower permissions than a human admin, that's a gap to
> design around (e.g. a proxy enforcing scope) rather than a config option
> that exists today.

---

## Slide 11 — Security Model: RBAC & Roles

# Four Roles, Resolved Before Any Query Runs

| Role | Scope |
|---|---|
| `admin` | Full system access, including account management |
| `user` | Read/write on permitted hypergraphs |
| `agent` | API/MCP-only access, intended for AI agents |
| `readonly` | Read-only |

Roles are checked in `hgai/core/auth.py`; every protected route resolves
the caller's roles before touching storage. Combined with Spaces (next
slide) for tenant-scoped access, this is the access-control surface a
security review will actually exercise — worth a dedicated pass before
production rollout, since (per Slide 10) API-key auth bypasses role
granularity entirely today.

---

## Slide 12 — Multi-Tenancy: Spaces

# Tenant Isolation Is a Membership Check, Not a Convention

A **Space** groups hypergraphs for multi-tenant deployments. Space roles:
`owner` (full control + manage space) → `admin` (manage members) →
`member` (read/write/query/export/import) → `viewer` (read/query/export).

**Access resolution order (exact, from `hgai/core/space_engine.py`):**
1. **Global admin** (`"admin"` in account roles) bypasses all checks
2. **Space membership** — if the graph belongs to a space, the account
   *must* be a member of that space; non-members are rejected regardless
   of anything else
3. **`permissions.graphs`** — applies only to *unowned* (non-space) graphs

```
hql: { from: team-a/eng-graph }     # space-scoped
hql: { from: [team-a/g, team-b/g] } # same graph ID, different spaces — no conflict
```

**The load-bearing guarantee:** a `permissions.graphs: ["*"]` wildcard on
an account **cannot** leak across tenant boundaries into a space that
account isn't a member of. This is the property a multi-tenant deployment
review will specifically want demonstrated, not just stated.

---

## Slide 13 — Performance: Indexes

# Every Hot Path Is Indexed at Startup, Idempotently

Indexes are created automatically (`ensure_indexes()`,
`hgai_module_storage_mongodb/indexes.py`) on every server start — skips
existing indexes with matching definitions, safe to run repeatedly.

| Collection | Key indexes | Purpose |
|---|---|---|
| `hypernodes` | `id+hypergraph_id` (unique), `hypergraph_id+status`, `hypergraph_id+type`, `tags` (multikey), `hypergraph_id+valid_from+valid_to` (sparse, PIT) | Per-graph ID uniqueness, hot-path listing, temporal queries |
| `hyperedges` | `id+hypergraph_id` (unique), `hyperkey+hypergraph_id` (unique — semantic dedup), `hypergraph_id+relation`, `members.node_id` (multikey), PIT (sparse) | Dedup at the DB layer via hyperkey, relation/membership filtering |
| `query_cache` | `cache_key` (unique), `graph_ids` (multikey), `expires_at` (TTL) | Cache hit lookup, scoped invalidation, automatic expiry |

**Without these, every query is a full collection scan** regardless of how
much concurrency is layered on top — indexes are the single highest-impact
lever on latency, called out explicitly in the project's own performance
notes, not an afterthought.

---

## Slide 14 — Performance: Query Result Caching

# Graph-Scoped Invalidation, Not a Blunt TTL-Only Cache

Every cached result stores which local `hypergraph_id`s it touched. A
write to graph `X` runs `delete_many({"graph_ids": "X"})` — evicting only
entries that actually queried `X`, leaving every other graph's cache warm.

| Query shape | What gets invalidated on write to graph X |
|---|---|
| `from: X` | Evicted |
| `from: [X, Y]` | Evicted (touched X) |
| `from: [Y, Z]` | **Not evicted** — never touched X |
| Remote mesh dot-ref only | Never graph-evicted; expires via TTL only |

Config: `HGAI_CACHE_ENABLED`, `HGAI_CACHE_TTL_SECONDS` (default 300),
`HGAI_CACHE_MAX_SIZE`. A hypergraph-level create/update/delete triggers a
full cache flush (not graph-scoped) since it changes what "the graph"
even resolves to.

---

## Slide 15 — Operations: Deployment & Networking

# One Compose File, Health-Checked, Container-Native

`docker-compose.yml` ships two services: `mongo:7` and the `hgai` app
image, wired with a `healthcheck` on each (`mongosh ping` / `curl
/health`) and `depends_on: condition: service_healthy` so the app doesn't
start against a not-yet-ready database.

```bash
docker compose up          # MongoDB + hgai server, one command
curl http://localhost:8000/health
```

Configuration is entirely environment-variable driven (`HGAI_` prefix,
`pydantic-settings`, `.env`-file-aware) — no config files to template for
different environments, just env var overrides per deployment target.
Outbound mesh HTTP calls share a single pooled `httpx.AsyncClient`
(`max_connections=100`, `max_keepalive_connections=20`) rather than a
connection per request — relevant when sizing a mesh with many peer
servers.

---

## Slide 16 — Operations: Backup, Restore, and What's Not There Yet

# Standard Mongo Tooling Today — Not Bespoke HA Yet

```bash
docker-compose exec mongo mongodump  --username admin --password <pwd> \
  --authenticationDatabase admin --db hgai --out /backup

docker-compose exec mongo mongorestore --username admin --password <pwd> \
  --authenticationDatabase admin --db hgai /backup/hgai
```

**What this means for an architecture review:** backup/restore today is
"you own standard MongoDB operational practice" — replica sets, point-in-
time recovery beyond Mongo's own tooling, and multi-region write topology
are **not** provided or documented as a HypergraphAI-specific capability.
If your enterprise HA/DR bar requires more than what MongoDB itself
provides out of the box, plan that as infrastructure work alongside
adoption, not as something the platform hands you.

---

## Slide 17 — Honest Gap Assessment

# What We Verified Is *Not* Built — So You Don't Discover It in Prod

| Capability implied by docs/marketing | Actual status |
|---|---|
| SKOS/semantic inferencing (`broader`/`narrower`/`related`) | 🔶 Data model exists; `hgai/core/inference.py` has zero call sites anywhere in the codebase — not wired to any API, query engine, or MCP tool |
| Audit logging | 🔶 An `audit_log` index is defined; **nothing in the codebase writes to that collection** — there is no audit trail today despite the index existing |
| `hgai_hyperedge_update` (MCP) | ❌ Not present — hyperedges are create/delete only via MCP; use the REST API for updates via agent tooling if needed |
| API-key scoped permissions | ❌ API keys are all-or-nothing full-admin (Slide 10) |
| Non-MongoDB storage backend | 🔶 Registry/interface exists; only MongoDB is implemented |
| Enterprise SSO (SAML/OIDC) | ❌ Not present — JWT (username/password) and API keys only |

None of these are disqualifying for a scoped pilot — they're exactly the
kind of thing to raise in an architecture review *before* committing to a
production timeline that assumes them.

---

## Slide 18 — Comparative Positioning (Technical)

# Where HypergraphAI's Data Model Actually Differs

| Property | Neo4j | Amazon Neptune | Weaviate | Stardog | **HypergraphAI** |
|---|:---:|:---:|:---:|:---:|:---:|
| Native n-ary edges (no reification pattern needed) | ✗ | ✗ | ✗ | ✗ | ✅ |
| Edge is a first-class attributed document | ✗ | ✗ | ✗ | Partial | ✅ |
| Native temporal validity per node/edge | ✗ | ✗ | ✗ | Partial | ✅ |
| MCP-native agent access | ✗ | ✗ | ✗ | ✗ | ✅ |
| Federated multi-server query fan-out | ✗ | ✗ | ✗ | ✗ | ✅ |
| Production inferencing engine | ✅ (via plugins) | ✗ | ✗ | ✅ | ❌ (roadmap) |
| Managed cloud offering | ✅ | ✅ | ✅ | ✅ | ❌ (self-host today) |
| Query language maturity / ecosystem | High (Cypher) | Medium | Medium | High (SPARQL) | Early (HQL/SHQL) |

This is a **younger platform with a genuinely different edge model** — the
right comparison isn't "does it beat Neo4j at Neo4j's own game" but
"does the n-ary, temporal, MCP-native model reduce integration work for
*your specific* agent-memory use case enough to offset ecosystem maturity."

---

## Slide 19 — Migration & Incremental Adoption

# You Don't Have to Migrate Everything on Day One

**Model a slice, not the estate.** Pick one bounded context (a team's org
chart, a product catalog, a decision log) and represent it as hypernodes +
hyperedges. This is a modeling exercise, not a data migration project —
existing systems of record stay authoritative until you choose otherwise.

**Coexist via federation, not ETL.** The mesh module lets a pilot
hypergraph on one team's server be queried alongside production graphs
elsewhere — there's no requirement to consolidate into one physical store
before it's useful.

**RDBMS → hypergraph mapping pattern:**
```
A join table between users, roles, and projects (3-way M:N)
  → one hyperedge per (user, role, project) assignment,
    flavor: hub, members: [user, role, project]
  → no join at query time; the assignment IS the row
```

**Property-graph → hypergraph mapping pattern:** an n-ary fact modeled as
several 2-node edges plus a synthetic "event" node in a property graph
collapses to a single hyperedge with n members — fewer entities, one
fewer join, and the relationship's own attributes live in one place.

---

## Slide 20 — Reference Use Case: Agent Decision Memory

# A Concrete Read/Write Pattern

**Write (agent asserts a fact mid-task):**
```yaml
# via hgai_hyperedge_create (MCP) or POST /api/v1/graphs/{g}/edges
relation: "decision:recommended"
flavor: hub
members:
  - { node_id: "agent:deploy-advisor", seq: 0 }
  - { node_id: "service:checkout-api", seq: 1 }
  - { node_id: "region:us-east-1", seq: 2 }
attributes:
  rationale: "lowest observed p99 latency in last 24h window"
  confidence: 0.82
valid_from: "2026-08-08T14:32:00Z"
```

**Read (a later agent turn, or a human, asks "why"):**
```yaml
shql:
  from: ops-graph
  at: "2026-08-08T15:00:00Z"
  where:
    - edge: ?d
      relation: "decision:recommended"
      members:
        - node_id: "service:checkout-api"
  select: [?d.attributes.rationale, ?d.attributes.confidence, ?d.members]
```

The rationale isn't reconstructed from a transcript — it's a queryable
fact with its own identity, timestamp, and confidence attribute.

---

## Slide 21 — Proof-of-Concept Path

# A Scoped Pilot, Not a Big-Bang Adoption Decision

| Phase | Activity | Exit criteria |
|---|---|---|
| **0 — Environment** | `docker compose up`, verify `/health`, log in as bootstrap admin, rotate the default password immediately | Server reachable, default credentials rotated |
| **1 — Model** | Pick one bounded context; design hypernode/hyperedge types for it (relations, flavors, attribute schema) | Schema reviewed with the owning team |
| **2 — Load** | Bulk-import via REST/CLI; validate counts and a few hand-checked queries | Data present, spot-checked correct |
| **3 — Query** | Exercise HQL and SHQL against real questions the team actually asks; test PIT queries against known historical states | Query results match team's own manual answers |
| **4 — Agent wiring** | Point an MCP-compatible agent at `/mcp` with a scoped API key; exercise the write/read pattern from Slide 20 | Agent can assert and recall facts correctly |
| **5 — Review** | Revisit Slides 10–17 (security, ops, gaps) against your specific compliance/HA bar | Go/no-go decision made with eyes open on real gaps |

**Realistic timeline:** 2–4 weeks for phases 0–4 with one engineer,
assuming the bounded context is genuinely bounded.

---

## Slide 22 — Enterprise Readiness Checklist

# What To Bring to Your Own Architecture Review

| Requirement area | Status | Notes |
|---|---|---|
| Core CRUD + n-ary relationship modeling | ✅ Ready | Production-shape code; automated test coverage today is thin and concentrated on hyperkey generation and query-parsing/matching logic — REST API, auth, and RBAC paths have no test suite yet |
| Temporal (PIT) queries | ✅ Ready | Threaded through HQL, SHQL, and mesh |
| Federation across servers/teams | ✅ Ready | Concurrent fan-out, partial-failure tolerant |
| Multi-tenant isolation | ✅ Ready | Membership-gated, wildcard-permission leak specifically prevented |
| MCP agent integration | ✅ Ready | 25 tools, minus hyperedge update (Slide 9) |
| Role-based access control | 🔶 Partial | Roles exist; API-key auth bypasses them entirely (Slide 10) |
| Semantic inferencing | ❌ Not shipped | Roadmap item; data model present, engine not wired |
| Audit trail | ❌ Not shipped | Index defined, nothing writes to it |
| SSO / enterprise identity | ❌ Not shipped | JWT + API key only |
| HA / DR beyond MongoDB defaults | ❌ Not shipped | Standard `mongodump`/`mongorestore` only |
| Non-MongoDB backend | 🔶 Interface only | Registry pattern exists, one implementation |

Bring this table, not the marketing deck, to the review where someone
asks "what could go wrong."

---

## Slide 23 — Next Steps

# From Evaluation to Pilot

1. Clone the repo (MIT licensed) and run the Phase 0–2 steps from Slide 21
   against a throwaway dataset before involving a real team
2. Pick one bounded context with a clear owner and a query workload
   specific enough to validate against (Phase 1–3)
3. Loop in security/platform review early using Slides 10, 16, and 17 —
   surfacing the real gaps now is cheaper than discovering them in a
   production incident review later
4. If the pilot validates the model, professional-services engagement or
   in-house build-out are both viable paths — the platform doesn't require
   a vendor relationship to adopt

**Contact for architecture review / pilot support:** `[technical-contact-email]`
**Source (MIT licensed):** `[repository-url]`

*(Contact fields are placeholders — replace with real, verifiable
endpoints before this deck is shared externally.)*
