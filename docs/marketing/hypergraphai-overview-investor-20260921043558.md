---
title: "HypergraphAI — Semantic Knowledge Hypergraphs for the AI Era"
description: "Investor and press overview: concepts, implemented platform features for humans and AI agents, use cases, market analysis, competitors, revenue model, go-to-market and funding plan"
generated: "2026-09-21T04:35:58"
audience: "Investors, venture capital, technology media"
status: "Confidential draft — illustrative planning figures, see the Disclaimer slide"
---

# HypergraphAI
## The Semantic Knowledge Hypergraph for the Age of AI Agents

**Investor & press overview** · generated 2026-09-21

*One store of meaning, provenance and time — for people, for AI agents, and for every model vendor they use.*

**Format:** each `---` is one slide. Open this file in any Markdown slide tool (Marp, reveal-md, Slides import) or read it top to bottom. Tables and ASCII diagrams render in any Markdown viewer.

**Legend used throughout**

| Mark | Meaning |
|:-:|---|
| ✅ | **Live today** — implemented in this repository and exercised by its test suite or a live verification |
| 🛠️ | **Enabled by live features** — a pattern that works today using live building blocks, but is not a packaged product feature |
| 🗺️ | **Planned / roadmap** — designed, not built |

---

## Agenda

1. **The problem** — why AI agents need more than vectors, tables and binary graphs
2. **Concepts** — semantic knowledge hypergraphs in plain language
3. **The platform** — what HypergraphAI is and every major feature, for humans *and* agents
4. **Use cases** — enterprise store, semantic layer, analytics (human & agent), HgNexus chat, agent memory, and more
5. **Proof points** — what has actually been built and verified
6. **Market** — TAM · SAM · SOM, with sources and stated assumptions
7. **Competition** — where we win, where we don't yet
8. **Business model** — seven revenue streams
9. **Go-to-market & timeline**
10. **Financial plan & the ask**
11. **Risks, honest gaps, and press hooks**
12. **Appendix** — feature inventory, MCP tools, SHQL cheat sheet, glossary, sources

---

## 1. The Problem

# AI agents are only as good as the knowledge they can reach

Frontier models reason well, but the enterprise knowledge they are pointed at is stored in structures built for other eras:

| Store | Great at | Where agents get hurt |
|---|---|---|
| Relational tables | Rows, transactions | Relationships are implicit in joins; agents re-derive structure every time |
| Property graphs | Connections between **two** things | A real event ("a contract with a buyer, a seller, a witness and a jurisdiction") must be split into artificial pairs |
| Vector stores | "What is *similar*?" | No structure, no provenance, no notion of *how* things relate or *when* something was true |
| Chat history / memory layers | Recent conversation | Vendor-locked, session-bound, unstructured; gone when the session or the model changes |

**Consequence:** agents hallucinate relationships, cannot cite where a fact came from, forget across sessions, and cannot be audited.

> Gartner expects more than 40% of agentic AI projects to be cancelled by the end of 2027 — citing cost, unclear value and inadequate risk controls. Grounding, provenance and auditability are exactly the controls that are missing. *(source: Gartner, via Software Strategies Blog — see Sources)*

---

## 2. The Concept — Hypergraphs in One Slide

A normal graph edge joins **two** nodes. A **hyperedge** joins **any number**, is an object in its own right, and carries its own data.

```
  Property graph (binary edges)          Hypergraph (n-ary hyperedge)
  ─────────────────────────────          ───────────────────────────────────────────
  Alice ── signed ──▶ Contract           ┌─ hyperedge: rel:signed-contract ─────────┐
  Bob   ── signed ──▶ Contract           │ attributes: value=$2M, date=2026-03-01   │
  Carol ── witnessed ▶ Contract          │ valid_from / valid_to · provenance · tags │
  Contract ── in ──▶ Delaware            │                                          │
                                         │  Alice · Bob · Carol · Delaware          │
  4 edges, 1 invented "Contract" node,   └──────────────────────────────────────────┘
  facts scattered                        1 fact, 4 participants, one place
```

**In HypergraphAI a hyperedge is first-class:** it has its own `attributes`, `tags`, `status`, validity window, audit trail — and can itself be a member of another hyperedge (a fact *about* a fact).

Two flavors describe how the members relate: **hub** (one focal member, many spokes — a group and its members, an account and its transactions) and **symmetric** (all mutually equivalent — siblings, peers, accounts sharing a card). ✅

---

## 3. The Concept — "Semantic" Means the Rules Live in the Data

Relation meaning is not hard-coded. It is declared as ordinary hyperedges over *relation-type* nodes, using a small control vocabulary the inference engine understands: ✅

| Axiom hyperedge | Meaning | Example |
|---|---|---|
| `owl:inverse-of [R, R′]` | Every R fact implies the reverse R′ fact | `rel:initiated` ⇄ `rel:initiated-by` |
| `owl:symmetric [R]` | R holds both ways | `rel:shares-card-with` |
| `owl:transitive [R]` | Chains of R imply R | `rel:contains`: world → continent → country → city |
| `skos:broaderTransitive [narrow, broad]` / `skos:narrowerTransitive` | A relation hierarchy that projects facts upward | `shares-phone-with` ⊂ `shares-attribute-with` ⊂ `linked-to` |

Adding an inference rule is a **data change** (create a hyperedge), not a code deployment. Inferred facts are computed live at query time, flagged `_inferred: true`, and point to the axiom that licensed them — so every derived answer is explainable. ✅

---

## 4. The Concept — Time and Provenance

**Time.** Every hypernode and hyperedge can carry `valid_from` / `valid_to`. A query adds `at: "<instant>"` and gets the world **as it was** — "who was in the group in 1940?", "what did the org chart look like on March 1?". ✅

**Provenance.** Every record has an audit trail of who created or changed which fields and when, and records can carry their own `provenance` metadata (source file, row, method). In our reference dataset every one of 5.5 million records does. ✅

**Why it matters for AI:** an agent that can say *what* is true, *when* it was true, *who or what said so*, and *what was inferred rather than stored* is an agent a regulated business can actually deploy.

---

## 5. Benefits of Semantic Knowledge Hypergraphs in the AI Era

| Benefit | How | For people | For AI agents |
|---|---|---|---|
| **Grounded answers** | Structured, typed facts instead of similarity guesses | Trustworthy analysis | Fewer hallucinated relationships; can cite facts |
| **Faithful modelling** | One n-ary fact stays one fact | Models match how the business talks | No lossy pair-splitting to reason over |
| **Explainability** | Provenance + `_inferred` + axiom links + audit trail | Audit and compliance | Can answer "why did you conclude that?" |
| **Temporal correctness** | Validity windows + `at:` queries | Historical reporting | Time-aware reasoning |
| **Shared, vendor-neutral memory** | MCP + REST + files, any model | Knowledge survives tool and vendor changes | Same memory for every agent/model |
| **Governance** | RBAC and spaces on the REST API, note scopes, API keys, audit trail | Least-privilege access on the REST surfaces | Per-caller authorization for MCP/SHQL is 🗺️ (today: authentication only) |
| **Structured retrieval efficiency** | Query returns exactly the rows/edges needed | — | Less context stuffing per request *(qualitative; not yet benchmarked)* |
| **Federation** | Query several servers as one mesh | No ETL to a central lake | Cross-domain retrieval in one call |

---

## 6. What HypergraphAI Is

**A hybrid semantic hypergraph document platform**: knowledge-graph semantics + document-database flexibility + n-ary hyperedges + an AI-native interface. ✅

```
┌────────────────────────────────────────────────────────────────────────┐
│  People                              AI agents & tools                 │
│  Web UI · hgsh shell · HgNexus chat  Claude · GPT · Grok · Cursor · any  │
│                                      MCP client                        │
├──────────────────────────────────┬─────────────────────────────────────┤
│  REST API (FastAPI, OpenAPI docs)│  MCP server — 30 tools              │
├──────────────────────────────────┴─────────────────────────────────────┤
│  Core engine: SHQL query · inference · temporal · auth/RBAC · cache    │
│  Modules: SHQL · Mesh · MCP · AgentChat (HgNexus) · Storage            │
├────────────────────────────────────────────────────────────────────────┤
│  Pluggable storage abstraction ──▶ MongoDB backend (default)           │
└────────────────────────────────────────────────────────────────────────┘
```

MIT-licensed core; Python 3.11+, FastAPI, MongoDB 7; Docker Compose deployment. Roughly **26,000 lines** of source and **346 automated tests** at the time of writing.

---

## 7. Feature Map — Humans and Agents Use the Same Platform

Every capability is reachable both ways. ✅

| Capability | A human uses it to… | An AI agent uses it to… |
|---|---|---|
| Hypergraphs, hypernodes, hyperedges | Create/edit/browse knowledge in the Web UI or shell | Read/write knowledge with `hgai_hypernode_*`, `hgai_hyperedge_*` MCP tools |
| **SHQL** query language | Run and save queries in the Query screen | Run structured queries via `hgai_query_execute` / `hgai_query_validate` |
| **Semantic inference** | Toggle "show inferred edges", materialize with Project Inference | Call `hgai_infer_expand_edge`, `hgai_infer_check_transitive`; `infer: true` in SHQL |
| **Point-in-time** | Time-travel in Visualize and queries | Ask "as of" questions in SHQL |
| **Mesh federation** | Register servers, ping, sync, federate | `hgai_mesh_*` tools; dot-notation `mesh.server.space.graph` |
| **Spaces & RBAC** | Multi-tenant isolation, member roles (enforced on the REST API) | Authenticates with API key or JWT; per-caller authorization on MCP is 🗺️ |
| **Media** | Attach/embed files | `hgai_media_*` tools |
| **Notes** (Markdown, folders, 5 sharing scopes) | Write and share knowledge, audit records | Export chat turns to Notes; help topics as retrieval source |
| **Help** (40 built-in topics + `system:help` notes) | Search documentation | `help_search` / `help_get` tools inside HgNexus |
| **Import / export & seeds** | Move a graph between servers as one file | Bulk-load knowledge from generated export files |

---

## 8. Feature — The Data Model

**Hypernode** (entity) · **Hyperedge** (n-ary relationship) · **Hypergraph** (container) · **Space** (tenant namespace) · **Mesh** (federation of servers). ✅

| Element | Key fields |
|---|---|
| Hypernode | `id`, `label`, `type`, `description`, `attributes` (free-form JSON), `tags`, `status` (active/draft/archived), `valid_from/to`, `media` |
| Hyperedge | `relation`, `members[{node_id, seq}]`, `flavor` (hub/symmetric), `attributes`, `tags`, validity window, SHA-256 `hyperkey` for de-duplication |
| Hypergraph | `instantiated` (physical) or `logical` (composition of other graphs, local or remote) |
| Audit | `mutations[]` on every node/edge: who, when, which fields changed |

**Human:** forms, tag filters, sortable tables, media thumbnails. **Agent:** the same objects as JSON via REST/MCP.

Because `attributes` is a free-form document, adding a property never needs a schema migration; the ontology (types, relations, axioms) is itself data.

---

## 9. Feature — SHQL, One Query Language for Everything

**SHQL** (*"shekel"*) — a SPARQL-inspired, YAML-native pattern language: `?variable` bindings, implicit joins, multi-hop traversal, OPTIONAL, UNION, filters, aggregation, point-in-time and inference. ✅

A real query, run against our 3.6-million-node fraud demonstration graph (returns 20 rows; ~5 s):

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
    - ?txn.attributes.timestamp
    - ?txn.attributes.amount
    - ?txn.attributes.ip_risk_score
    - ?txn.attributes.velocity_1h
    - ?txn.attributes.amount_vs_avg_ratio
    - ?txn.attributes.is_fraud
  order_by:
    - ?txn.attributes.ip_risk_score desc
    - ?txn.attributes.amount_vs_avg_ratio desc
  limit: 20
```

**Human:** editor with examples, history, validation, cache toggle, and **parameterized queries** (typed `/$name:type:default$/` placeholders saved as reusable, shareable templates). **Agent:** `hgai_query_validate` then `hgai_query_execute`. YAML means an LLM can write and repair it reliably.

---

## 10. Feature — Inference You Can Audit

Inference runs live, never silently persisted, and every derived edge says where it came from. ✅

```yaml
# The `eden` demo graph stores only "Seth has children Enosh and Enoch".
shql:
  from: eden
  infer: true
  select:
    - ?ancestor.label
  where:
    - edge:
        relation: rel:parent
        members:
          - node_id: person:enoch
            seq: 0
          - node_id: ?ancestor_id
    - node:
        bind: ?ancestor
        id: ?ancestor_id
  distinct: true
# → Seth   (derived from rel:child via the owl:inverse-of axiom; flagged _inferred)
```

| | Human | Agent |
|---|---|---|
| Explore | Visualize → "Show inferred edges" | `hgai_infer_expand_edge` |
| Reachability | — | `hgai_infer_check_transitive` (path / closure / bool) |
| Persist | **Project Inference**: preview, then materialize inferred facts into a graph | via REST `POST /graphs/{id}/infer/project` |

---

## 11. Feature — Federation, Spaces and Security

**Mesh federation** ✅ — register several HypergraphAI servers; one SHQL query fans out concurrently and merges results; unreachable servers are skipped and reported. Dot-notation addresses graphs anywhere: `mesh.server.space.graph`.

**Multi-tenancy** ✅ — Spaces group graphs; space membership is the *sole* gate to a space's graphs (a `*` permission cannot leak across tenants). Space roles: owner / admin / member / viewer.

**Access control** ✅

| Layer | Mechanism |
|---|---|
| Accounts | Roles `admin`, `user`, `agent`, `readonly`; per-graph permissions |
| Authentication | JWT for people; primary + secondary API keys (zero-downtime rotation) for machines and MCP clients |
| Notes | Five scopes: `private`, `protected`, `protected-edit`, `public`, `public-edit`, plus per-account viewer/editor grants |
| AI vendor keys | Stored Fernet-encrypted at rest; only admins can manage vendors/models |
| Agent web access | SSRF-guarded fetch tool (private and internal addresses refused) |

**Human:** Accounts / Spaces / Meshes screens. **Agent:** authenticates with an API key or token. *Authorization is enforced on the REST CRUD/export/import/inference surfaces; the MCP and SHQL endpoints currently authenticate but do not yet apply per-graph permissions (🗺️) — see Honest Gaps.*

---

## 12. Feature — The Web UI (for People)

✅ A single-page app served by the platform itself — no separate front-end deployment.

| Screen | Purpose |
|---|---|
| Dashboard | Graph overview and counts |
| Hypergraphs / Hypernodes / Hyperedges | Full CRUD, tag filters, sort, media, **Export / Import** of a whole graph as one file |
| **Visualize** | Interactive 3D graph, point-in-time slider, orphan hiding, inferred edges |
| **Query (SHQL)** + **Parameterized Queries** | Editor, examples, history, saved templates |
| **Notes** | Markdown with tag-based virtual folders, YAML front-matter rendering, media embeds, five sharing scopes |
| **Help** | 40 built-in topics searchable by keyword/tag, plus team-authored `system:help` notes |
| Project Inference | Materialize inferred facts |
| Media | Upload and attach files |
| Admin: AI Agent, Spaces, Accounts, Meshes, System | Vendors/models/keys, tenants, users, federation, cache |

Resizable panels and persistent preferences.

---

## 13. Feature — MCP: The Agent Interface

✅ **30 MCP tools** turn every platform operation into something any MCP-capable model can call (authenticated with an API key or token).

| Area | Tools |
|---|---|
| Hypergraphs | list · get · stats · create |
| Hypernodes | list · get · create · update · delete |
| Hyperedges | list · get · create · delete |
| Query | execute · validate |
| Inference | expand edge · check transitive |
| Mesh | list · get · ping · sync · query |
| Media | upload · download · delete |
| Spaces | list · get · create · add member · list graphs |

**Why it matters commercially:** MCP is now vendor-neutral infrastructure — donated to the Linux Foundation's Agentic AI Foundation in Dec 2025 (co-founded by Anthropic, Block, OpenAI), with **10,000+ published servers** and ~**97M monthly SDK downloads** by March 2026. A knowledge platform that speaks MCP natively plugs into Claude, ChatGPT, Gemini, Copilot, Cursor and VS Code without custom connectors. *(sources: see Sources)*

---

## 14. Feature — HgNexus: Integrated AI Agent Chat

**HgNexus** is the platform's built-in agent chat — a collapsible, resizable panel beside every screen, powered by an agent framework and wired to the platform's own tools. ✅ *(implemented in the `hgai_module_agentchat` module)*

| Capability | Detail |
|---|---|
| **Multi-vendor, multi-model** | Admin-managed catalog: Anthropic, OpenAI, xAI (Grok); seeded small default catalog; bring-your-own API keys (encrypted); enable/disable per model |
| **Knows the platform** | Every turn is built with the platform's MCP tools, a help-topic search tool (permission-aware for note-backed topics), and a guarded web-fetch tool |
| **Session memory** | Multi-turn context stored server-side; restart any session later |
| **Prompt history** | Last 50 prompts per account, persisted across restarts, browsers and machines |
| **Save as Note** | Turn any prompt+answer into a Markdown Note with YAML front matter: prompt, vendor/model, start/stop, duration, tokens |
| **Streaming** | Token-by-token responses |

**Human:** ask questions about their data or about HypergraphAI itself. **Agent view:** the model is an MCP client of the platform, so the same tools an external agent uses are what HgNexus uses.

---

## 15. Use Case — Enterprise Semantic Knowledge Hypergraph Store

**Problem:** enterprise knowledge is fragmented across systems, expressed as pairs and rows, and unversioned.

**Solution:** HypergraphAI as the **system of record for meaning** — entities, n-ary relationships, ontology, provenance and history in one governed store.

| Need | HypergraphAI feature |
|---|---|
| Model real n-ary facts (contracts, incidents, org changes) | Hyperedges |
| Keep history, answer "as of" questions | Validity windows + `at:` |
| Separate business units | Spaces + RBAC |
| Trace every fact | Audit trail + `provenance` |
| Human curation + machine writes | UI/shell + MCP/REST |
| Portability and DR | One-file graph export/import; Mongo backups |

**Human:** stewards curate ontology and data in the UI. **Agent:** reads authoritative knowledge and *proposes* new facts (draft status → review → active).

**Status:** ✅ core store · 🗺️ enterprise hardening (SSO, HA packaging, SOC 2) in the plan.

---

## 16. Use Case — Enterprise Semantic Layer Across Systems

**Idea:** a *semantic layer* gives every system and every agent one shared vocabulary — entity types, relationships, business rules — over data that stays where it lives.

```
  CRM ──┐                                   ┌── BI / analysts
  ERP ──┤   ingest / map      HypergraphAI  ├── AI agents (MCP)
  Files ┼──▶ (connectors,  ─▶ semantic      ├── Apps (REST)
  Logs ─┤   import files)     layer + mesh  └── HgNexus chat
  APIs ─┘
```

| Layer capability | Live? |
|---|---|
| Shared ontology as data (types, relations, axioms) | ✅ |
| Federated query across servers/departments | ✅ mesh |
| Bulk ingestion via export/import files and scripts | ✅ |
| Packaged connectors (Salesforce, SAP, SharePoint, Snowflake…) | 🗺️ marketplace |
| Semantic-layer / data-fabric budgets (adjacent category ≈ $4.3B in 2026) | context for market sizing |

**Real evidence:** a generated ontology-plus-data load of two 1M-transaction fraud datasets (see *Proof Points*) — entities, relationships, SKOS schemes, provenance — completed in ~13 minutes.

---

## 17. Use Case — Analytics Platform for Human Analysts

**Scenario:** fraud, AML, threat or supply-chain analysts explore relationships that tables hide.

| Step | Feature |
|---|---|
| Explore the graph | Visualize (3D), tag and type filters |
| Ask precise questions | SHQL editor, examples, history, parameterized templates |
| See the network | Symmetric "shares-card/device/IP" hyperedges; ring membership; transitive linkage |
| Time-travel | `at:` queries, Visualize point-in-time |
| Explain findings | `_inferred` edges with axiom links; provenance rows back to the source file |
| Record the work | Notes with front matter, sharing scopes (private → public-edit) |
| Ask in natural language | HgNexus chat over the same data |

**Demonstration (synthetic data):** "probable fraud" query returns the 20 highest-risk transactions; of the 944 transactions the rule selects, 908 (96%) already carry the fraud label and 36 do not — those 36 are the analyst's review queue. (The rule is deliberately narrow; it is a demonstration of the workflow, not a tuned detector.)

---

## 18. Use Case — Analytics Platform for AI Agents via MCP

**Scenario:** an autonomous or copilot agent (in Claude Desktop, an IDE, a custom orchestrator) must answer and act using enterprise knowledge.

```
Agent ── MCP ──▶ hgai_hypergraph_list        discover what knowledge exists
                 hgai_query_validate         check the query it wrote
                 hgai_query_execute          retrieve exact facts
                 hgai_infer_expand_edge      ask what follows from a fact
                 hgai_hyperedge_create       write back a finding (with provenance)
```

| Agent need | How the platform answers |
|---|---|
| Discover the schema | List graphs, node types, relations, stats |
| Retrieve without hallucinating | Typed pattern queries, not similarity guesses |
| Multi-hop reasoning | Joins over shared variables; transitive closure; inference |
| Time-aware answers | `at:` |
| Safe autonomy | API-key/JWT authentication and a per-record audit trail today; **per-agent authorization and scoping over MCP is 🗺️** — until then, run agents against dedicated servers/graphs and isolate the endpoint |
| Multi-agent collaboration | One shared graph; every MCP write is audit-stamped (today as the generic `mcp-agent` — per-agent identity stamping is 🗺️; agents can record their own identity in `attributes.provenance`) |

**Status:** ✅ 30 tools, API-key/JWT authentication, audit trail. 🗺️ per-caller authorization on MCP, per-agent usage metering and rate limits.

---

## 19. Use Case — HgNexus: Integrated Chat with AI Vendors and Models

**Positioning:** the fastest path from "we have a knowledge graph" to "our people can talk to it" — without building an agent UI.

| Buyer concern | HgNexus answer |
|---|---|
| Vendor lock-in | Admin picks any enabled vendor/model; sessions and history live in *our* store |
| Cost and control | Bring-your-own keys (encrypted), per-model enable, token usage recorded per answer |
| Security | Web fetch is SSRF-guarded; vendor keys encrypted and never shown to non-admins; *data access through MCP is not yet permission-scoped per user (🗺️) — restrict who can use HgNexus* |
| Trust | Answers about HypergraphAI cite help-topic ids; answers about data come from queries |
| Knowledge capture | One click turns an answer into an audit-ready Note (vendor, model, timing, tokens) |
| Onboarding | Built-in Help library the agent can search |

**Human:** analysts and admins chat in the UI. **Agent perspective:** HgNexus is itself an MCP client, so anything an external agent can do, it can do for the user.

🗺️ Roadmap: per-session model switching, team-shared sessions, tool-call trace panel, usage dashboards.

---

## 20. Use Case — Transient Memory / Workspace for Agents

**Problem:** while servicing one request an agent produces intermediate hypotheses, partial results and plans — today held in a context window that truncates or vanishes.

**Pattern (🛠️ enabled by live features):** give each task a scratch hypergraph (or a tagged region of one):

| Need | Live building block |
|---|---|
| Hold intermediate entities and links | `hgai_hypernode_create`, `hgai_hyperedge_create` |
| Mark as provisional | `status: draft`, tags such as `session:<id>` |
| Time-box | `valid_to` on records |
| Query its own working set | SHQL with a tag filter — *and joins to durable knowledge* |
| Clean up | Delete by tag / drop the scratch graph |
| Hand off between agents | Same graph, audit trail on every write (agent identity in `provenance` today; per-agent stamping 🗺️) |

**Honest status:** all primitives are live; **automatic expiry and promotion** of working memory to durable memory are **not built** (🗺️) — today an application or scheduled job does it.

**Why better than a context window:** structured, queryable, shareable between agents, and joinable with the enterprise graph.

---

## 21. Use Case — Persisted Context Memory Across Vendors, Hosts, Models and Sessions

**The vendor-neutral memory idea:** context stored in the hypergraph belongs to the *customer*, not to a model vendor or a chat product.

| Memory tier | Lives in HypergraphAI as | Status |
|---|---|---|
| Working | Draft records / scratch graph | 🛠️ |
| Session | Tagged session records; HgNexus sessions stored server-side, restartable | ✅ (HgNexus) · 🛠️ (external agents) |
| Episodic | Past decisions/outcomes as hyperedges with validity time | 🛠️ |
| Semantic | Durable domain knowledge — the graph itself | ✅ |
| Procedural | Runbooks/constraints as nodes; help topics; Notes | ✅ / 🛠️ |

| Dimension | How persistence spans it |
|---|---|
| Across **vendors & models** | Any MCP/REST client reads the same memory — Claude today, another model tomorrow |
| Across **sessions** | Records outlive any chat; HgNexus prompt history (50/account) and sessions persist |
| Across **hosting** | Mesh federation + one-file export/import move or share memory between servers |
| Across **people & agents** | Note scopes and Spaces govern who sees which memory |

**Honest gap:** an HgNexus session is currently pinned to one model; switching models mid-session with automatic context hand-off is 🗺️. Cross-vendor continuity works today through the *shared graph*, not chat-transcript replay.

---

## 22. More Compelling Use Cases

| Use case | Why a hypergraph | Status |
|---|---|---|
| **Fraud, AML & threat investigation** | Rings, shared devices/cards/IPs, n-ary transactions, provenance for case files | ✅ demonstrated on synthetic data |
| **Regulatory audit & explainable AI** | Every fact and every inferred fact traceable; point-in-time reconstruction | ✅ primitives |
| **Contracts & legal knowledge** | Multi-party agreements as single hyperedges with dates | 🛠️ |
| **Supply-chain provenance** | Multi-party shipments, transformations, certifications over time | 🛠️ |
| **Life sciences / clinical** | Trials, cohorts, compounds, outcomes are inherently n-ary | 🛠️ |
| **Defense & intelligence analysis** | Federated, tenant-isolated, temporal, auditable | 🛠️ (business-development decks already produced in this repo) |
| **Customer / partner 360 & master data** | One entity graph across systems, with lineage | 🛠️ |
| **Agent skill & runbook registry** | Procedures as versioned, queryable, permissioned knowledge | 🛠️ |
| **Knowledge brokering** | Curated domain graphs (ontologies + facts + provenance) licensed to other organizations over the mesh | 🗺️ |

---

## 23. Proof Points — What Has Actually Been Built and Verified

| Evidence | Detail |
|---|---|
| **Working platform** | REST + MCP (30 tools) + Web UI + shell + agent chat; ~26k lines of source; **346 automated tests** |
| **Scale demonstration — "Alchemy" fraud graph** | Six CSV files (~300 MB, **2,000,000 transactions**, two synthetic datasets) transformed into **3,631,632 hypernodes** and **1,872,417 hyperedges** with a generated domain ontology, in ~**13 minutes** |
| **Provenance completeness** | 100% of nodes and edges carry `provenance`; 0 dangling references across 13.5M hyperedge member slots |
| **Fidelity** | 2,000 randomly sampled source rows compared with stored data: **0 mismatches**; source-file aggregates recomputed and reconciled exactly |
| **Ontology in action** | Transitive geography path, SKOS closures, inverse/symmetric/broaderTransitive derivations verified through the live API |
| **Portability** | One-file graph export/import; example graphs (`hello-world`, `eden`) ship as seed files |
| **Documentation** | 40 in-product help topics, API reference, module-development guide, four demo decks |

**Not claimed:** customers, revenue, third-party benchmarks, or production references. The Alchemy data is synthetic.

---

## 24. Market — Why Now

| Signal | Data point *(sources on the Sources slide)* |
|---|---|
| AI spending | Gartner forecasts worldwide AI spending to grow **49.5% in 2026** (press release dated 2026-09-16) |
| Agents | Gartner-derived estimates: agentic AI spending **~$202B in 2026 (+141%)**, overtaking chatbot spend by 2027; ~**40% of enterprise applications** to embed agents by end-2026 |
| The catch | **>40% of agentic AI projects** may be cancelled by end-2027 (cost, unclear value, weak risk controls) — a market for *grounding and governance* |
| MCP standardization | Donated to the Linux Foundation's Agentic AI Foundation (Dec 2025); **10,000+ servers**; **~97M monthly SDK downloads** (Mar 2026) |
| Knowledge graphs | ~**$1.9B (2026)** → **$8.9–9.9B by 2032**, CAGR ~29–32% (research-firm range) |
| Graph databases | ~**$3.6B (2026)** → **$20.3B by 2034**, CAGR ~24% |
| Agent memory infrastructure | ~**$1.2B (2025)** → ~**$8.4B by 2030** *(single-source estimate)* |

> **Thesis:** the AI wave is turning *knowledge infrastructure* — grounded, governed, shared memory — from a nice-to-have into a control point. MCP means it can be adopted without custom integration.

---

## 25. Market — Method and Definitions

Earlier internal decks used top-down, unsourced figures ("SAM $800M, TAM $8B+"). This deck **replaces them with a transparent, bottom-up model** you can change. Third-party market-research figures vary widely by provider; ranges are shown, not single "truths."

| Layer | Definition | 2030 estimate |
|---|---|---|
| **TAM** | Spend on platforms where a semantic knowledge / agent-memory store is the system of record | **≈ $6–14B** |
| **SAM** | The part reachable by an open-core, self-hosted-or-hosted semantic hypergraph with MCP: organizations running production agents that need a dedicated knowledge/memory store | **≈ $0.49B** (bottom-up) |
| **SOM** | What a focused company can obtain in 5 years | **≈ $28M ARR (~6% of SAM)** *(scenario)* |

The next slides derive each number. **Every assumption is labeled as an assumption.**

---

## 26. Market — TAM (Top-Down, With Sources)

| Component | 2030 value | Basis |
|---|---|---|
| Knowledge-graph platforms | **≈ $5.7B** | $1.9B (2026) grown at the widely cited 31.6% CAGR (MarketsandMarkets) |
| Agent-memory infrastructure | **≈ $8.4B** | Single-source forecast ($1.2B 2025 → $8.4B 2030) — treat as the *upper* case |
| Overlap between the two | Unquantified | Both describe structured stores for AI context; **not de-duplicated** |

**TAM ≈ $6B (knowledge graphs alone) to ≈ $14B (both, no overlap deducted).**

Adjacent context, *not* counted in TAM: data fabric ≈ $4.3B (2026) → $10.4B (2030); AI semantic layer ≈ $0.95B (2026); "agentic AI in semantic layer & knowledge graph" ≈ $1.07B (2026) → $3.2B (2031); AI agents software ≈ $7.8B (2025) → $52.6B (2030). Overall agent-related spend (Gartner: ~$202B in 2026) is a context signal, not addressable market.

---

## 27. Market — SAM (Bottom-Up, Assumptions Explicit)

| Step | Value | Nature |
|---|---:|---|
| Organizations with ≥1,000 employees worldwide | 60,000 | **Assumption** — validate with a commissioned market study |
| … with ≥1 agent in production by 2030 | 40% | **Assumption** (only ~31% of enterprises had one in production per Gartner-derived reporting in 2026) |
| … that need a dedicated semantic knowledge / memory store | 25% | **Assumption** |
| = Target organizations | **6,000** | |
| × Blended annual contract value (hosting + support + modules) | $75,000 | **Assumption** (illustrative pricing — see *Revenue Stream Detail — Hosting, Subscriptions and Support*) |
| **Enterprise SAM** | **≈ $450M** | |
| Developer / SMB long tail: 150,000 teams × 4% paid × $6,000 | ≈ $36M | **Assumption** |
| **Total SAM (2030)** | **≈ $0.49B** | |

*Sensitivity:* halve any one assumption and SAM falls ~50%; double the ACV and it roughly doubles. That is why we recommend commissioning an independent bottom-up study before a priced round.

---

## 28. Market — SOM and How We Would Win It

**SOM (5-year, illustrative scenario): ≈ $28M ARR ≈ 6% of the 2030 SAM.**

| Segment (ICP) | Why they buy first | Entry motion |
|---|---|---|
| **AI-forward enterprises with agents in pilot/production** (financial services, insurance lead adoption) | Need grounded, auditable memory; MCP makes adoption a config change | 30-day "connect your agent to structured knowledge" pilot |
| **Fraud / AML / risk / security teams** | Naturally n-ary, temporal, network-shaped problems; demonstrated | Vertical pack + services |
| **Regulated & public sector** | Provenance, tenant isolation, federation, self-hosting | Design partners, partner channel |
| **Agent builders and ISVs** | Need a memory/knowledge backend that isn't vendor-locked | Open-source core → hosted upgrade; marketplace |

**Beachhead logic:** land through one agent use case; expand via new hypergraphs per department; federate with the mesh; monetize modules and ontology packs.

---

## 29. Competitive Landscape — Categories

| Category | Representatives | What they do well | Where HypergraphAI differs |
|---|---|---|---|
| **Property-graph databases** | Neo4j (>$200M ARR as of Nov 2024; ~44% share of graph DBMS per a Cupole analysis cited by Neo4j), Amazon Neptune, TigerGraph, Memgraph | Scale, maturity, ecosystem, large customer bases | Binary edges; n-ary facts need reification. HypergraphAI models the fact once, adds temporal validity, axiom-driven inference and an agent interface in the box |
| **Semantic / RDF platforms** | Stardog (Bosch, Ericsson, BNY Mellon, NASA, NIH), Ontotext, TopQuadrant | Standards-based reasoning, enterprise semantic layers, LLM assistants (Voicebox) | Triple-based; heavier standards stack. HypergraphAI is document-flexible, YAML-native, AI-first, open-core |
| **Hypergraph / n-ary databases** | **TypeDB** (structured hypergraph with typed schema and n-ary relations) | Strong type system, schema-enforced modelling | Closest technical rival. HypergraphAI differentiates on document flexibility, federation mesh, built-in Notes/Help/chat, MCP-first delivery and marketplace strategy — *not* on n-ary support alone |
| **Agent-memory layers** | Mem0 ($24M raised Oct 2025), Zep/Graphiti (temporal KG), Letta ($10M seed), Cognee | Fast developer adoption, vector-first or agent-runtime memory | Mostly session/user memory. HypergraphAI is a governed enterprise knowledge store *plus* memory, with RBAC, spaces, federation, audit |
| **Vector databases** | Pinecone, Weaviate, others | Similarity retrieval at scale | Complementary today (no native vector search here — see gaps) |

---

## 30. Competitive Landscape — Positioning

```
                    structured, governed, explainable
                                  ▲
                                  │
        Stardog / RDF  ●          │          ● HypergraphAI  (target position)
                                  │            n-ary · temporal · axioms · MCP
         Neo4j / Neptune ●        │      ● TypeDB
                                  │
   ───────────────────────────────┼───────────────────────────────▶ AI-agent-native
   database-first                 │                                   (memory, tools, chat)
                                  │
        Vector DBs ●              │        ● Mem0 / Zep / Letta
                                  │
                    unstructured, similarity-first
```

**Where we intend to win:** the intersection — *governed enterprise semantic knowledge* **and** *agent-native delivery*.

**Where incumbents are stronger today:** scale proof points, ecosystems, certifications, sales reach, vector search, customer references. Our plan (Go-to-Market and Funding sections) is to compete on a **wedge** — n-ary + provenance + MCP + open-core — not head-on on raw scale.

*Positions are qualitative and based on public documentation reviewed 2026-09; verify before external publication.*

---

## 31. Differentiation — Why HypergraphAI, Concretely

| Differentiator | Evidence in the product |
|---|---|
| **N-ary facts are first-class** | Hub and symmetric hyperedges; edges can be members of edges |
| **Semantics as data** | Axiom hyperedges drive inverse / symmetric / transitive / SKOS inference — no code deployments |
| **Explainable inference** | Every derived edge names its source edge and axiom |
| **Time built in** | `valid_from/to` + `at:` across queries, visualization and mesh |
| **Provenance-first** | Audit trail on every record; `provenance` convention proven at 5.5M records |
| **AI-native by default** | 30 MCP tools + built-in multi-vendor chat (HgNexus) — same tools for people and agents |
| **Vendor-neutral memory** | Knowledge and history live in the customer's store, readable by any model |
| **Federation without ETL** | Mesh queries across servers; dot-notation graph addresses |
| **Open-core & modular** | MIT core; every subsystem is a module → marketplace foundation |
| **Operational simplicity** | One Docker Compose file; MongoDB; a UI, shell and API from day one |

---

## 32. Business Model — Seven Revenue Streams

| # | Stream | What is sold | Nature | Notes |
|---|---|---|---|---|
| 1 | **Managed hosting** | Single-/multi-tenant HypergraphAI instances with backup, monitoring, upgrades, SLA | Recurring | Core of the funding model |
| 2 | **Subscriptions** | Cloud tiers; enterprise editions with advanced modules (SSO, audit export, HA, advanced inference) | Recurring | Open-source core stays free (MIT) |
| 3 | **Marketplace** | Extension modules — first-party (HypergraphAI) and third-party | Take rate + first-party sales | Foundation exists (module architecture) |
| 4 | **Support** | Tiered SLAs, named engineers, upgrade assistance | Recurring, attach to 1–2 | Typically a % of subscription |
| 5 | **Professional services** | Ontology/schema design, migrations, agent integration, custom modules | Project | Land-and-expand wedge; high margin |
| 6 | **Knowledge brokering** | Curated, licensed domain knowledge (ontologies + facts + provenance) delivered over the mesh | Subscription / usage / rev-share | 🗺️ early concept |
| 7 | **Training & certification** | SHQL/MCP developer certification, admin training, partner enablement | Per seat / cohort | Builds the partner channel |

Vendor model costs are **pass-through**: customers bring their own AI-vendor keys (already how HgNexus works), so we do not resell tokens or carry model-cost risk.

---

## 33. Revenue Stream Detail — Hosting, Subscriptions and Support

| Tier *(illustrative)* | Who | Included | Price |
|---|---|---|---|
| **Community** | Developers, evaluators | Open-source core, self-hosted, community support | Free |
| **Cloud Starter** | Small teams, agent builders | Managed instance, backups, MCP endpoint, HgNexus chat (BYO keys) | ≈ $1.5K / month |
| **Cloud Team** | Departments | Higher capacity, spaces/RBAC, mesh, email support | ≈ $5K / month |
| **Cloud Enterprise** | Business-critical | Dedicated/single-tenant, SLA, SSO 🗺️, audit export 🗺️, priority support | ≈ $15K+ / month |
| **Self-hosted Enterprise** | Regulated / air-gapped | Enterprise modules, support, upgrade assistance | Annual subscription |
| **Support plans** | All paid | Business-hours → 24×7, named engineer options | Typically 15–20% of subscription |

*SSO and audit export are 🗺️ (not yet built).* Tier prices are the planning assumptions used in the funding model ($1.5K / $5K / $15K monthly tiers, blended); benchmark for context: Neo4j AuraDB lists $65 per GB-month (Professional) and $146 per GB-month (Business Critical), capacity-based.

---

## 34. Revenue Stream Detail — Marketplace

**Concept:** an app store for knowledge infrastructure, built on the existing module system (`hgai_module_<name>`; conditional mount; documented developer guide). ✅ foundation · 🗺️ marketplace itself

| Extension type | Examples | Publisher |
|---|---|---|
| **Connectors** | Salesforce, SAP, SharePoint, Snowflake, Kafka, S3 → hypergraph | HypergraphAI + partners |
| **Domain ontology packs** | Fraud/AML, KYC, supply chain, clinical, cyber-threat | Partners, HypergraphAI |
| **Inference packs** | Domain rule sets expressed as axioms | Partners |
| **MCP tool & agent-skill packs** | Ready-made agent workflows on top of the graph | Partners, community |
| **Storage backends** | Alternative to MongoDB (interface already abstract) | Community, HypergraphAI |
| **UI modules** | Dashboards, vertical workbenches | Partners |

| Economics *(assumptions)* | |
|---|---|
| Platform take rate on third-party modules | 20–30% (app-store norm) |
| First-party premium modules | Sold directly, bundled into Enterprise tiers |
| Needed to launch | Packaging/signing, listing & review, licensing, billing/metering, publisher SDK & docs |

Network effect: more modules → more reasons to standardize on the platform → more publishers.

---

## 35. Revenue Stream Detail — Services, Training and Knowledge Brokering

**Professional services** — the wedge into large accounts (and the source of reusable ontology/connector IP):

| Offering | Typical scope | Illustrative price |
|---|---|---|
| Agent-grounding pilot | 30 days: MCP connect, seed ontology, first use case | $40–75K |
| Ontology & schema design | Domain modelling, axioms, provenance conventions | $50–150K |
| Data migration / integration | RDBMS/graph/CSV → hypergraph pipelines (our generator pattern: 2M records in minutes) | $50–150K |
| Custom module development | Bespoke connectors, relation types, MCP tools | $50–200K |

*(The funding model conservatively assumes only ~$280K of cumulative services revenue in the first 24 months.)*

**Training & certification:** SHQL/MCP developer, administrator, partner-implementer tracks; $500–5,000 per seat/cohort.

**Knowledge brokering (🗺️):** publishers list curated hypergraphs (ontology + facts + provenance); subscribers federate them over the mesh under space-level access control; the platform takes a share. Live primitives: meshes, spaces, one-file export/import, provenance convention. Not built: catalog, licensing, metering, payouts.

---

## 36. Unit Economics and Revenue Scenario

**Funding-model ramp (illustrative, from the planning document):**

| Month | Hosting customers | Blended MRR |
|---:|---:|---:|
| 7 | 1 (alpha, discounted) | ~$0.5K |
| 13 (GA) | 3 | ~$9K |
| 18 | 12 | ~$60K |
| 24 | 30 | ~$180K (≈ $2.16M annualized) |

Cumulative revenue (all streams, illustrative): **~$65K at 12 months · ~$410K at 18 · ~$1.44M at 24**.

**Five-year exit-ARR scenario (extension of the same assumptions — a scenario, not a forecast):**

| Year | Exit ARR | Note |
|---:|---:|---|
| 1 | ~$0.1M | Alpha customers, discounted |
| 2 | ~$2.2M | GA + first channel partners |
| 3 | ~$6M | Marketplace v1, vertical packs |
| 4 | ~$14M | Partner channel, regional hosting |
| 5 | ~$28M | ≈ 6% of 2030 SAM |

**Year-5 mix:** hosting & subscriptions 60% ($16.8M) · support 12% ($3.4M) · professional services 12% ($3.4M) · marketplace net 10% ($2.8M) · training 3% ($0.8M) · knowledge brokering 3% ($0.8M).

---

## 37. Go-to-Market — Three Motions

Built on the open-core split in the funding plan: **hgx (HypergraphX)** open-source core + **HypergraphAI** commercial module and hosting.

| Motion | Goal | Tactics |
|---|---|---|
| **1. Product-led adoption** (open source) | Developers and agent builders self-serve | GitHub, MCP registries/directories, quick-start in minutes, demo decks and datasets, community |
| **2. Direct commercial** (hosting) | Convert highest-intent users; land design partners | 30-day agent-grounding pilot; discounted alpha for case-study rights; GA with public pricing |
| **3. Partner & training channel** | Scale without a large direct sales team | Certification, SI/reseller track, ISV/OEM embedding, marketplace publishers |

**Assets already built:** four demo decks (agent memory engine, engineering-org demo, defense business-development, special-operations), a ready-to-run fraud-analysis dataset, seed graphs, in-product Help, API docs.

---

## 38. Go-to-Market — Phases and Timeline

*Month 0 = September 2026 (from the planning document; shift if kickoff moves).*

| Phase | Months | Milestones |
|---|---|---|
| **Build & Launch** | 0–3 (Sep–Dec 2026) | Team ramp; **hgx v0.1 (OSS) + HypergraphAI v0.1** release; docs, demos; MCP directory listings |
| **Alpha** | 6–9 (Mar–Jun 2027) | **1–3 design-partner hosting customers**; first certification cohort; case studies; SOC 2 readiness begins |
| **General availability** | 12–15 (Sep–Dec 2027) | **GA of commercial hosting**, public pricing, self-serve + sales-assisted; Series A conversations from month 14–15 |
| **Platform** *(proposed)* | 15–24 | Marketplace v1 with publisher SDK; first vertical packs (fraud/AML, cyber, life sciences); partner program; OEM pilots |
| **Scale** *(proposed)* | 24–36 | Regional hosting, HA/SSO, knowledge-brokering pilot, Series B readiness |

**Leading indicators we will report:** GitHub stars/forks, MCP-directory installs, pilots started, pilot→paid conversion, hosted instances, net revenue retention, modules published, partner-sourced pipeline.

---

## 39. Go-to-Market — Sales Motion and Channels

| Element | Plan |
|---|---|
| **Wedge offer** | "Connect your agent to governed, structured knowledge in 30 days" — fixed-scope pilot |
| **Buyers** | Head of AI/agents platform, data/analytics leaders, fraud/risk/security leaders, CISO/GRC (auditability) |
| **Land** | One use case, one hypergraph, one space |
| **Expand** | New hypergraph per department; mesh across them; modules and ontology packs |
| **Channels** | Direct (early); SIs and boutique data/AI consultancies (certified); ISVs/OEMs embedding the store; marketplace publishers |
| **Proof assets** | Reference dataset + query gallery; demo decks; benchmark and reference-architecture papers *(🗺️)* |
| **Pricing** | Free core → $1.5K / $5K / $15K+ monthly cloud tiers → enterprise annual |
| **Objection handling** | *Scale?* federation + roadmap for sharding; *Security?* REST-level RBAC and audit today, MCP/SHQL per-caller authorization and SOC 2 planned; *Vectors?* complementary, integration on roadmap |

---

## 40. Traction — Honest Status

| | |
|---|---|
| **Stage** | Pre-revenue, pre-launch. Working platform and demonstrations. |
| **Built** | Core engine, SHQL, inference, mesh, MCP (30 tools), Web UI, shell, HgNexus chat, Notes/Help, import/export, seeds, generator tooling |
| **Engineering signals** | ~26k lines of source; 346 tests; one-command Docker deployment |
| **Demonstrated** | 3.6M-node / 1.9M-edge fraud graph generated with 100% provenance and zero fidelity mismatches |
| **Not yet** | Paying customers, published benchmarks, SOC 2, marketplace, billing, packaged connectors |

> We would rather show investors exactly what exists than a polished claim of "production-ready". The plan funds the distance between the two.

---

## 41. Honest Gaps and How the Plan Addresses Them

| Gap today | Impact | Plan |
|---|---|---|
| **No native vector / embedding search** | Similarity retrieval must be paired with a vector store | Embeddings-as-attributes + hybrid retrieval module (🗺️) |
| **Scale envelope** | Verified to ~5.5M records for storage and targeted queries; SHQL `infer: true` considers a bounded candidate set per pattern and whole-graph export loads in memory | Streaming export, indexed/incremental inference, sharded storage backend (🗺️) |
| **Single storage backend** | MongoDB only (interface is pluggable) | Additional backends via marketplace |
| **Authorization on MCP / SHQL** | Both authenticate callers but do not apply per-graph or per-space permissions; an API key is a full-admin credential | Enforce `can_access_graph` / `can_perform` per caller in both paths (small, well-bounded change; first engineering item) |
| **Enterprise packaging** | No SSO/SAML, HA reference architecture, or SOC 2 yet | Funded in seed plan (security/compliance line from month ~10) |
| **HgNexus sessions pinned to one model** | No mid-session model switch | Session hand-off feature (🗺️) |
| **Memory lifecycle automation** | Expiry / promotion of working memory is application-side | Lifecycle policies module (🗺️) |
| **No marketplace / billing yet** | Extension revenue starts after v1 | Months 15–24 |
| **Team & references** | Pre-revenue; hiring plan in *Team and Company Structure* | Seed round |

---

## 42. Risks and Mitigations

| Risk | Why it matters | Mitigation |
|---|---|---|
| **Category creation** | "Semantic hypergraph for agents" is new; buyers use existing labels | Position on outcomes (grounded, auditable agent memory); MCP as adoption vector; vertical packs |
| **Agentic-AI disappointment** | Gartner: >40% of agentic projects may be cancelled by 2027 | Sell governance and grounding — the antidote — not agent hype |
| **Incumbent response** | Graph vendors are adding GenAI/agent features; TypeDB is a close technical peer | Wedge on provenance + temporal + federation + open-core + speed of iteration; do not fight on raw scale |
| **MCP/standards shifts** | Protocol details may change | REST + files remain first-class; MCP is governed by the Linux Foundation |
| **Scale/performance perception** | Enterprises need proof at their size | Publish benchmarks; sharded backend roadmap; mesh for horizontal scale-out |
| **Open-core monetization** | Free core can cannibalize | Monetize operations (hosting/support), enterprise modules, marketplace, services |
| **Execution / hiring** | 10-person plan | Milestone-gated hiring; fractional CFO option extends runway |
| **Assumption risk** | Market and revenue figures are models | Commission independent market study; refresh quarterly |

---

## 43. Team and Company Structure

*Founders' biographies to be added by the company before external distribution.*

**Planned team (10 roles, fully ramped by month 3):** CEO · CTO / Chief Scientist · Tech Lead · 4 developers · CPO / Sales / BD · COO / CFO (fractional option) · Admin / Ops.

**Company structure recommendation (from the funding plan):** Delaware C-Corp (standard, QSBS-eligible), with a Delaware **Public Benefit Corporation** as an equally fundable alternative given the open-source stewardship and responsible-AI framing. LLC/S-Corp/LLP ruled out for a VC-backed product company.

**Governance ideas for an open-core company:** charter-level commitment to keep the core open source; contributor license and trademark policy; clear boundary between OSS core and commercial modules.

---

## 44. The Ask — Seed Round

**Raise: $3.0M seed** *(planning recommendation; not an offer)*

| | Conservative | **Recommended** | Aggressive |
|---|---:|---:|---:|
| Pre-money | $9M | **$11M** | $15M |
| Post-money | $12M | **$14M** | $18M |
| New-investor ownership | 25.0% | **≈ 21.4%** | ≈ 16.7% |

Context: AI seed medians reported in 2026 are far higher, but they are dominated by foundation-model and hype-cycle companies; the plan recommends pricing conservatively for a pre-revenue infrastructure company to protect the Series A.

**Use of funds (≈ 17-month runway, burn-only):**

| Category | Amount | Share |
|---|---:|---:|
| Engineering (CTO, tech lead, 4 developers) | ≈ $1.63M | ≈ 54% |
| CEO / leadership | ≈ $0.29M | ≈ 10% |
| Sales / BD | ≈ $0.28M | ≈ 9% |
| Finance, ops, admin (COO/CFO, admin) | ≈ $0.41M | ≈ 14% |
| Infrastructure, security/compliance (SOC 2 readiness), legal, marketing, insurance | ≈ $0.40M | ≈ 13% |

---

## 45. What the Seed Round Buys — Milestones

| By month | Milestone | Investor-visible proof |
|---:|---|---|
| 3 | hgx v0.1 (OSS) + HypergraphAI v0.1 released | Public repo, docs, demos |
| 6–9 | 1–3 alpha hosting customers; first training cohort | Design-partner agreements, case studies |
| 12–15 | **GA** of managed hosting; public pricing | Paying customers, MRR curve |
| 14–15 | Series A process starts | Pipeline, retention, OSS adoption metrics |
| 17 | Burn-only runway ends (≈ $3.0M cumulative spend) | Series A closed or bridged |

**Cumulative spend (planning model):** $380K @ 3 mo · $923K @ 6 · $1.47M @ 9 · $2.04M @ 12 · $3.22M @ 18 · $4.42M @ 24.
**Projected funding path:** Seed $3M → Series A $10–15M (month ~15–20, gated on GA + MRR growth + OSS metrics) → Series B $25–40M (month ~30–36). *Placeholders, re-derived from real traction.*

---

## 46. Why This Is Investable

1. **A structural insight, already implemented:** n-ary, semantic, temporal, provenance-first knowledge — running code, not a slide.
2. **Riding a standard, not fighting one:** MCP is now Linux-Foundation-governed and adopted by every major AI vendor.
3. **Control-point economics:** knowledge and memory that persists across models and vendors is sticky infrastructure — customers own it, so it becomes the system of record for their agents.
4. **Open-core distribution + multiple monetization layers:** hosting, subscriptions, marketplace, support, services, training, brokering.
5. **Capital-efficient proof:** a 10-person plan, ~17 months of runway, GA inside it.
6. **Honest engineering culture:** verified claims, stated limits, reconciled data.

> *Potential outcomes are uncertain; this is not a promise of returns.*

---

## 47. Story Angles for Technology Media

| Angle | One-line pitch | Supporting fact |
|---|---|---|
| **"Agents need memory that outlives the model"** | Your agent's knowledge shouldn't be locked to one chatbot vendor | MCP + vendor-neutral store; HgNexus multi-vendor chat |
| **"Why AI hallucinates relationships — and a fix"** | Facts with more than two participants get mangled by pair-based graphs | Hyperedges, provenance, inferred-vs-stored labels |
| **"Time travel for enterprise knowledge"** | Ask what was true on any date | Point-in-time queries |
| **"Two million transactions to a knowledge graph in 13 minutes — with receipts"** | Every record traceable to a CSV line | Alchemy generation with 0 mismatches in sampled rows |
| **"Open-core knowledge infrastructure for the agent era"** | MIT-licensed core, marketplace to follow | Module architecture; MCP standard |
| **"Explainable AI, literally"** | Every conclusion links to its axiom and source | `_inferred` + `_axiom` metadata |

**Demo you can run in five minutes:** start Docker Compose → `python scripts/seed_data.py` → open the Web UI → run a SHQL query → chat with HgNexus.

---

## 48. Summary

- **Concept:** semantic knowledge hypergraphs represent real-world n-ary facts, meaning, time and provenance — the grounding AI agents lack.
- **Platform:** a working, open-core system — SHQL, inference, temporal, mesh, Spaces/RBAC, 30 MCP tools, Web UI, shell, and **HgNexus** multi-vendor agent chat — usable by people and agents alike.
- **Use cases:** enterprise knowledge store · semantic layer · analyst analytics · agent analytics over MCP · integrated chat · agent working memory · persisted cross-vendor memory · fraud/AML, audit, contracts, supply chain, life sciences, defense.
- **Market:** TAM ≈ $6–14B · SAM ≈ $0.49B · SOM ≈ $28M ARR by year 5 (scenario) — with explicit assumptions.
- **Model:** hosting · subscriptions · marketplace · support · services · training · knowledge brokering.
- **Plan:** OSS + module v0.1 at month 3 → alpha month 6–9 → GA month 12–15 → Series A from month 14–15.
- **Ask:** $3.0M seed to reach GA with ≈ 17 months of runway.

**HypergraphAI — where meaning, memory and provenance live for the intelligent enterprise.**

---

## Disclaimer

This document is a **confidential planning and marketing draft**, not an offer to sell or a solicitation to buy securities, and not investment, legal, tax or accounting advice.

- Product statements marked ✅ describe functionality present in this repository at the generation date; 🛠️ and 🗺️ items are not shipped features.
- Financial figures, valuations, pricing, adoption and revenue projections are **illustrative estimates** based on stated assumptions from the company's internal planning document and this deck's own model. They are not forecasts or commitments.
- Third-party market data comes from cited public sources retrieved 2026-09-21; research firms disagree materially, several are vendor press releases, and one cited figure (agent-memory infrastructure) is a single-source estimate.
- Competitor descriptions are qualitative, from public materials, and should be re-verified before external publication.
- The "Alchemy" fraud dataset is **synthetic**; no real customer data is represented.
- Founders' biographies and any customer/partner references must be added and approved by the company before distribution.

---

# Appendix

---

## A1. Feature Inventory (Implemented) — for Diligence

| Area | Feature | Status |
|---|---|---|
| Core | Hypernodes, hyperedges (hub/symmetric), hypergraphs (instantiated/logical), tags, status, free-form attributes, validity windows, audit trail, SHA-256 hyperkeys | ✅ |
| Query | SHQL: patterns, joins, OPTIONAL, UNION, filters, order/limit/offset/distinct, aggregate, `at:` PIT, multi-graph `from:`, result cache with graph-scoped invalidation | ✅ |
| Inference | inverse-of, symmetric, transitive, skos broader/narrowerTransitive; expand edge; transitive closure/path; project-to-graph | ✅ |
| Federation | Mesh registry, concurrent fan-out, dot-notation, ping/sync/query | ✅ |
| Tenancy & security | Spaces (4 roles), accounts (4 roles), JWT, dual API keys, encrypted vendor keys, SSRF-guarded fetch | ✅ |
| Interfaces | REST (OpenAPI), MCP (30 tools), Web UI, hgsh shell | ✅ |
| Knowledge work | Notes (Markdown, tag folders, front matter, media embeds, 5 scopes + grants), Parameterized Queries, Media library, Help (40 topics) | ✅ |
| Visual | Interactive 3D Visualize with PIT and inference toggle | ✅ |
| AI chat (HgNexus) | Multi-vendor/model catalog, MCP-aware agent, help tool, web tool, sessions, prompt history, Save-as-Note, streaming | ✅ |
| Data movement | One-file export/import (YAML/JSON), seed loader, generator + verifier pattern | ✅ |
| Extensibility | Pluggable modules; pluggable storage interface (MongoDB implemented) | ✅ |
| Ops | Docker/Compose, health endpoint, indexes at startup, cache | ✅ |
| Marketplace, billing/metering, SSO, HA/sharding, vector search, memory lifecycle automation, session model hand-off | — | 🗺️ |

---

## A2. The 30 MCP Tools

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

Client configuration is one JSON block (`url` + `Authorization: Bearer <key>`); a machine-to-machine API key needs no login step.

---

## A3. SHQL Cheat Sheet

```yaml
shql:
  from: hello-world            # graph, "space/graph", a list, or mesh.server.graph
  at: "1940-06-01T00:00:00Z"   # point-in-time (optional)
  infer: true                  # axiom-driven inference (optional)
  where:
    - edge:                    # hyperedge pattern
        bind: ?e
        relation: rel:member
        members:
          - node_id: group:three-stooges
          - node_id: ?person_id    # bind a member's id ...
    - node:                    # ... then join to its node to constrain it
        bind: ?person
        id: ?person_id
        type: Person
    - filter: "CONTAINS(?person.description, 'Howard')"
  select:                      # write ?variables in block style, never inside { } or [ ]
    - ?person.id
    - ?person.label
  order_by: ?person.label
  limit: 20
```

Result of the example on the `hello-world` seed: `Moe` and `Curly` — the two Howards in the lineup valid on 1940-06-01. Member patterns match by `id`/`node_id`, `seq` and `bind`; constrain a member's own properties via the join shown.

---

## A4. Architecture and Deployment

```
Browser / hgsh / MCP client / REST client
              │
   ┌──────────▼───────────┐
   │ FastAPI app           │   static UI · /api/v1 · /mcp · /api/docs
   │  modules: shql, mesh, │
   │  mcp, agentchat       │
   └──────────┬───────────┘
              │ StorageBackend interface
   ┌──────────▼───────────┐
   │ MongoDB (7+)          │   hypergraphs · hypernodes · hyperedges · notes · media ·
   └──────────────────────┘   accounts · meshes · query cache · agent chat collections
```

- **Deploy:** `docker-compose up -d` (server + MongoDB); or `./hgai.sh` locally.
- **Load examples:** `python scripts/seed_data.py`.
- **Configure:** environment variables (`HGAI_*`): storage, secrets, ports, cache, server identity, help directory.
- **Scale-out:** multiple servers federated as a mesh; storage interface prepared for additional backends.
- **Extend:** drop-in `hgai_module_<name>` packages.

---

## A5. Security and Governance Summary

| Control | Implementation |
|---|---|
| Authentication | JWT (interactive), API keys with rotation (machines/agents) |
| Authorization | Global roles + per-graph permissions + space membership; space membership is the sole gate for space graphs — **enforced on REST CRUD, export/import and inference; not yet on SHQL query or MCP tools** |
| Data segregation | Spaces; Note scopes and per-account grants |
| Secrets | AI vendor keys encrypted at rest (Fernet, keyed from the server secret); admin-only management |
| Agent safety | Web-fetch refuses private/internal addresses; help tool is permission-aware. **MCP tools and SHQL do not yet apply per-graph permissions (authentication only)** |
| Audit | Per-record mutation history; provenance metadata; export of audit Notes |
| Planned | SSO/SAML, SOC 2, audit-log export, rate limiting/metering |

---

## A6. Glossary (for a General Audience)

| Term | Plain-language meaning |
|---|---|
| **Knowledge graph** | A database of things and the relationships between them |
| **Hypergraph / hyperedge** | A graph whose relationships can link *many* things at once, not just two |
| **Ontology** | The agreed vocabulary of a domain: kinds of things, kinds of relationships, and rules |
| **SKOS** | A standard way to organize concepts into broader/narrower hierarchies |
| **OWL axioms** | Rules such as "X is the inverse of Y" or "this relation is transitive" |
| **Inference** | Deriving facts that were never stored, from stored facts plus rules |
| **Point-in-time query** | A query answered *as of* a chosen date |
| **Provenance** | A record of where a fact came from and how it was produced |
| **MCP (Model Context Protocol)** | An open standard that lets AI models call tools and read data |
| **Agent memory** | Information an AI agent keeps beyond one prompt: working, session, episodic, semantic, procedural |
| **Semantic layer** | A shared business vocabulary over many data systems |
| **Open-core** | A free, open-source foundation with paid hosting, support and extensions |
| **GraphRAG** | Retrieval-augmented generation that retrieves from a knowledge graph rather than only text chunks |
| **TAM / SAM / SOM** | Total / serviceable / obtainable market |

---

## A7. Sources (retrieved 2026-09-21 unless noted)

**Market and adoption**
- [Knowledge Graph Market surges to $9.88B by 2032, 31.6% CAGR — MarketsandMarkets via GlobeNewswire](https://www.globenewswire.com/news-release/2026/06/29/3319085/0/en/knowledge-graph-market-surges-to-9-88-billion-at-a-cagr-31-6-by-2032-report-by-marketsandmarkets.html)
- [Knowledge Graph Market — Global Forecast 2026–2032, Research and Markets](https://www.researchandmarkets.com/reports/5924736/knowledge-graph-market-global-forecast)
- [Graph Database Market Size, Share, Industry Report 2034 — Fortune Business Insights](https://www.fortunebusinessinsights.com/graph-database-market-105916)
- [AI Agents Market Report 2025–2030 — MarketsandMarkets](https://www.marketsandmarkets.com/Market-Reports/ai-agents-market-15761548.html)
- [Agentic AI Orchestration and Memory Systems Market — Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/agentic-artificial-intelligence-orchestration-and-memory-systems-market)
- [AI Agent Memory Systems Infrastructure Market Research Report 2034 — Marketintelo](https://marketintelo.com/report/ai-agent-memory-systems-infrastructure-market) *(single-source estimate)*
- [Agentic AI in Semantic Layer and Knowledge Graph Market — Mordor Intelligence](https://www.mordorintelligence.com/industry-reports/agentic-artificial-intelligence-in-semantic-layer-and-knowledge-graph-market)
- [AI Semantic Layer Market Outlook 2026–2034 — Intel Market Research](https://www.intelmarketresearch.com/ai-semantic-layer-market-46980)
- [Data Fabric Market Report 2026 — Research and Markets](https://www.researchandmarkets.com/reports/5767222/data-fabric-market-report)
- [Gartner Forecasts Worldwide AI Spending to Grow 49.5% in 2026 (2026-09-16)](https://www.gartner.com/en/newsroom/press-releases/2026-09-16-gartner-forecasts-worldwide-ai-spending-to-grow-49-point-5-percent-in-2026)
- [Roundup of agentic AI forecasts and market estimates, 2026 — Software Strategies Blog (citing Gartner)](https://softwarestrategiesblog.com/2026/02/26/roundup-of-agentic-ai-forecasts-and-market-estimates-2026/)
- [AI Agent Adoption 2026: What the Analysts' Data Shows — Joget (Gartner, IDC)](https://joget.com/ai-agent-adoption-in-2026-what-the-analysts-data-shows/)

**MCP**
- [Linux Foundation announces the Agentic AI Foundation (AAIF), anchored by MCP](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)
- [MCP Adoption Statistics 2026 — Digital Applied](https://www.digitalapplied.com/blog/mcp-adoption-statistics-2026-model-context-protocol)

**Competitors**
- [Neo4j surpasses $200M in revenue — Neo4j press release](https://neo4j.com/press-releases/neo4j-revenue-milestone-2024/)
- [Neo4j pricing 2026 — Vendr](https://www.vendr.com/marketplace/neo4j)
- [TypeDB — structured hypergraph](https://typedb.com/blog/the-case-for-a-structured-hypergraph)
- [Stardog — knowledge-graph-powered semantic layer](https://www.stardog.com/)
- [AI Agent Memory 2026 — Comparing Mem0, Zep, Graphiti, Letta (survey)](https://medium.com/@wasowski.jarek/i-compared-5-ai-agent-memory-systems-across-6-dimensions-none-wins-6a658335ed0a)
- [AI Memory: how startups solve persistent context — Value Add VC (Mem0, Letta funding)](https://valueaddvc.com/blog/the-ai-memory-problem-how-startups-are-solving-for-persistent-context)

**Internal (this repository)**
- `README.md`, `docs/api-reference.md`, `docs/module-development.md`, `docs/help/notes/` (in-product Help)
- `docs/operations/timeline-funding-20260817.md` — funding, staffing, timeline and revenue-ramp assumptions
- `docs/decks/demo-ai-context-memory-20260817/` — agent-memory tiers and lifecycle
- `.project/prompts/mutations/mutation_20260920123049_alchemy_cyber_fraud_hypergraph/` and the generation Note — Alchemy dataset generation and verification record
