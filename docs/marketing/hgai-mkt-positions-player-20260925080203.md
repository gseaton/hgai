---
title: "HypergraphAI — Market Positions Where HypergraphAI Is a Player"
description: "Investor and executive deck: platform overview, three market positions (Universal AI Infrastructure, Enterprise Semantics, Knowledge Analytics) with implementations, TAM/SAM/SOM per market, and aggregate roll-ups"
generated: "2026-09-25T08:02:03"
audience: "Angel investors, venture capital investors, senior technical executives"
status: "Confidential draft — desk-research planning estimates, see the Disclaimer slide"
---

# HypergraphAI
## Market Positions Where HypergraphAI Is a Player

**Universal AI Infrastructure · Universal AI Enterprise Semantics · Universal AI Knowledge Analytics**

*One semantic hypergraph platform — memory, meaning and analytics — for people, AI agents and every model vendor they use.*

**Audience:** angel and VC investors, senior technical executives
**Format:** each `---` is one slide (Marp / reveal-md / any Markdown viewer) · generated 2026-09-25

**Legend**

| Mark | Meaning |
|:-:|---|
| ✅ | **Live today** — implemented in the repository and covered by its automated tests |
| 🛠️ | **Enabled by live features** — works today by composing live building blocks; not a packaged feature |
| 🗺️ | **Planned / roadmap** — designed, not built |

---

## Executive Summary

**HypergraphAI is a semantic hypergraph knowledge platform** — n-ary relationships, semantics-as-data, time and provenance built in, with an AI-native (MCP) interface. It plays in **three market positions**, seven concrete implementations:

| Market position | Implementations | Net TAM (base, 2030) | Net SAM (base) | Net SOM (base, yr 5) |
|---|---|---:|---:|---:|
| **1. Universal AI Infrastructure** | Universal context memory · Universal agentic knowledge store (persistent, transient/per-job) | $6.9B | $560M | $30.0M |
| **2. Universal AI Enterprise Semantics** | Universal enterprise semantic layer · Universal semantic knowledge store | $5.4B | $185M | $2.1M |
| **3. Universal AI Knowledge Analytics** | AI analytics agents (interactive / real-time) · Interactive / real-time UI analytics | $4.3B | $55M | $0.3M |
| Adjacent markets (16 further use cases) | Verticals, horizontal stores, first-of-kind spaces | $11.3B | $437M | $4.3M |
| **Aggregate (de-duplicated)** | 24 sized use cases | **$28.0B** | **$1.2B** | **$36.7M** |

- **Range across scenarios:** net TAM $16.0B–$49.1B · net SAM $770M–$1.8B · net SOM $11.5M–$80.4M.
- **The obtainable revenue is concentrated in the agentic core** (persisted context memory + agentic knowledge store): $29.0M of the $36.7M base SOM (79%). Everything else is upside that depends on packs, connectors and partners.
- **Stage today:** working platform, pre-revenue, pre-launch. **875 automated tests.** No paying customers, no third-party benchmarks, no SOC 2 — stated plainly on the *Honest status* slide.
- All market figures are **desk-research planning estimates for 2030 (USD)**, built top-down for TAM and bottom-up for SAM/SOM, with every assumption listed — not forecasts and not financial advice.

---

## Agenda

1. **The platform** — the problem, the concept, and what HypergraphAI is and does (features for people *and* agents)
2. **Proof and honesty** — engine readiness, what has been verified, what is not built yet, competition
3. **The three market positions** — how the platform maps to Universal AI Infrastructure, Enterprise Semantics and Knowledge Analytics
4. **Market by market** — each implementation: use case, how HypergraphAI delivers it, TAM / SAM / SOM
5. **Adjacent markets** — where else the same platform can play
6. **Summary and roll-ups** — TAM / SAM / SOM by implementation, by market, by tier; aggregate; scenarios; sensitivities
7. **Investment context** — business model, plan and ask, risks

**How TAM / SAM / SOM are defined here (all 2030, USD):**

| | Definition |
|---|---|
| **TAM** | Annual spend on the product category where a semantic knowledge / hypergraph store is the natural architecture (top-down from analyst reports × a stated slice; bottom-up where no report exists) |
| **SAM** | The part of TAM HypergraphAI can serve with its model (open-core, self-hosted or hosted, MCP-first, English-first): target organisations × need × reach × annual contract value. **Always bottom-up** |
| **SOM** | Annual recurring revenue realistically obtainable by **year 5**: SAM × obtainable share |
| **Net / aggregate** | After removing budget overlap between use cases and applying an execution limit (one company cannot win 24 markets at once) |

---

## 1. The Problem — AI Agents Are Only as Good as Their Knowledge Store

Today's agents are strong reasoners trapped in weak data structures.

| The reality | The consequence |
|---|---|
| Relational stores model rows, not relationships | Context is lost across joins |
| Property graphs allow only 2-node edges | Real facts involve *n* parties at once (a contract: buyer, seller, witnesses, jurisdiction) |
| Vector stores retrieve by similarity, not structure | No way to reason about *how* things are related |
| Every model vendor keeps its own siloed memory | Switch vendor, host or session — lose what the agent knew |
| No native time or provenance | "What did we know when, and why?" cannot be answered |

> **Result:** agents hallucinate, misattribute and forget — not because the models are weak, but because the knowledge stores feeding them are structurally inadequate. Gartner-derived reporting expects **more than 40% of agentic-AI projects to be cancelled by end-2027** (cost, unclear value, weak risk controls): a market for *grounding, memory and governance*.

---

## 2. The Insight — Relationships Are Not Binary, Knowledge Is Not Flat

```
  A conventional graph edge connects exactly 2 nodes:
      Alice ──── knows ──── Bob

  A hyperedge connects n nodes as one first-class fact, with its own attributes:
      ┌──────────────────────────────────────────────┐
      │ relation: signed-contract        flavor: hub │
      │ members: buyer · seller · witness-1 · witness-2 · jurisdiction │
      │ valid_from / valid_to · provenance · attributes                │
      └──────────────────────────────────────────────┘
```

Human and agent knowledge is **n-ary** · **semantic** (rules live in the data as axioms) · **temporal** (valid-time built in) · **provenance-first** · **composable and distributed**. No incumbent store addresses all five natively. **HypergraphAI does.**

---

## 3. What HypergraphAI Is

**A hybrid semantic hypergraph document platform:** knowledge-graph semantics + document-database flexibility + n-ary hyperedges + an AI-native interface. ✅ MIT-licensed open core.

```
┌────────────────────────────────────────────────────────────────────────┐
│  People                              AI agents & tools                 │
│  Web UI · hgsh shell · HgNexus chat  Claude · GPT · Grok · Cursor · any│
│                                      MCP client                        │
├──────────────────────────────────┬─────────────────────────────────────┤
│  REST API (FastAPI, OpenAPI)     │  MCP server — 30 tools              │
├──────────────────────────────────┴─────────────────────────────────────┤
│  Core engine: SHQL query · inference · temporal · auth/RBAC · cache    │
│  Modules: SHQL · Mesh federation · MCP · AgentChat (HgNexus) · Storage │
├────────────────────────────────────────────────────────────────────────┤
│  Pluggable storage abstraction ──▶ MongoDB backend (default)           │
└────────────────────────────────────────────────────────────────────────┘
```

Python 3.11+ · FastAPI · MongoDB 7 · one-command Docker Compose deployment · **875 automated tests**.

---

## 4. Feature Map — Humans and Agents Use the Same Platform ✅

| Capability | A person uses it to… | An AI agent uses it to… |
|---|---|---|
| **Hypergraphs, hypernodes, hyperedges** (n-ary, hub / symmetric, edges-as-members) | Create, edit and browse knowledge in the Web UI or shell | Read and write knowledge via the `hgai_hypernode_*` / `hgai_hyperedge_*` MCP tools |
| **SHQL** query language (YAML-native) | Run, save and parameterise queries in the Query screen | `hgai_query_validate` then `hgai_query_execute` — LLM-writable, LLM-repairable |
| **Semantic inference** (inverse, symmetric, transitive, SKOS) | Toggle "show inferred edges"; materialise with Project Inference | `infer: true` in SHQL; expand-edge and transitive-closure tools |
| **Point-in-time** (`valid_from/to`, `at:`) | Time-travel slider in Visualize and queries | Ask "as of" questions |
| **Mesh federation** | Register servers, ping, sync, federate | `hgai_mesh_*` tools; addresses like `mesh.server.space.graph` |
| **Spaces & RBAC** | Multi-tenant isolation, member roles | Dedicated least-privilege agent accounts (same enforcement on REST, SHQL, MCP) |
| **Notes, Media, Help** | Markdown notes with sharing scopes; 40 built-in help topics | Export chat turns to Notes; help topics as retrieval source |
| **Import / export, RDF import, seeds** | Move a graph as one file; load Turtle / RDF-XML / JSON-LD / N3 | Bulk-load generated knowledge |

---

## 5. Semantics as Data — Query, Inference, Time and Provenance ✅

**SHQL** ("shekel") is a SPARQL-inspired, YAML-native pattern language: `?variable` bindings, implicit joins, multi-hop traversal, `optional`, `union`, filters, aggregation (`count`, `sum`, `avg`, `min`, `max`, `group_by`), ordering, paging, point-in-time and inference.

```yaml
shql:
  from: eden
  infer: true                 # axioms in the data derive extra facts, live
  select: [ "?ancestor.label" ]
  where:
    - edge: { relation: rel:parent, members: [ {node_id: person:enoch}, {node_id: "?a"} ] }
    - node: { bind: "?ancestor", id: "?a" }
# → Seth   (derived via an owl:inverse-of axiom; flagged _inferred; never silently persisted)
```

| Principle | What it means for buyers |
|---|---|
| **Semantics are data** | Types, relations and axioms are hyperedges — change the ontology without deploying code |
| **Explainable inference** | Every derived edge names its source edge and axiom |
| **Time built in** | Validity windows on every node and edge; `at:` across queries, visualisation and mesh |
| **Provenance-first** | Audit trail (`mutations[]`: who, when, which fields) on every record |

---

## 6. Federation, Multi-tenancy and Security ✅

| Area | Capability |
|---|---|
| **Mesh federation** | Register several HypergraphAI servers; one SHQL query fans out concurrently and merges results — **no ETL**. Unreachable servers are skipped and reported. Logical graphs compose local and remote graphs |
| **Federated aggregates** | `count` / `sum` / `avg` / `min` / `max` over a whole mesh: each server aggregates its own graphs and the partials are merged exactly (avg as merged sum ÷ merged numeric count) |
| **Spaces** | Tenant namespaces; membership is the sole gate to a space's graphs (owner / admin / member / viewer) |
| **Accounts & RBAC** | Roles and per-graph permissions, enforced identically on REST, SHQL and MCP; JWT for people; dual API keys for machines (zero-downtime rotation) |
| **Secrets** | AI-vendor keys encrypted at rest (Fernet); SSRF-guarded web fetch for the chat agent |

**Known limits (see Honest status):** API keys are full-admin credentials (agents should use dedicated accounts); no SSO / SAML, no SOC 2, no HA reference architecture yet. 🗺️

---

## 7. The AI Interface — MCP and HgNexus ✅

**30 MCP tools** expose every platform operation to any MCP-capable model:

| Area | Tools |
|---|---|
| Hypergraphs · Hypernodes · Hyperedges | list · get · create · update · delete · stats |
| Query | validate · execute |
| Inference | expand edge · check transitive |
| Mesh | list · get · ping · sync · query |
| Media · Spaces | upload / download / delete · list / get / create / add member |

**HgNexus** — the built-in agent chat beside every screen: multi-vendor, multi-model (Anthropic, OpenAI, xAI; bring-your-own keys), server-side session memory, 50-prompt history, streaming, and **Save as Note** with full prompt / model / token metadata. The model is an MCP client of the platform — the same tools an external agent uses.

**Why it matters commercially:** MCP is vendor-neutral infrastructure — donated to the Linux Foundation's Agentic AI Foundation (Dec 2025), with 10,000+ published servers (per the investor overview's cited sources). A knowledge platform that speaks MCP natively plugs into Claude, ChatGPT, Gemini, Copilot and Cursor without custom connectors.

---

## 8. Engine Readiness — Built to Be Honest at Scale ✅

Recent engine work removed the main ways a query could be **silently wrong or slow** on large graphs:

| Capability | What changed | Effect |
|---|---|---|
| **Configurable candidate caps + `meta.truncated`** | Per-pattern fetch limits are settings (`HGAI_SHQL_MAX_*`), and a result says when a cap cut data short | No more silent truncation |
| **Storage-layer aggregation** | `count / sum / avg / min / max / count_distinct / count_numeric`, grouped, ordered — pushed into MongoDB; any other backend inherits a correct default | Exact aggregates at any size; portable contract |
| **SHQL aggregate pushdown** | Single-pattern `aggregate:` queries are computed by storage, uncapped; `limit: 0` fetches no rows | Exact totals on millions of records |
| **Sorted paging pushdown** | `order_by` / `offset` / `limit` executed by storage with deterministic tie-breaks | Exact, stable pages |
| **Batched joins** | One storage query per *distinct* bound value (many per query) instead of one per match | Removes the N+1 join cost |
| **Federated aggregate merge** | Per-server partials merged exactly across a mesh | Correct answers over federated data |

**Verified by:** 875 automated tests, including conformance suites that run identical assertions against a reference backend and a **real MongoDB**. **Not yet done:** published multi-million-row benchmarks, sharded storage, HA. 🗺️

---

## 9. Proof Points and Honest Status

| Evidence | Detail |
|---|---|
| **Working platform** | REST + MCP (30 tools) + Web UI + shell + agent chat; 875 automated tests; one-command Docker deployment |
| **Scale demonstration — "Alchemy"** | ~300 MB / 2,000,000 synthetic transactions → **3,631,632 hypernodes** and **1,872,417 hyperedges** with a generated ontology in ~13 minutes |
| **Provenance and fidelity** | 100% of nodes and edges carry provenance; 0 dangling references across 13.5M member slots; 2,000 sampled source rows: **0 mismatches** |
| **Ontology in action** | Transitive, inverse, symmetric and SKOS derivations verified through the live API |
| **Portability** | One-file graph export/import; RDF import (Turtle, RDF/XML, JSON-LD, N3); seed graphs ship with the product |

**Not claimed:** paying customers, revenue, third-party benchmarks, production references (the Alchemy data is synthetic).
**Gaps the plan funds:** no native vector / embedding search · no SSO / SAML · no SOC 2 · no HA / sharded backend · no packaged connectors · no marketplace or billing · no memory-lifecycle automation · SPARQL→SHQL conversion is designed, not built. 🗺️

---

## 10. Competitive Position

| Category | Representatives | Where HypergraphAI differs |
|---|---|---|
| Property-graph databases | Neo4j, Amazon Neptune, TigerGraph, Memgraph | Binary edges — n-ary facts need reification. HypergraphAI models the fact once and adds time, inference and an agent interface |
| Semantic / RDF platforms | Stardog, Ontotext, TopQuadrant | Triple-based, heavier standards stack. HypergraphAI is document-flexible, YAML-native, AI-first, open-core |
| Hypergraph / n-ary databases | **TypeDB** (closest technical rival) | Differentiates on document flexibility, federation mesh, built-in Notes / Help / chat and MCP-first delivery — not on n-ary support alone |
| Agent-memory layers | Mem0, Zep / Graphiti, Letta, Cognee | Mostly session / user memory. HypergraphAI is a governed enterprise store *plus* memory: RBAC, spaces, federation, audit |
| Vector databases | Pinecone, Weaviate | Complementary today (no native vector search here) |

```
                  structured, governed, explainable
                                ▲
       Stardog / RDF ●          │          ● HypergraphAI (target position)
                                │  ● TypeDB   n-ary · temporal · axioms · MCP
       Neo4j / Neptune ●        │
 ───────────────────────────────┼──────────────────────────────▶ AI-agent-native
 database-first                 │
       Vector DBs ●             │      ● Mem0 / Zep / Letta
                  unstructured, similarity-first
```

**Where we win:** the intersection of governed enterprise semantic knowledge **and** agent-native delivery. **Where incumbents are stronger today:** scale proof, ecosystems, certifications, sales reach, vector search. We compete on a wedge — n-ary + provenance + MCP + open core — not on raw scale. *Positions are qualitative; verify before external publication.*

---

## 11. The Three Market Positions and Seven Implementations

```
 HypergraphAI — one platform, three market positions
 ══════════════════════════════════════════════════════════════════════════
  1  UNIVERSAL AI INFRASTRUCTURE
       1.1  Universal context memory — across providers, hosting services, models, sessions
       1.2  Universal agentic knowledge store — persistent / long-term
       1.3  Universal agentic knowledge store — transient / per-job
  2  UNIVERSAL AI ENTERPRISE SEMANTICS
       2.1  Universal enterprise semantic layer
       2.2  Universal semantic knowledge store
  3  UNIVERSAL AI KNOWLEDGE ANALYTICS
       3.1  AI analytics agents — interactive / real-time agentic analytics
       3.2  Interactive / real-time UI user analytics
 ══════════════════════════════════════════════════════════════════════════
  A  ADJACENT — verticals, horizontal stores, first-of-kind spaces (16 sized use cases)
```

**Why "universal":** knowledge, memory and meaning live in the customer's store, in an open model, readable by any model vendor, host, framework or person — not inside one vendor's silo.

| # | Implementation | Sized as (24-use-case markets analysis) |
|---|---|---|
| 1.1 | Universal context memory | **UC 6** AI-agent persisted context / memory store · extension **UC 20** portable, user-owned AI memory |
| 1.2 | Agentic knowledge store — persistent | **UC 7** agentic semantic knowledge hypergraph store (grounding / GraphRAG) |
| 1.3 | Agentic knowledge store — transient / per-job | **UC 21** multi-agent shared world model (closest sized analogue) |
| 2.1 | Enterprise semantic layer | **UC 5** enterprise semantic integration layer |
| 2.2 | Semantic knowledge store | **UC 2** enterprise semantic knowledge hypergraph store |
| 3.1 / 3.2 | Agentic and UI analytics | **UC 4** enterprise graph / relationship analytics · **UC 3** prosumer analytics (one shared analytics budget — see Market 3) |

---

## 12. How TAM, SAM and SOM Were Determined

1. **TAM (top-down):** 2030 parent-market size from published analyst estimates (three or more sources per category, retrieved 2026-09-21) × the **slice** where a knowledge / relationship store is the natural architecture. Where no report exists (first-of-kind spaces) TAM is bottom-up or analogue-based and graded Low confidence.
2. **SAM (bottom-up):** target organisations (or users) × share with the need × share reachable with today's channels and product × annual contract value (ACV: about **$75,000** enterprise blended, **$6,000** developer / SMB).
3. **SOM (bottom-up):** SAM × obtainable share, using comparables — e.g. Neo4j ≈ $200M ARR after more than a decade; Mem0 ($24M raised) and Letta ($10M seed) among agent-memory peers; the plan's own ramp of $2.2M ARR (year 2) → $28M (year 5).
4. **Scenarios:** *conservative / base / optimistic* come from the spread of sources (TAM) and explicit low / base / high inputs (SAM, SOM).
5. **Aggregation:** TAM — remove overlap **within** clusters (retention 60–100%, where use cases share one budget) and **between** clusters (×0.85). SAM / SOM — the two anchor use cases (6, 7) are counted in full; every other use case counts 75% (the same account rarely pays twice), and SOM is further scaled by an **execution factor** (Tier 2: 50%, Tier 3: 20%).

**Confidence rubric:** *Medium* — analysts cover the category directly, sources within ~3×; *Low* — an assumed slice of a bigger parent, or sources disagree > 3×; *Very low* — first-of-kind, analogue-based.

Sizing source: *HypergraphAI — Markets: TAM, SAM and SOM by Product Space and Use Case* (2026-09-21), which lists parent markets, sources and the assumption register. Figures are nominal USD.

---

## Market 1 — Universal AI Infrastructure

*Memory and knowledge that outlive any one model, vendor, host or session*

AI agents need two things the model vendors do not give them in a portable form: **memory** (what happened, what was decided, what the user prefers) and **knowledge** (what is true, how things relate, where it came from). Today each vendor keeps its own siloed memory, and retrieval is mostly similarity over chunks.

HypergraphAI positions as the **neutral system of record** for both — reachable by any MCP-capable client, with per-account permissions, audit trail and time built in.

| Implementation | Sized as | Net TAM · SAM · SOM (base) |
|---|---|---|
| 1.1 Universal context memory | UC 6 (+ UC 20) | see slides |
| 1.2 Agentic knowledge store — persistent | UC 7 | see slides |
| 1.3 Agentic knowledge store — transient / per-job | UC 21 | see slides |

**This is the core wedge:** UC 6 and UC 7 are the anchors of the whole plan and carry **79% of the aggregate base SOM**.

---

## 1.1 — Universal Context Memory (across providers, hosting services, models, sessions)

**The use case.** A persistent memory layer that outlives sessions and is shared across vendors (Claude, GPT, Grok…), models, hosts and agent frameworks — over MCP — with audit trail, temporal validity and per-account permissions. Switching model or vendor no longer means starting from zero.

**How HypergraphAI delivers it**

- ✅ **MCP server (30 tools)** authorised per caller: any MCP client reads and writes the same memory
- ✅ **HgNexus** multi-vendor chat (Anthropic, OpenAI, xAI) with server-side sessions and prompt history; **Save as Note** exports any turn with model, tokens and timing
- ✅ Memory is ordinary hypernodes / hyperedges: n-ary facts ("this *meeting* between *these people* about *this project*"), validity windows and an audit trail on every record
- ✅ Per-agent accounts, spaces and RBAC give least-privilege memory; one-file export/import moves memory between servers
- 🛠️ Working / long-term tiers by using separate graphs per agent, session or space
- 🗺️ **Gaps:** embedding / vector recall, memory extraction and consolidation, expiry / promotion lifecycle policies

**Who buys:** Teams running production agents; agent builders and ISVs; platform-engineering groups.  
**Competes with:** Mem0, Zep / Graphiti, Letta, Cognee; built-in assistant memory (ChatGPT, Claude, Gemini); cloud-provider agent-memory services.

**Market sizing (2030, gross of overlap)**

| Use case (sized in the markets analysis) | TAM cons. | **TAM base** | TAM opt. | SAM cons. | **SAM base** | SAM opt. | SOM cons. | **SOM base** | SOM opt. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UC 6 · AI-agent persisted context / memory store | $2.9B | **$5.0B** | $8.4B | $135M | **$216M** | $306M | $4.0M | **$13.0M** | $28.0M |
| UC 20 · Portable, user-owned AI memory *(extension, first-of-kind)* | $750M | **$1.5B** | $2.2B | $22M | **$45M** | $68M | $0.1M | **$0.9M** | $2.7M |
| **Subtotal (gross)** | $3.6B | **$6.5B** | $10.6B | $157M | **$261M** | $374M | $4.1M | **$13.9M** | $30.7M |

*UC 6* — **Priority tier:** 1 — anchor · **Sizing confidence:** Medium

- **TAM basis:** Agent memory share of agentic orchestration-and-memory systems $2.9B / $5.0B / $8.4B [S13, S14, S15, S16] × slice 100% (the category itself).
- **SAM segment:** Large enterprises with a production agent (40% of all) needing cross-vendor persistent memory: 24,000 × need 6% / 10% / 14% × reachable 100% × $75,000 ACV = $108M / $180M / $252M.
- **SAM segment:** Agent builders / SMB teams (developer long tail): 150,000 × need 3% / 4% / 6% × reachable 100% × $6,000 ACV = $27M / $36M / $54M.
- **SOM basis:** obtainable share of SAM 3.0% / 6.0% / 9.0%.

*UC 20* — **Priority tier:** 3 — option · **Sizing confidence:** Very low

- **TAM basis:** Paying consumer / prosumer AI-assistant users who would pay to own and port their memory - 12.5M / 25.0M / 37.5M users × $60 per year.
- **SAM segment:** Multi-assistant, MCP-capable users (10% of 250M paid subscribers) × reachable: 25,000,000 × need 3% / 6% / 9% × reachable 50% × $60 ACV = $22M / $45M / $68M.
- **SOM basis:** obtainable share of SAM 0.5% / 2.0% / 4.0%.

**Main risk:** Fast-moving; hyperscalers and model vendors are bundling memory; the category may commoditise.  
**Validate first:** Cross-vendor portability as a buying reason; memory-extraction quality versus Mem0/Zep on public benchmarks.

> UC 20 (portable, user-owned memory for individuals) is a first-of-kind analogue market — Very low confidence; it is shown as an extension of 1.1, not part of the core case.

---

## 1.2 — Universal Agentic Knowledge Store — Persistent / Long-Term

**The use case.** A knowledge base that agents read **and write** directly — ontology, entities, n-ary facts, inferred facts, provenance — so answers are grounded, explainable and correctable. GraphRAG-style retrieval with *structure* rather than chunks.

**How HypergraphAI delivers it**

- ✅ Ontology-as-data: axioms (inverse-of, symmetric, transitive, SKOS) drive **explainable inference** with `infer: true`; every derived edge names its source
- ✅ **SHQL over MCP** (`hgai_query_validate` / `hgai_query_execute`): YAML an LLM can write and repair; structured multi-hop retrieval, not just similarity
- ✅ Provenance and temporal validity on every fact; `at:` answers "what did the agent know then?"
- ✅ Large-graph engine: exact server-side aggregation, sorted paging and batched joins; demonstrated on a 3.6M-node / 1.9M-edge graph
- ✅ Mesh federation: ground one agent on knowledge spread over several servers, no ETL
- 🗺️ **Gaps:** native vector / hybrid retrieval, packaged connectors, SOC 2 / SSO for regulated buyers

**Who buys:** AI platform teams, applied-AI groups, regulated-industry AI programmes.  
**Competes with:** Neo4j (GraphRAG), Microsoft GraphRAG, Cognee, TypeDB, Stardog Voicebox, LightRAG / LlamaIndex property graphs.

**Market sizing (2030, gross of overlap)**

| Use case (sized in the markets analysis) | TAM cons. | **TAM base** | TAM opt. | SAM cons. | **SAM base** | SAM opt. | SOM cons. | **SOM base** | SOM opt. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UC 7 · Agentic semantic knowledge hypergraph store | $2.6B | **$3.8B** | $4.8B | $180M | **$270M** | $360M | $5.4M | **$16.0M** | $32.0M |

*UC 7* — **Priority tier:** 1 — anchor · **Sizing confidence:** Medium

- **TAM basis:** Agentic AI in semantic layer & knowledge graph $2.6B / $2.6B / $2.6B [S20] + Graph-augmented share of vector / RAG infrastructure $0.0B / $1.2B / $2.2B [S23, S24] × slice 100% (the category itself).
- **SAM segment:** Large enterprises with a production agent (40% of all) needing a governed knowledge store: 24,000 × need 10% / 15% / 20% × reachable 100% × $75,000 ACV = $180M / $270M / $360M.
- **SOM basis:** obtainable share of SAM 3.0% / 6.0% / 9.0%.

**Main risk:** Buyers expect hybrid vector + graph retrieval and turnkey ingestion.  
**Validate first:** Answer-accuracy uplift versus a vector-only baseline on a design-partner corpus; ingestion effort.

---

## 1.3 — Universal Agentic Knowledge Store — Transient / Per-Job

**The use case.** Short-lived, per-job working knowledge for agents and agent fleets: a governed, time-aware shared state that agents from different vendors read and write — who knows what, what changed, what was decided — instead of ad-hoc message passing or per-agent memory. Valuable facts are promoted to the persistent store (1.2) when the job ends.

**How HypergraphAI delivers it**

- ✅ A hypergraph (or a space) per job or workflow; **spaces and RBAC** decide which agents may read or write
- ✅ Shared state is queryable with SHQL and visible in the 3D Visualize screen, with a point-in-time slider to replay how state evolved
- ✅ **Promotion path:** export / import, logical-graph composition and Project Inference move or materialise facts into a long-term graph
- 🛠️ Per-job lifecycle today is application-side (create graph → use → archive or delete)
- 🗺️ **Gaps:** automated expiry and promotion policies (memory-lifecycle module), agent-fleet coordination primitives

**Who buys:** Teams running coordinated multi-agent workflows.  
**Competes with:** LangGraph state and checkpointers, Redis / Postgres-based state, orchestration frameworks (CrewAI, AutoGen), cloud agent platforms.

**Market sizing (2030, gross of overlap)**

| Use case (sized in the markets analysis) | TAM cons. | **TAM base** | TAM opt. | SAM cons. | **SAM base** | SAM opt. | SOM cons. | **SOM base** | SOM opt. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UC 21 · Multi-agent shared world model | $480M | **$1.3B** | $2.4B | $34M | **$54M** | $81M | $0.7M | **$2.2M** | $5.7M |

*UC 21* — **Priority tier:** 2 — adjacent (pack/partner-led after GA) · **Sizing confidence:** Very low

- **TAM basis:** Multi-agent systems $12.0B / $16.2B / $20.0B [S48, S49] × slice 4% / 8% / 12%.
- **SAM segment:** Large enterprises running ≥10 coordinated agents (15% of all) × reachable: 9,000 × need 5% / 8% / 12% × reachable 100% × $75,000 ACV = $34M / $54M / $81M.
- **SOM basis:** obtainable share of SAM 2.0% / 4.0% / 7.0%.

**Main risk:** Orchestrators may embed their own state; needs pub/sub semantics.  
**Validate first:** Whether multi-agent teams prefer an external governed store to framework-native state.

> Transient / per-job stores are sized here with the closest analogue in the markets analysis, **UC 21 (multi-agent shared world model)** — a first-of-kind space at Very low confidence. Treat these figures as an indication, not a measurement.

---

## Market 1 — Universal AI Infrastructure — Roll-up

| Use case (sized in the markets analysis) | TAM cons. | **TAM base** | TAM opt. | SAM cons. | **SAM base** | SAM opt. | SOM cons. | **SOM base** | SOM opt. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UC 6 · AI-agent persisted context / memory store | $2.9B | **$5.0B** | $8.4B | $135M | **$216M** | $306M | $4.0M | **$13.0M** | $28.0M |
| UC 7 · Agentic semantic knowledge hypergraph store | $2.6B | **$3.8B** | $4.8B | $180M | **$270M** | $360M | $5.4M | **$16.0M** | $32.0M |
| UC 21 · Multi-agent shared world model | $480M | **$1.3B** | $2.4B | $34M | **$54M** | $81M | $0.7M | **$2.2M** | $5.7M |
| UC 20 · Portable, user-owned AI memory | $750M | **$1.5B** | $2.2B | $22M | **$45M** | $68M | $0.1M | **$0.9M** | $2.7M |
| **Total (gross)** | $6.7B | **$11.6B** | $17.8B | $371M | **$585M** | $815M | $10.2M | **$32.1M** | $68.4M |

**Net of overlap and execution limits** (the same method as the aggregate):

| | Conservative | **Base** | Optimistic |
|---|---:|---:|---:|
| Net TAM | $4.0B | **$6.9B** | $10.6B |
| Net SAM | $357M | **$560M** | $778M |
| Net SOM | $9.7M | **$30.0M** | $62.5M |

Net SOM is dominated by the two Tier 1 anchors (UC 6, UC 7 = $29.0M base). Confidence: Medium for UC 6 and 7; Very low for UC 20 and 21.

---

## Market 2 — Universal AI Enterprise Semantics

*One governed model of business meaning that people and AI agents both query*

Enterprises have meaning scattered across silos — warehouses, catalogs, documents, apps. AI agents need one governed model to reason over; humans need to trust where an answer came from.

HypergraphAI positions as the **semantic layer and the semantic knowledge store** in one open-core platform: ontology, entities, n-ary relationships and provenance as data, federated across systems without ETL, with per-tenant governance.

| Implementation | Sized as |
|---|---|
| 2.1 Universal enterprise semantic layer | UC 5 |
| 2.2 Universal semantic knowledge store | UC 2 |

Cluster note: the semantic layer (D) and the knowledge store (A) are frequently one purchase, so the aggregate removes overlap between them (retention 65% / 60%).

---

## 2.1 — Universal Enterprise Semantic Layer

**The use case.** A governed semantic layer that maps business meaning across silos, so that people and AI agents query **one model** — federation, entity alignment and provenance included.

**How HypergraphAI delivers it**

- ✅ **Mesh federation without ETL:** one SHQL query spans servers and graphs; logical graphs compose local and remote graphs; dot-notation addresses (`mesh.server.space.graph`)
- ✅ **Federated aggregates** merged exactly across servers
- ✅ **Semantics as data:** the ontology (types, relations, axioms) lives in the graph and is versioned with it
- ✅ **RDF import** (Turtle, RDF/XML, JSON-LD, N3) maps existing ontologies onto hypergraphs
- ✅ One query language (SHQL) for humans (Query screen) and agents (MCP)
- 🗺️ **Gaps:** packaged connectors to warehouses / catalogs, SPARQL-to-SHQL conversion (designed, not built), SSO / SAML, SOC 2

**Who buys:** Data-platform and architecture teams, AI platform owners.  
**Competes with:** Stardog, Denodo, AtScale, Cube, dbt semantic layer, Informatica, Collibra (governance).

**Market sizing (2030, gross of overlap)**

| Use case (sized in the markets analysis) | TAM cons. | **TAM base** | TAM opt. | SAM cons. | **SAM base** | SAM opt. | SOM cons. | **SOM base** | SOM opt. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UC 5 · Enterprise semantic integration layer | $2.6B | **$4.6B** | $7.7B | $68M | **$112M** | $158M | $0.7M | **$2.2M** | $6.3M |

*UC 5* — **Priority tier:** 2 — adjacent (pack/partner-led after GA) · **Sizing confidence:** Medium

- **TAM basis:** Semantic web / semantic-layer technology $2.6B / $4.6B / $7.7B [S18, S19, S20] × slice 100% (the category itself).
- **SAM segment:** Large enterprises building a governed semantic layer for AI (25% of all) × reachable while connectors are young: 15,000 × need 6% / 10% / 14% × reachable 100% × $75,000 ACV = $68M / $112M / $158M.
- **SOM basis:** obtainable share of SAM 1.0% / 2.0% / 4.0%.

**Main risk:** Connector breadth; integration is a services-heavy sale.  
**Validate first:** Top five source systems per target segment; services-to-licence ratio in pilots.

---

## 2.2 — Universal Semantic Knowledge Store

**The use case.** A governed, shared knowledge graph as the enterprise **system of record** for concepts, entities, relationships and provenance — the platform on which teams build ontologies and domain graphs.

**How HypergraphAI delivers it**

- ✅ **N-ary hyperedges** model real-world facts once (no reification), with hub and symmetric flavours and edges-as-members
- ✅ **Temporal validity, audit trail and provenance** on every record; point-in-time queries
- ✅ **Axiom-driven inference** (inverse, symmetric, transitive, SKOS) with an explainable trail; **Project Inference** materialises derived facts
- ✅ **Spaces and RBAC** for multi-tenant governance, enforced identically on REST, SHQL and MCP
- ✅ Open core (MIT), pluggable storage interface, one-file export / import, 3D Visualize
- 🗺️ **Gaps:** SSO / SAML, HA reference architecture, SOC 2, full OWL / SHACL interoperability, connectors

**Who buys:** CDO / CIO organisations, data architecture, knowledge-management and domain teams.  
**Competes with:** Neo4j, Stardog, Ontotext, TopQuadrant, TigerGraph, Amazon Neptune, TypeDB.

**Market sizing (2030, gross of overlap)**

| Use case (sized in the markets analysis) | TAM cons. | **TAM base** | TAM opt. | SAM cons. | **SAM base** | SAM opt. | SOM cons. | **SOM base** | SOM opt. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UC 2 · Enterprise semantic knowledge hypergraph store | $4.5B | **$5.7B** | $6.9B | $90M | **$135M** | $180M | $0.9M | **$3.4M** | $9.0M |

*UC 2* — **Priority tier:** 2 — adjacent (pack/partner-led after GA) · **Sizing confidence:** Medium

- **TAM basis:** Knowledge graph platforms $4.5B / $5.7B / $6.9B [S1, S2, S3] × slice 100% (the category itself).
- **SAM segment:** Large enterprises running a knowledge-graph programme (20% of all) × open to a new open-core vendor: 12,000 × need 10% / 15% / 20% × reachable 100% × $75,000 ACV = $90M / $135M / $180M.
- **SOM basis:** obtainable share of SAM 1.0% / 2.5% / 5.0%.

**Main risk:** Incumbent reference customers; RDF/OWL standards expectations; long enterprise sales cycles.  
**Validate first:** Three or more design partners running a real domain graph; how often RDF/OWL interoperability is a hard requirement.

---

## Market 2 — Universal AI Enterprise Semantics — Roll-up

| Use case (sized in the markets analysis) | TAM cons. | **TAM base** | TAM opt. | SAM cons. | **SAM base** | SAM opt. | SOM cons. | **SOM base** | SOM opt. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UC 5 · Enterprise semantic integration layer | $2.6B | **$4.6B** | $7.7B | $68M | **$112M** | $158M | $0.7M | **$2.2M** | $6.3M |
| UC 2 · Enterprise semantic knowledge hypergraph store | $4.5B | **$5.7B** | $6.9B | $90M | **$135M** | $180M | $0.9M | **$3.4M** | $9.0M |
| **Total (gross)** | $7.1B | **$10.3B** | $14.6B | $158M | **$247M** | $338M | $1.6M | **$5.6M** | $15.3M |

**Net of overlap and execution limits** (the same method as the aggregate):

| | Conservative | **Base** | Optimistic |
|---|---:|---:|---:|
| Net TAM | $3.7B | **$5.4B** | $7.8B |
| Net SAM | $118M | **$185M** | $254M |
| Net SOM | $0.6M | **$2.1M** | $5.7M |

Both use cases are Medium confidence and Tier 2 (adjacent: pack- or partner-led after GA). Their SOM counts at 75% × 50% in the aggregate because the same accounts also buy the agentic core.

---

## Market 3 — Universal AI Knowledge Analytics

*Relationship, temporal and group analytics — for AI analytics agents and for people in a UI*

Business intelligence answers "how much"; relationship analytics answers "who and what is connected, how, and since when" — multi-hop, temporal, n-ary (group) questions such as fraud rings, ownership networks, supply chains and incident blast radius.

HypergraphAI delivers the **same analytics engine to two audiences**: AI analytics agents calling SHQL over MCP, and people using an interactive UI.

| Implementation | Audience | Sized as |
|---|---|---|
| 3.1 AI analytics agents — interactive / real-time agentic analytics | Agents (MCP) | shares UC 4's budget |
| 3.2 Interactive / real-time UI user analytics | Analysts, prosumers | UC 4 (enterprise) + UC 3 (prosumer) |

**Sizing note:** the markets analysis sizes graph / relationship analytics as one category. It does **not** split spend between agent-driven and UI-driven analytics, so 3.1 and 3.2 are shown against the same figures and **not double counted**. Agent-driven analytics is a delivery channel into the same budget, plus upside from the agentic markets (UC 7).

---

## 3.1 — AI Analytics Agents (Interactive / Real-Time Agentic Analytics)

**The use case.** AI agents (in HgNexus or any MCP client) answer analytical questions over a knowledge graph on demand: they draft a structured query, run it, and reason over exact results — instead of guessing from retrieved text.

**How HypergraphAI delivers it**

- ✅ **SHQL over MCP:** `hgai_query_validate` (check before running) → `hgai_query_execute`; YAML is reliably written and repaired by LLMs
- ✅ **Exact server-side aggregates** — `count`, `sum`, `avg`, `min`, `max`, `count_numeric`, `group_by` — computed by the storage layer on single-pattern queries, so the agent gets true totals rather than a sample; `limit: 0` returns aggregates only
- ✅ **Stable sorted paging** and batched joins for multi-hop questions; `meta.truncated` tells the agent when a result is incomplete
- ✅ **Federated aggregates** across a mesh; **inference** (`infer: true`) and **point-in-time** (`at:`) inside the same query
- ✅ Parameterised, shareable query templates; results cached with graph-scoped invalidation
- ✅ Demonstrated: a fraud-pattern query with ordering over a **3.6M-node** synthetic graph returned in ≈ 5 s (measured before the recent aggregation / paging engine work)
- 🗺️ **Gaps:** published latency benchmarks at scale, vector / hybrid retrieval, BI-tool connectors

**Sizing:** shares the graph-analytics budget with 3.2 — see the next slide. Not separately sized.

---

## 3.2 — Interactive / Real-Time UI User Analytics

**The use case.** People — analysts, risk and operations teams, researchers — explore relationships interactively: multi-hop, temporal and group (hyperedge) analysis alongside conventional BI. Enterprise programmes (UC 4) and individual prosumers (UC 3) are sized separately.

**How HypergraphAI delivers it**

- ✅ **Web UI:** Query screen with examples, history, validation and cache toggle; **parameterised queries** saved as reusable, shareable templates
- ✅ **Interactive 3D Visualize** with a point-in-time slider, inferred-edge toggle and orphan hiding
- ✅ Dashboard counts, tag filters, sortable tables, media thumbnails; **Notes** for findings, with five sharing scopes
- ✅ Same engine and results as the agent path (3.1): one truth for people and agents
- ✅ **hgsh shell** for scripted analysis
- 🗺️ **Gaps:** visual (no-code) query builder, BI dashboards and connectors, mobile app

**Who buys:** Analytics leaders, data-science teams, risk and operations analysts.  
**Competes with:** Neo4j (graph data science), TigerGraph, Tableau / Power BI (not graph-native), Palantir Foundry, Quantexa, Linkurious.

**Market sizing (2030, gross of overlap)**

| Use case (sized in the markets analysis) | TAM cons. | **TAM base** | TAM opt. | SAM cons. | **SAM base** | SAM opt. | SOM cons. | **SOM base** | SOM opt. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UC 4 · Enterprise analytics platform | $4.1B | **$5.4B** | $6.7B | $36M | **$54M** | $81M | $0.4M | **$1.6M** | $4.0M |
| UC 3 · Personal / prosumer analytics platform *(prosumer analytics)* | $600M | **$960M** | $1.4B | $9.6M | **$19M** | $34M | $0.1M | **$0.6M** | $1.7M |
| **Subtotal (gross)** | $4.7B | **$6.4B** | $8.1B | $46M | **$73M** | $115M | $0.5M | **$2.2M** | $5.7M |

*UC 4* — **Priority tier:** 3 — option · **Sizing confidence:** Medium

- **TAM basis:** Graph analytics $4.1B / $5.4B / $6.7B [S7, S8] × slice 100% (the category itself).
- **SAM segment:** Large enterprises with relationship-analytics programmes (20% of all; fraud counted separately) × would adopt a new platform: 12,000 × need 4% / 6% / 9% × reachable 100% × $75,000 ACV = $36M / $54M / $81M.
- **SOM basis:** obtainable share of SAM 1.0% / 3.0% / 5.0%.

*UC 3* — **Priority tier:** 3 — option · **Sizing confidence:** Low

- **TAM basis:** Independent analysts, researchers, investigative journalists, investors, consultants doing relationship analysis - 2.5M / 4.0M / 6.0M users × $240 per year.
- **SAM segment:** Self-serve users comfortable with SHQL / a visual query builder × reachable: 4,000,000 × need 2% / 4% / 7% × reachable 50% × $240 ACV = $9.6M / $19M / $34M.
- **SOM basis:** obtainable share of SAM 1.0% / 3.0% / 5.0%.

**Main risk:** Algorithms and BI integration are table stakes; graph-database incumbents own this space.  
**Validate first:** Which three analytics workloads buyers would move first; whether BI connectors are a gating requirement.

> Sized once for both 3.1 and 3.2. UC 3 (individual analysts, journalists, investors) is Low confidence and Tier 3 (an option, not part of the funded plan).

---

## Market 3 — Universal AI Knowledge Analytics — Roll-up

| Use case (sized in the markets analysis) | TAM cons. | **TAM base** | TAM opt. | SAM cons. | **SAM base** | SAM opt. | SOM cons. | **SOM base** | SOM opt. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| UC 4 · Enterprise analytics platform | $4.1B | **$5.4B** | $6.7B | $36M | **$54M** | $81M | $0.4M | **$1.6M** | $4.0M |
| UC 3 · Personal / prosumer analytics platform | $600M | **$960M** | $1.4B | $9.6M | **$19M** | $34M | $0.1M | **$0.6M** | $1.7M |
| **Total (gross)** | $4.7B | **$6.4B** | $8.1B | $46M | **$73M** | $115M | $0.5M | **$2.2M** | $5.7M |

**Net of overlap and execution limits** (the same method as the aggregate):

| | Conservative | **Base** | Optimistic |
|---|---:|---:|---:|
| Net TAM | $3.2B | **$4.3B** | $5.5B |
| Net SAM | $34M | **$55M** | $86M |
| Net SOM | $0.1M | **$0.3M** | $0.9M |

UC 4 is Medium confidence but Tier 3: the graph-analytics market is large ($5.4B base TAM) yet crowded (Neo4j, TigerGraph, Palantir, Quantexa) and the reachable slice is small (1% of TAM). Its value is as a second door into the same accounts.

---

## Adjacent Markets — Where the Same Platform Can Also Play

The three positions are the focus. The same capabilities also fit **16 further sized use cases**. They are not part of the funded plan; they are upside that depends on vertical packs, connectors and partners.

| # | Use case | Tier | Conf. | TAM base | SAM base | SOM base |
|--:|---|:-:|---|---:|---:|---:|
| 1 | Personal semantic knowledge hypergraph store | 3 | Medium | $1.0B | $120M | $1.8M |
| 8 | General-purpose graph / n-ary data store | 2 | Low | $1.2B | $71M | $2.9M |
| 9 | Metadata, governance, lineage & provenance store | 3 | Low | $1.9B | $40M | $1.2M |
| 10 | Master data management & entity resolution | 3 | Low | $2.1B | $36M | $0.72M |
| 11 | Ontology, taxonomy & controlled-vocabulary management | 3 | Low | $432M | $35M | $1.0M |
| 12 | Enterprise search & knowledge-management augmentation | 3 | Low | $1.2B | $22M | $0.43M |
| 13 | Fraud, AML & financial-crime analytics | 2 | Low | $3.0B | $22M | $1.3M |
| 14 | Cybersecurity threat intelligence & attack-path graphs | 3 | Low | $1.2B | $45M | $1.3M |
| 15 | Supply chain, provenance & digital-twin knowledge | 3 | Low | $880M | $27M | $0.81M |
| 16 | Life sciences & healthcare knowledge graphs | 3 | Low | $495M | $14M | $0.54M |
| 17 | Regulatory, compliance & legal knowledge | 3 | Low | $776M | $34M | $1.0M |
| 18 | Defense, intelligence & public-sector analysis | 2 | Low | $1.2B | $14M | $0.81M |
| 19 | Software-engineering & enterprise-architecture knowledge | 2 | Low | $695M | $24M | $0.72M |
| 22 | Agent accountability & provenance ledger | 2 | Very low | $672M | $38M | $1.5M |
| 23 | Federated knowledge mesh & knowledge brokering | 3 | Very low | $390M | $14M | $0.51M |
| 24 | Point-in-time knowledge & decision reproducibility | 3 | Low | $812M | $27M | $1.1M |
| | **Total (gross, 16 use cases)** | | | **$18.0B** | **$583M** | **$17.6M** |

---

## Adjacent Markets — What They Are

| Group | Use cases | What HypergraphAI brings | Gross base TAM · SAM · SOM |
|---|---|---|---|
| **Other horizontal stores** | 1 personal knowledge (PKM + AI) · 8 graph / n-ary data store · 9 metadata, lineage & provenance · 10 master data & entity resolution · 11 ontology & taxonomy management · 12 enterprise search augmentation | N-ary modelling without reification, provenance on every fact, YAML-native ontologies | $7.8B · $324M · $8.1M |
| **Vertical solution packs** | 13 fraud / AML · 14 cyber threat intelligence · 15 supply chain & provenance · 16 life sciences · 17 regulatory / GRC · 18 defense & public sector · 19 software / enterprise architecture | Network-shaped, n-ary, temporal problems; the fraud vertical is demonstrated on the 3.6M-node Alchemy graph; air-gapped self-hosting suits defense | $8.2B · $180M · $6.5M |
| **First-of-kind spaces** | 22 agent accountability ledger · 23 federated knowledge brokering · 24 point-in-time decision reproducibility (20 and 21 are counted in Market 1) | Audit trail + provenance + mesh + `at:` queries as a new category; strategic (category creation) more than near-term revenue | $1.9B · $79M · $3.1M |

**Highest-value adjacent use cases (base SOM):** UC 8 General-purpose graph / n-ary data store ($2.9M), UC 1 Personal semantic knowledge hypergraph store ($1.8M), UC 22 Agent accountability & provenance ledger ($1.5M), UC 13 Fraud, AML & financial-crime analytics ($1.3M).

---

# Summary and Roll-ups

---

## Roll-up 1 — By Implementation (base case, gross of overlap)

| Implementation | UC | TAM | SAM | SOM | Tier | Confidence |
|---|---|---:|---:|---:|:-:|---|
| 1.1 Universal context memory | 6 | $5.0B | $216M | $13.0M | 1 | Medium |
|    ↳ extension: portable user-owned memory (UC 20) | 20 | $1.5B | $45M | $0.9M | 3 | Very low |
| 1.2 Agentic knowledge store — persistent | 7 | $3.8B | $270M | $16.0M | 1 | Medium |
| 1.3 Agentic knowledge store — transient / per-job | 21 | $1.3B | $54M | $2.2M | 2 | Very low |
| 2.1 Enterprise semantic layer | 5 | $4.6B | $112M | $2.2M | 2 | Medium |
| 2.2 Semantic knowledge store | 2 | $5.7B | $135M | $3.4M | 2 | Medium |
| 3.1 / 3.2 Agentic + UI analytics (shared) | 4 | $5.4B | $54M | $1.6M | 3 | Medium |
|    ↳ extension: prosumer analytics (UC 3) | 3 | $960M | $19M | $0.6M | 3 | Low |
| **Seven implementations + 2 extensions** | | **$28.3B** | **$905M** | **$39.9M** | | |

**Base SOM by implementation (year-5 ARR):**

```
1.1 Universal context memory                 ████████████████████████ $13.0M
↳ extension: portable user-owned memory (UC  ██ $0.9M
1.2 Agentic knowledge store — persistent     ██████████████████████████████ $16.0M
1.3 Agentic knowledge store — transient / pe ████ $2.2M
2.1 Enterprise semantic layer                ████ $2.2M
2.2 Semantic knowledge store                 ██████ $3.4M
3.1 / 3.2 Agentic + UI analytics (shared)    ███ $1.6M
↳ extension: prosumer analytics (UC 3)       █ $0.6M
```

---

## Roll-up 2 — By Market Position (all three scenarios)

**Gross** (simple sum of use cases — overstates, because use cases share budgets):

| Market position | TAM cons. | **TAM base** | TAM opt. | SAM cons. | **SAM base** | SAM opt. | SOM cons. | **SOM base** | SOM opt. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1. Universal AI Infrastructure | $6.7B | $11.6B | $17.8B | $371M | $585M | $815M | $10.2M | $32.1M | $68.4M |
| 2. Universal AI Enterprise Semantics | $7.1B | $10.3B | $14.6B | $158M | $247M | $338M | $1.6M | $5.6M | $15.3M |
| 3. Universal AI Knowledge Analytics | $4.7B | $6.4B | $8.1B | $46M | $73M | $115M | $0.5M | $2.2M | $5.7M |
| A. Adjacent markets | $8.1B | $18.0B | $39.7B | $347M | $583M | $893M | $4.6M | $17.6M | $47.0M |
| **Total, 24 use cases** | **$26.6B** | **$46.2B** | **$80.2B** | **$921M** | **$1.5B** | **$2.2B** | **$16.8M** | **$57.5M** | **$136M** |

**Net** (overlap removed, execution-limited — the headline figures):

| Market position | TAM cons. | **TAM base** | TAM opt. | SAM cons. | **SAM base** | SAM opt. | SOM cons. | **SOM base** | SOM opt. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1. Universal AI Infrastructure | $4.0B | $6.9B | $10.6B | $357M | $560M | $778M | $9.7M | $30.0M | $62.5M |
| 2. Universal AI Enterprise Semantics | $3.7B | $5.4B | $7.8B | $118M | $185M | $254M | $0.6M | $2.1M | $5.7M |
| 3. Universal AI Knowledge Analytics | $3.2B | $4.3B | $5.5B | $34M | $55M | $86M | $0.1M | $0.3M | $0.9M |
| A. Adjacent markets | $5.1B | $11.3B | $25.2B | $260M | $437M | $670M | $1.2M | $4.3M | $11.3M |
| **Aggregate, 24 use cases** | **$16.0B** | **$28.0B** | **$49.1B** | **$770M** | **$1.2B** | **$1.8B** | **$11.5M** | **$36.7M** | **$80.4M** |

*Net TAM = Σ (use-case TAM × cluster retention) × 0.85 cross-cluster factor. Net SAM counts Tier 1 in full and other use cases at 75%. Net SOM additionally applies execution factors (Tier 2: 50%, Tier 3: 20%). Rounded; the underlying markets analysis reports aggregate SOM as $12M / $37M / $80M.*

---

## Roll-up 3 — Where the Value Is

**Share of aggregate net (base case):**

| Market position | Net TAM | % | Net SAM | % | Net SOM | % |
|---|---:|---:|---:|---:|---:|---:|
| 1. Universal AI Infrastructure | $6.9B | 25% | $560M | 45% | $30.0M | 82% |
| 2. Universal AI Enterprise Semantics | $5.4B | 19% | $185M | 15% | $2.1M | 6% |
| 3. Universal AI Knowledge Analytics | $4.3B | 15% | $55M | 4% | $0.3M | 1% |
| A. Adjacent markets | $11.3B | 40% | $437M | 35% | $4.3M | 12% |

```
Net SOM (base) — where obtainable revenue sits
1 Universal AI Infrastructure      ████████████████████████████████████ $30.0M
2 Universal AI Enterprise Semantics ███ $2.1M
3 Universal AI Knowledge Analytics █ $0.3M
A Adjacent markets                 █████ $4.3M

Net TAM (base) — how large the addressable spend is
1 Universal AI Infrastructure      ██████████████████████ $6.9B
2 Universal AI Enterprise Semantics █████████████████ $5.4B
3 Universal AI Knowledge Analytics ██████████████ $4.3B
A Adjacent markets                 ████████████████████████████████████ $11.3B
```

**Reading it:** the three positions hold most of the net SOM, and Market 1 (infrastructure) dominates it. TAM is spread more widely — adjacent markets are a large share of *spend* but a small share of what is *obtainable* with today's product and a 10-person seed plan.

---

## Roll-up 4 — By Priority Tier and Confidence (base, gross)

| Tier | Meaning | Use cases | TAM | SAM | SOM |
|---|---|---:|---:|---:|---:|
| 1 | **Anchor** — funded core, counted in full | 2 | $8.8B | $486M | $29.0M |
| 2 | **Adjacent** — pack- or partner-led after GA (SOM × 50%) | 8 | $18.4B | $470M | $15.0M |
| 3 | **Option** — opportunistic (SOM × 20%) | 14 | $19.0B | $532M | $13.5M |

| Confidence | Use cases | TAM | SAM | SOM |
|---|---:|---:|---:|---:|
| Medium | 6 | $25.5B | $907M | $38.0M |
| Low | 14 | $16.9B | $430M | $14.4M |
| Very low | 4 | $3.9B | $151M | $5.1M |

**Reading it:** the six *Medium*-confidence use cases (the agentic core, enterprise semantics, enterprise analytics and personal knowledge) hold about two-thirds of gross SOM — the numbers an investor should lean on are the ones with the best evidence. The rest rests on assumed slices or analogues.

---

## Roll-up 5 — By Cluster and the De-duplication Step (base)

Use cases in a cluster largely spend from the same budget, so each cluster's TAM is multiplied by a *retention factor*; a further 0.85 removes overlap between clusters.

| Cluster | Use cases | Retention | Gross TAM | Net TAM (before ×0.85) | Gross SAM | Gross SOM |
|---|---:|---:|---:|---:|---:|---:|
| A — Knowledge & semantic stores | 5 | 60% | $9.5B | $5.7B | $383M | $9.5M |
| B — Agent context, knowledge & accountability | 5 | 70% | $12.3B | $8.6B | $623M | $33.6M |
| C — Analytics | 2 | 80% | $6.4B | $5.1B | $73M | $2.2M |
| D — Integration, governance & provenance | 4 | 65% | $9.4B | $6.1B | $215M | $5.2M |
| E — Vertical solutions | 7 | 85% | $8.2B | $7.0B | $180M | $6.5M |
| F — Knowledge ecosystem | 1 | 100% | $390M | $390M | $14M | $0.5M |
| **Total** | 24 | | **$46.2B** | **$32.9B** | **$1.5B** | **$57.5M** |

After the 0.85 cross-cluster factor: **net TAM $28.0B**. Retention factors are judgement — lowest where products substitute for each other (A, D), highest where budgets are distinct (verticals E, ecosystem F).

---

## Aggregate — From 24 Use Cases to One Number

| Layer (2030) | Conservative | **Base** | Optimistic | What it is |
|---|---:|---:|---:|---|
| TAM — gross sum | $26.6B | $46.2B | $80.2B | Simple sum; overstates (shared budgets) |
| **TAM — net (de-duplicated)** | **$16.0B** | **$28.0B** | **$49.1B** | Headline TAM |
| SAM — gross sum | $921M | $1.5B | $2.2B | Simple sum of bottom-up SAMs |
| **SAM — net** | **$770M** | **$1.2B** | **$1.8B** | Headline SAM: anchors in full, others at 75% |
| SOM — gross sum | $16.8M | $57.5M | $136M | If every use case were pursued at full effort |
| **SOM — net, execution-limited (year-5 ARR)** | **$11.5M** | **$36.7M** | **$80.4M** | Headline SOM: Tier 1 fully, Tier 2 at 50%, Tier 3 at 20% (each also × 75%) |

**Consistency checks:** net SAM ÷ net TAM = 4.4% (a low ratio is expected — many slices are far from today's product) · anchor SOM $29.0M ≈ the plan's ≈ $28M year-5 ARR (≈ 6% of the anchors' SAM of $486M) · headline SOM would imply roughly 490 enterprise customers at $75K ACV if it were all subscriptions (the year-5 mix also contains services, marketplace and training, so the real count is lower).

---

## The Funded Core vs. the Upside

| | Conservative | **Base** | Optimistic |
|---|---:|---:|---:|
| Anchor SAM (UC 6 + UC 7) | $315M | **$486M** | $666M |
| Incremental SAM from the other 22 use cases (× 0.75) | $455M | **$752M** | $1.1B |
| **Net SAM** | $770M | **$1.2B** | $1.8B |
| Anchor SOM (UC 6 + UC 7) | $9.4M | **$29.0M** | $60.0M |
| Incremental SOM (after overlap and execution factors) | $2.1M | **$7.7M** | $20.4M |
| **Execution-limited SOM** | $11.5M | **$36.7M** | $80.4M |

- **Present $29.0M as the funded plan** — it reproduces the investor deck's ≈ $28M year-5 ARR from identical inputs — **and the rest as unfunded upside** that needs vertical packs, connectors and partners.
- The **unconstrained** SOM ($57.5M gross) shows the opportunity cost of focus, not a forecast: about $21M of obtainable revenue sits in spaces a 10-person team cannot staff in its first five years.
- Every SAM is far below its TAM (0.7%–12% by use case). That is deliberate: HypergraphAI is a new open-core entrant without SSO, SOC 2, connectors, vector search or a GA hosted service today. **Closing those gaps raises reach more than any other lever.**

---

## Scenarios and Sensitivities

| | Conservative | **Base** | Optimistic |
|---|---|---|---|
| **TAM** | Lowest credible source per parent market | Central estimate | Highest credible source |
| **SAM** | Low end of each *need* share | Base share | High end |
| **SOM** | Low obtainable share (≈ ½ base) | Base share | High share (≈ 1.5× base) |
| **Net TAM / SAM / SOM** | $16.0B / $770M / $11.5M | **$28.0B / $1.2B / $36.7M** | $49.1B / $1.8B / $80.4M |

Scenarios move every input together, so they are a *bracket*, not a probability distribution.

**One-at-a-time sensitivities (base net SAM $1.2B, SOM $37M):**

| Input | Base | Low → High | Net SAM (low → high) | SOM (low → high) |
|---|---|---|---:|---:|
| Organisations with ≥ 1,000 employees | 60,000 | 40,000 → 80,000 | $914M → $1.6B | $26M → $48M |
| Share with ≥ 1 production agent by 2030 | 40% | 25% → 55% | $1.1B → $1.4B | $27M → $47M |
| Enterprise ACV | as modelled | ×0.6 → ×1.4 | $797M → $1.7B | $22M → $51M |
| Obtainable share of SAM | as modelled | ×0.5 → ×1.5 | unchanged | $18M → $55M |

**Reading it:** SOM is most sensitive to obtainable share and ACV (pricing outcomes as much as market facts), then to the enterprise population and the pace of agent adoption. Because the agentic core is about four-fifths of SOM, **anything that changes how quickly enterprises put agents into production moves the headline roughly in proportion.**

---

## What Must Be True — Assumptions to Validate First

| Priority | Assumption | Base value | Why it matters |
|:-:|---|---|---|
| 1 | Share of large enterprises with ≥ 1 production agent by 2030 | 40% (Gartner's 2026 CIO survey: 17% deployed today) | The agentic core (≈ 79% of SOM) scales with it |
| 2 | Obtainable share of SAM | 6% core; 1.5%–6% elsewhere | SOM scales one-for-one |
| 3 | Enterprise ACV | ≈ $75K blended ($18K / $60K / $180K+ per year tiers) | SAM and SOM scale with it |
| 4 | Organisations with ≥ 1,000 employees | 60,000 | No authoritative global count was found |
| 5 | Execution factors and overlap | Tier 2 50% · Tier 3 20% · overlap 75% | Judgement — affects the aggregate only |
| 6 | Product gaps closed by 2030 | SSO, SOC 2, HA, connectors, vector search, hosted GA | Determines reach (*r*) in most use cases |

**Validation plan (about 10 weeks):** buyer interviews and a commissioned independent bottom-up study, design-partner pilots to test willingness to pay and obtainable share, a second memory-specific market source, and a sales-overlap review.

---

## Limitations — Read Before Using These Numbers

- **Desk research only.** No customers, prospects or experts were interviewed; every input is an estimate.
- **Analyst reports disagree and were not audited.** Several parent-market figures come from research-firm summaries or press releases; scopes differ. Verify against the full reports before quoting.
- **Bottom-up counts are assumptions** — enterprise population, adoption rates and ACVs drive most of the SAM.
- **The product is not finished for every use case.** SSO / SAML, SOC 2, connectors, vector search, a visual query builder, a mobile app and a hosted GA are outstanding.
- **Overlap and execution factors are judgement,** not measured quantities.
- **First-of-kind markets are analogies** (UC 20–24, and the transient / per-job implementation 1.3): the figures show what would be true *if the analogue holds*.
- **Agentic vs UI analytics (3.1 / 3.2) are not split** in the sizing — they share one graph-analytics budget.
- **Not financial advice or a forecast.** Figures are planning estimates, nominal USD, no inflation or FX adjustment.

---

# Investment Context

---

## Business Model — Seven Revenue Streams

| # | Stream | What is sold | Nature |
|---|---|---|---|
| 1 | **Managed hosting** | Single- / multi-tenant instances with backup, monitoring, upgrades, SLA | Recurring — core of the model |
| 2 | **Subscriptions** | Cloud tiers; enterprise editions with advanced modules (SSO, audit export, HA) 🗺️ | Recurring; MIT open core stays free |
| 3 | **Marketplace** | First- and third-party extension modules 🗺️ | Take rate + first-party sales |
| 4 | **Support** | Tiered SLAs, named engineers | Recurring, attach to 1–2 |
| 5 | **Professional services** | Ontology design, migrations, agent integration, custom modules | Project; land-and-expand wedge |
| 6 | **Knowledge brokering** | Curated, licensed domain knowledge over the mesh 🗺️ | Early concept (UC 23) |
| 7 | **Training & certification** | SHQL / MCP certification, admin training | Per seat / cohort; builds the partner channel |

Vendor model costs are **pass-through**: customers bring their own AI-vendor keys (as HgNexus already works), so there is no token-resale or model-cost risk.

**Year-5 exit-ARR scenario (a scenario, not a forecast):** ~$0.1M (yr 1) → ~$2.2M → ~$6M → ~$14M → **~$28M (yr 5, ≈ 6% of core SAM)**. Mix: hosting & subscriptions 60% · support 12% · services 12% · marketplace net 10% · training 3% · brokering 3%.

---

## The Plan and the Ask — Seed Round (planning recommendation; not an offer)

**Raise $3.0M seed** (recommended pre-money $11M / post-money $14M ≈ 21.4% new-investor ownership; range $9M–$15M pre-money) for about **17 months** of runway.

| Use of funds | Amount | Share |
|---|---:|---:|
| Engineering (CTO, tech lead, 4 developers) | ≈ $1.63M | ≈ 54% |
| Leadership | ≈ $0.29M | ≈ 10% |
| Sales / BD | ≈ $0.28M | ≈ 9% |
| Finance, ops, admin | ≈ $0.41M | ≈ 14% |
| Infrastructure, SOC 2 readiness, legal, marketing, insurance | ≈ $0.40M | ≈ 13% |

| By month | Milestone | Investor-visible proof |
|---:|---|---|
| 3 | v0.1 open-source releases | Public repo, docs, demos |
| 6–9 | 1–3 alpha hosting customers; first training cohort | Design-partner agreements |
| 12–15 | **GA** of managed hosting; public pricing | Paying customers, MRR curve |
| 14–15 | Series A process begins | Pipeline, retention, OSS adoption |

Projected path: Seed $3M → Series A $10–15M (month ~15–20) → Series B $25–40M (month ~30–36) — placeholders, to be re-derived from real traction.

---

## Risks and Why This Is Investable

| Risk | Mitigation |
|---|---|
| **Category creation** — "semantic hypergraph for agents" is new | Position on outcomes (grounded, auditable, portable agent memory); MCP as the adoption vector; vertical packs |
| **Agentic-AI disappointment** (> 40% of projects may be cancelled by 2027) | Sell governance and grounding — the antidote — not agent hype |
| **Incumbent response** (graph vendors adding GenAI; TypeDB is a close peer) | Wedge on provenance + temporal + federation + open core; do not fight on raw scale |
| **Model vendors bundle memory** | Neutrality is the product: cross-vendor, customer-owned, audited |
| **Scale perception** | Publish multi-million-row benchmarks; sharded backend roadmap; mesh scale-out |
| **Open-core monetisation** | Monetise operations, enterprise modules, marketplace, services |
| **Assumption risk** | Commission an independent market study; refresh quarterly |

**Why investable:** (1) a structural insight already implemented — running code, 875 tests; (2) riding a standard, not fighting one — MCP is Linux-Foundation-governed and adopted across AI vendors; (3) control-point economics — memory and knowledge that persist across models become the customer's system of record; (4) open-core distribution with seven monetisation layers; (5) capital-efficient proof — a 10-person plan, ~17 months to GA; (6) an honest engineering culture — verified claims, stated limits, reconciled data.

---

## Disclaimer

This deck is a **confidential planning draft**. Market figures are desk-research estimates for 2030 (nominal USD) built from published analyst summaries and stated assumptions; they are not forecasts, valuations or financial advice, and have not been independently validated. Competitor descriptions are qualitative and based on public documentation reviewed 2026-09; verify before external publication. Product statuses (✅ live / 🛠️ enabled / 🗺️ planned) describe the repository at the time of writing. The seed terms shown are a planning recommendation, not an offer of securities. Potential outcomes are uncertain; nothing here is a promise of returns.

---

## Appendix A — Full Use-Case Catalog (base case) and Market Position

| # | Use case | Market position | Cluster | Tier | Conf. | TAM | SAM | SOM |
|--:|---|---|:-:|:-:|---|---:|---:|---:|
| 1 | Personal semantic knowledge hypergraph store | Adjacent | A | 3 | Medium | $1.0B | $120M | $1.8M |
| 2 | Enterprise semantic knowledge hypergraph store | 2 Enterprise semantics | A | 2 | Medium | $5.7B | $135M | $3.4M |
| 3 | Personal / prosumer analytics platform | 3 Knowledge analytics | C | 3 | Low | $960M | $19M | $0.58M |
| 4 | Enterprise analytics platform | 3 Knowledge analytics | C | 3 | Medium | $5.4B | $54M | $1.6M |
| 5 | Enterprise semantic integration layer | 2 Enterprise semantics | D | 2 | Medium | $4.6B | $112M | $2.2M |
| 6 | AI-agent persisted context / memory store | 1 Infrastructure | B | 1 | Medium | $5.0B | $216M | $13M |
| 7 | Agentic semantic knowledge hypergraph store | 1 Infrastructure | B | 1 | Medium | $3.8B | $270M | $16M |
| 8 | General-purpose graph / n-ary data store | Adjacent | A | 2 | Low | $1.2B | $71M | $2.9M |
| 9 | Metadata, governance, lineage & provenance store | Adjacent | D | 3 | Low | $1.9B | $40M | $1.2M |
| 10 | Master data management & entity resolution | Adjacent | D | 3 | Low | $2.1B | $36M | $0.72M |
| 11 | Ontology, taxonomy & controlled-vocabulary management | Adjacent | A | 3 | Low | $432M | $35M | $1.0M |
| 12 | Enterprise search & knowledge-management augmentation | Adjacent | A | 3 | Low | $1.2B | $22M | $0.43M |
| 13 | Fraud, AML & financial-crime analytics | Adjacent | E | 2 | Low | $3.0B | $22M | $1.3M |
| 14 | Cybersecurity threat intelligence & attack-path graphs | Adjacent | E | 3 | Low | $1.2B | $45M | $1.3M |
| 15 | Supply chain, provenance & digital-twin knowledge | Adjacent | E | 3 | Low | $880M | $27M | $0.81M |
| 16 | Life sciences & healthcare knowledge graphs | Adjacent | E | 3 | Low | $495M | $14M | $0.54M |
| 17 | Regulatory, compliance & legal knowledge | Adjacent | E | 3 | Low | $776M | $34M | $1.0M |
| 18 | Defense, intelligence & public-sector analysis | Adjacent | E | 2 | Low | $1.2B | $14M | $0.81M |
| 19 | Software-engineering & enterprise-architecture knowledge | Adjacent | E | 2 | Low | $695M | $24M | $0.72M |
| 20 | Portable, user-owned AI memory | 1 Infrastructure | B | 3 | Very low | $1.5B | $45M | $0.90M |
| 21 | Multi-agent shared world model | 1 Infrastructure | B | 2 | Very low | $1.3B | $54M | $2.2M |
| 22 | Agent accountability & provenance ledger | Adjacent | B | 2 | Very low | $672M | $38M | $1.5M |
| 23 | Federated knowledge mesh & knowledge brokering | Adjacent | F | 3 | Very low | $390M | $14M | $0.51M |
| 24 | Point-in-time knowledge & decision reproducibility | Adjacent | D | 3 | Low | $812M | $27M | $1.1M |
| | **Total (gross)** | | | | | **$46.2B** | **$1.5B** | **$57.5M** |

---

## Appendix B — Feature Inventory (for Diligence)

| Area | Feature | Status |
|---|---|:-:|
| Core | Hypernodes, hyperedges (hub / symmetric), hypergraphs (instantiated / logical), tags, status, free-form attributes, validity windows, audit trail, SHA-256 hyperkeys | ✅ |
| Query | SHQL: patterns, joins, OPTIONAL, UNION, filters, order / limit / offset / distinct, aggregate (`count`, `sum`, `avg`, `min`, `max`, `count_numeric`, `group_by`), `at:`, multi-graph `from:`, result cache | ✅ |
| Engine | Storage-side aggregation and sorted paging, batched joins, configurable candidate caps, `meta.truncated`, federated aggregate merge | ✅ |
| Inference | inverse-of, symmetric, transitive, SKOS broader / narrower transitive; expand edge; closure / path; project-to-graph | ✅ |
| Federation | Mesh registry, concurrent fan-out, dot-notation addresses, ping / sync / query | ✅ |
| Tenancy & security | Spaces (4 roles), accounts (4 roles), JWT, dual API keys, encrypted vendor keys, SSRF-guarded fetch | ✅ |
| Interfaces | REST (OpenAPI), MCP (30 tools), Web UI, hgsh shell | ✅ |
| Knowledge work | Notes (Markdown, tag folders, front matter, 5 scopes), parameterised queries, media library, Help (40 topics) | ✅ |
| Visual | Interactive 3D Visualize with point-in-time and inference toggle | ✅ |
| AI chat (HgNexus) | Multi-vendor / model catalog, MCP-aware agent, sessions, prompt history, Save as Note, streaming | ✅ |
| Data movement | One-file export / import, RDF import (Turtle, RDF/XML, JSON-LD, N3), seeds, generator + verifier pattern | ✅ |
| Extensibility | Pluggable modules; pluggable storage interface with conformance tests (MongoDB implemented) | ✅ |
| Ops | Docker / Compose, health endpoint, startup indexes, cache | ✅ |
| Vector / hybrid search, SSO / SAML, SOC 2, HA / sharding, marketplace, billing, memory-lifecycle automation, SPARQL→SHQL conversion, visual query builder | | 🗺️ |

---

## Appendix C — Sources and Method Notes

- **Sizing:** *HypergraphAI — Markets: TAM, SAM and SOM by Product Space and Use Case* (2026-09-21): parent-market table (Section 4), 24 use-case cards (Sections 5–6), aggregation (Section 7), sensitivities (Section 8), assumption register (Section 10), source list (Section 12).
- **Platform, competition, business model, plan and ask:** *HypergraphAI — Semantic Knowledge Hypergraphs for the AI Era* investor overview (2026-09-21).
- **Engine readiness:** the repository's automated test suite (875 tests) including storage-layer conformance suites and federated-aggregate tests.
- **How the three market positions map to sized use cases:** Universal context memory → UC 6 (+ UC 20); agentic knowledge store, persistent → UC 7; transient / per-job → UC 21 (closest analogue); enterprise semantic layer → UC 5; semantic knowledge store → UC 2; agentic and UI analytics → UC 4 (+ UC 3). Remaining 16 use cases are reported as adjacent markets, so the three positions plus adjacent markets reconcile exactly to the 24-use-case aggregate.
- **Market figures use published analyst estimates retrieved 2026-09-21.** Several were read from research-firm summaries and press releases; verify against the full reports before quoting.
