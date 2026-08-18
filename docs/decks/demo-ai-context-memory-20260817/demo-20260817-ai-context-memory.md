---
title: "HypergraphAI as an AI Agent Memory Engine"
description: "Working, session, episodic, semantic, and procedural memory for AI agents — modeled natively in HypergraphAI, served over MCP, contrasted against SQL, traditional knowledge graphs, and bare vector stores"
---

# HypergraphAI as an AI Agent Memory Engine
## Working · Session · Episodic · Semantic · Procedural

This deck is self-contained — every query and data snippet below is real,
verified-safe HQL/SHQL syntax (not pseudocode), built around one running
example. No external files required.

**Format:** each `---` is one slide. Open in any Markdown slide tool (Marp,
reveal-md, or a slide-import) or read top to bottom.

---

## Agenda

1. Why agents need more than a chat window
2. Five kinds of memory — one platform
3. hgai building blocks, in 60 seconds
4. One scenario, five tiers, worked end to end
5. Querying every tier — and across tiers
6. MCP: how an agent actually reads and writes memory
7. Why hgai over SQL, over RDF knowledge graphs, over a bare vector store
8. Lifecycle, honesty, and how to get started

---

## 1. Why Agents Need More Than a Chat Window

Ask what happens to everything an agent figures out the moment a session
ends, and the honest answer almost everywhere today is: **it's gone.**

- A context window is finite — long sessions truncate, and earlier
  reasoning silently falls out of what the model can see
- A new session starts from zero — yesterday's carefully-built context has
  to be re-explained
- Even *within* one session, an agent that did real multi-step reasoning
  has no way to hand that conclusion to a different tool call, a different
  agent, or its future self next week

This isn't a model problem. It's a **storage** problem — and it's not one
problem, it's (at least) five, because "memory" isn't one thing.

---

## 2. Five Kinds of Memory — One Platform

| Tier | What it holds | Lifespan |
|---|---|---|
| **Working** | The current step's scratch state — intermediate hypotheses, partial tool output | Seconds to minutes, usually superseded or discarded |
| **Session** | This conversation's active context — current goal, entities in play, working hypothesis | The current session |
| **Episodic** | What happened in past sessions — decisions, conclusions, outcomes | Durable, queryable indefinitely |
| **Semantic** | Durable domain knowledge independent of any session — entities, relationships, facts | Durable, the "ground truth" |
| **Procedural** | How to do something — runbooks, approved steps, constraints | Durable, rarely changes |

Most AI tooling today has **zero** of these as distinct concepts — it's
one vector store, undifferentiated. Section 7 explains exactly why that's
costly. hgai models all five as ordinary, queryable hypergraph data —
distinguished by tags and structure, not by five different systems.

---

## 3. hgai Building Blocks, in 60 Seconds

- **Hypernode** — an entity: a person, a service, a session, a conclusion
- **Hyperedge** — a relationship connecting **any number** of entities at
  once, with its own attributes, tags, and validity window — not just a
  pointer between two things
- **Point-in-time (PIT)** — nothing is overwritten; every fact carries a
  validity window, so "what did we know as of session X" is a real,
  answerable query
- **Tags + status** — every artifact carries free-form tags; this is how
  memory *tier* is expressed (`memory-tier: episodic`), not a separate
  schema per tier

One example, worth internalizing before Section 4: *"Agent A, in session
S, using evidence E, concluded C, with confidence 0.88."* That's a single
real memory — and it has **four simultaneous participants**. A hyperedge
holds it as one object. Keep that fact in mind for Section 7.

---

## 4. One Scenario, Five Tiers

An AI SRE-assistant agent is investigating a production incident for a
customer, **Acme Corp** — incident `INC-4521`, service `checkout-api`
showing elevated latency. We'll follow one thread of its work through all
five memory tiers. *(Fictional company/scenario, built for this demo.)*

```
docs/demos — this scenario is fully self-contained in this file.
Graph id used throughout: agent-memory-demo
```

Watch for one thing across every tier below: **the same underlying
building blocks** (hypernode, hyperedge, tags, PIT) represent all five —
there is no separate "episodic memory database" bolted onto a "semantic
knowledge graph." It's one hypergraph, tagged and typed consistently.

---

## 5. Tier 1 — Working Memory

The agent, mid-investigation, is holding a scratch note while it compares
two metrics dashboards — not yet a conclusion, not yet worth keeping past
this step.

```yaml
nodes:
  - id: scratch:hypothesis-check-1
    label: "Comparing pool metrics: INC-4521 vs INC-4102"
    type: WorkingNote
    attributes:
      note: "pool_active nearly saturated in both incidents — worth checking history"
    tags: ["memory-tier:working", "session:sess-2026-08-17-a"]
```

**Why a hypernode, not a hyperedge:** working memory is usually a single
entity's transient state, not yet a relationship worth asserting. It's
tagged by session so it can be bulk-cleaned when the session ends —
working-tier items are the one tier this platform expects you to *not*
keep forever.

---

## 6. Tier 2 — Session Memory

Broader than one working step: what the whole current session has
established so far.

```yaml
nodes:
  - id: session:sess-2026-08-17-a
    label: "Session sess-2026-08-17-a"
    type: SessionContext
    attributes:
      customer: "Acme Corp"
      incident_id: "INC-4521"
    tags: ["memory-tier:session"]

edges:
  - id: edge-session-focus-a
    relation: session-focus
    flavor: hub
    members:
      - { node_id: "session:sess-2026-08-17-a", seq: 0 }
      - { node_id: "customer:acme-corp", seq: 1 }
      - { node_id: "incident:inc-4521", seq: 2 }
    attributes:
      current_hypothesis: "connection pool exhaustion"
    tags: ["memory-tier:session"]
```

**Why this matters:** any tool call, any sub-agent, any UI panel that
needs "what's this session about right now" queries one hyperedge instead
of threading state through function arguments.

---

## 7. Tier 3 — Episodic Memory

Three weeks ago, a **different session** investigated a similar incident
on the same service and reached a conclusion. That session ended — but
the conclusion didn't disappear.

```yaml
nodes:
  - id: session:sess-2026-07-27-b
    label: "Session sess-2026-07-27-b"
    type: SessionContext
  - id: evidence:log-excerpt-pool-metrics-4102
    label: "Pool metrics excerpt, INC-4102"
    type: Evidence
    attributes:
      excerpt: "pool_active=20/20 pool_wait_ms=4200 (default max_pool_size=20)"
  - id: conclusion:root-cause-pool-misconfig
    label: "Root cause: pool size left at framework default"
    type: Conclusion
    attributes:
      statement: "Connection pool max size stayed at the framework default (20) after a deploy tripled concurrent request volume."

edges:
  - id: edge-incident-conclusion-4102
    relation: incident-conclusion
    flavor: hub
    members:
      - { node_id: "service:checkout-api", seq: 0 }
      - { node_id: "session:sess-2026-07-27-b", seq: 1 }
      - { node_id: "evidence:log-excerpt-pool-metrics-4102", seq: 2 }
      - { node_id: "conclusion:root-cause-pool-misconfig", seq: 3 }
    attributes:
      confidence: 0.88
      investigator_agent: "claude-agent-sre-v1"
      summary: "Pool exhaustion root-caused to a stale default after a deploy; recommended raising max_pool_size."
    tags: ["memory-tier:episodic", "ai-generated"]
    valid_from: "2026-07-27T16:40:00Z"
```

**This is the centerpiece example of the whole deck.** One memory, four
simultaneous participants (subject service, originating session,
supporting evidence, the conclusion itself) — Section 10 shows exactly
what this costs to represent in SQL or RDF instead.

---

## 8. Tier 4 — Semantic Memory

Durable, session-independent ground truth — true regardless of which
incident, which agent, or which day it is.

```yaml
nodes:
  - id: customer:acme-corp
    label: "Acme Corp"
    type: Customer
    attributes: { tier: "Tier-1" }
  - id: incident:inc-4521
    label: "INC-4521"
    type: Incident
    attributes: { status: "investigating" }
  - id: service:checkout-api
    label: "checkout-api"
    type: Service
  - id: database:orders-db
    label: "orders-db"
    type: Database
    attributes: { connection_pool_default_size: 20 }

edges:
  - id: edge-checkout-depends-on-orders-db
    relation: depends-on
    flavor: direct
    members:
      - { node_id: "service:checkout-api", seq: 0 }
      - { node_id: "database:orders-db", seq: 1 }
```

**Why this matters:** this is the same kind of core domain knowledge every
prior HypergraphAI deck has described — the difference here is just that
episodic and session memories *reference into it* (both edges above use
`service:checkout-api`), which is what makes cross-tier queries possible
in Section 9.

---

## 9. Tier 5 — Procedural Memory

How to actually run this kind of investigation — captured once, reused
by every future session and every agent, human or AI.

```yaml
nodes:
  - id: procedure:incident-triage-runbook
    label: "Incident Triage Runbook"
    type: Procedure
    attributes:
      steps:
        - "Check connection pool metrics for the affected service"
        - "Check recent deploys in the preceding 24 hours"
        - "Query episodic memory for prior incidents on the same service"
        - "Escalate if unresolved after 30 minutes"
    tags: ["memory-tier:procedural"]
```

**Why this matters:** notice step 3 — the runbook itself instructs the
agent to query episodic memory. That's not a hypothetical; it's exactly
what Section 5's cross-tier query does. Procedural memory in hgai isn't
just "a document with steps" — it's data another query can act on.

---

## 10. Querying Every Tier

All four HQL, one query each, same graph (`agent-memory-demo`):

```yaml
# Session — what's this session about right now?
hql:
  from: agent-memory-demo
  match: { type: hyperedge, relation: session-focus }
  where: { members: { node_id: "session:sess-2026-08-17-a" } }
  return: [members, attributes]
```

```yaml
# Episodic — has this happened before, for this service?
hql:
  from: agent-memory-demo
  match: { type: hyperedge, relation: incident-conclusion }
  where: { members: { node_id: "service:checkout-api" } }
  return: [id, members, attributes, valid_from]
```

```yaml
# Semantic — what does this service depend on?
hql:
  from: agent-memory-demo
  match: { type: hyperedge, relation: depends-on }
  where: { members: { node_id: "service:checkout-api" } }
  return: [members]
```

```yaml
# Procedural — what's the runbook?
hql:
  from: agent-memory-demo
  match: { type: hypernode, id: "procedure:incident-triage-runbook" }
  return: [label, attributes.steps]
```

Four different *kinds* of memory. One query language, one graph, zero
separate integrations.

---

## 11. Cross-Tier Queries — The Real Payoff

The single most valuable query an agent can run isn't within one tier —
it's **across** them: "for this semantic entity, what has episodic memory
already concluded, above a confidence threshold?"

```yaml
shql:
  from: agent-memory-demo
  select: [?conclusion.label, ?edge.attributes.summary, ?edge.attributes.confidence]
  where:
    - node: { bind: "?service", id: "service:checkout-api" }
    - node: { bind: "?session", type: SessionContext }
    - node: { bind: "?evidence", type: Evidence }
    - node: { bind: "?conclusion", type: Conclusion }
    - edge:
        bind: "?edge"
        relation: incident-conclusion
        members:
          - node: { bind: "?service" }
          - node: { bind: "?session" }
          - node: { bind: "?evidence" }
          - node: { bind: "?conclusion" }
    - filter: "?edge.attributes.confidence >= 0.8"
  order_by: ?edge.attributes.confidence
```

Every variable is bound independently up front (type-checked safely at
the top level), and the `edge:` pattern is a pure join constraint — the
safe way to extract multiple unknowns from a multi-member hyperedge.
Run against the data above, this returns the INC-4102 conclusion in one
query — the exact question Section 9's runbook step 3 asks the agent to
answer.

---

## 12. MCP: How an Agent Actually Reads and Writes Memory

Every tier above is reachable through the **same MCP tools** an agent
already knows how to call — no bespoke "memory SDK."

**Writing an episodic memory** (after the agent finishes its analysis):
```json
{
  "jsonrpc": "2.0", "id": 1, "method": "tools/call",
  "params": {
    "name": "hgai_hyperedge_create",
    "arguments": {
      "graph_id": "agent-memory-demo",
      "relation": "incident-conclusion",
      "flavor": "hub",
      "members": [
        {"node_id": "service:checkout-api", "seq": 0},
        {"node_id": "session:sess-2026-08-17-a", "seq": 1},
        {"node_id": "evidence:log-excerpt-4521", "seq": 2},
        {"node_id": "conclusion:pool-size-again", "seq": 3}
      ],
      "attributes": {"confidence": 0.91, "investigator_agent": "claude-agent-sre-v1"},
      "tags": ["memory-tier:episodic", "ai-generated"]
    }
  }
}
```

**Reading it back** — same `hgai_query_execute` tool, any HQL/SHQL query
from Sections 10–11. One tool surface. Read and write. That's the whole
mechanism.

---

## 13. The Loop That Actually Matters

Put Sections 9–12 together and this is the sequence that happens on a
**real second incident**:

1. New session opens: `INC-4521`, same service, elevated latency
2. Procedural memory (Section 9) tells the agent to check episodic memory
   *before* re-deriving anything from scratch
3. The Section 11 query runs — **one query, no re-reading logs, no
   re-running analysis** — and returns the INC-4102 conclusion with 0.88
   confidence
4. The agent starts from "we've seen this, here's what we found last
   time" instead of from zero, and writes its *own* new conclusion back
   when done — extending episodic memory for the next session

The expensive part — a careful multi-source root-cause analysis — happened
**once**. Every future session pays a query, not a re-derivation.

---

## 14. Why hgai Over SQL/RDBMS — For Memory Specifically

A relational schema forces you to decide, in advance, what shape a memory
record has — and memory shapes are inherently **emergent**: new memory
*kinds* appear as an agent gains new capabilities.

```sql
-- Every new kind of memory record needs its own table, its own
-- migration, and its own copy of the same temporal-window logic:
CREATE TABLE incident_conclusion (
    id INT PRIMARY KEY, service_id VARCHAR(40), session_id VARCHAR(40),
    evidence_id VARCHAR(40), conclusion_id VARCHAR(40),
    confidence DECIMAL(3,2), valid_from DATETIME, valid_to DATETIME
);
-- ...next month, a new memory kind ("tool_invocation_outcome",
-- "escalation_decision", ...) means another CREATE TABLE + migration.
```

hgai's answer: a new memory *kind* is a new `relation` value on a
hyperedge — no migration, no new table, no coordination with a DBA. The
temporal-window logic (`at:`) is built into the query engine once, not
re-implemented per table.

---

## 15. Why hgai Over Traditional/RDF Knowledge Graphs — For Memory Specifically

RDF triples are strictly two-way. The Section 7 memory record — one fact,
four participants — needs a manufactured resource and one triple per
fact *about* it:

```turtle
demo:conclusion_4102 a demo:IncidentConclusion ;
    demo:aboutService demo:service_checkout_api ;
    demo:fromSession demo:session_sess_2026_07_27_b ;
    demo:basedOnEvidence demo:evidence_pool_metrics_4102 ;
    demo:hasConclusion demo:conclusion_pool_misconfig ;
    demo:confidence "0.88"^^xsd:decimal .
```

Structurally survivable for *one* fact — but traditional triple stores
are also typically optimized for relatively stable, curated reference
data, not the **high-volume, constantly-churning writes** working and
session memory generate. Reifying every transient scratch note the same
way real reference facts are reified is expensive in exactly the tier
that needs to be cheapest.

---

## 16. Why hgai Over "Just a Vector Database" — For Memory Specifically

Most "AI memory" products today are a single vector index. It answers one
question — *"what's semantically similar to this?"* — and none of these,
all of which the five-tier model needs constantly:

| Question | Vector-only store | hgai |
|---|---|---|
| "What tier is this memory — working, episodic, semantic?" | Not represented | A tag, filterable in every query |
| "Get the CURRENT session state" (exact, not similar) | No native exact/structural lookup | `where: { members: { node_id: ... } }` |
| "What did we know AS OF that prior session?" | No temporal model | `at:` — native PIT |
| "Who concluded this, from what evidence, how confident?" | Usually one flat text blob | Structured, multi-entity, queryable per field |

A vector index is a fine complement for *fuzzy* recall over memory
content — it is not a substitute for representing memory's structure.

---

## 17. Side by Side

| | SQL/RDBMS | RDF/Triple Store | Vector-only | **hgai** |
|---|---|---|---|---|
| N-ary memory facts (4+ participants, one record) | Wide table or bridge table | Manufactured resource, N triples | Flat blob, structure lost | **Native — one hyperedge** |
| New memory kind added later | New table + migration | New predicate set (no migration, but no structure either) | N/A — everything's a blob | **New `relation` value, no migration** |
| Point-in-time ("as of session X") | Hand-written per query | Hand-written per query | Not supported | **Native `at:`** |
| Tier-scoped retrieval | Extra `WHERE tier = ...` column | Extra typing triples | Not representable | **Native `tags`** |
| Agent-writable via one standard interface | Bespoke API | Bespoke API | Usually read-mostly | **MCP-native, same tools throughout** |

---

## 18. Lifecycle & Hygiene

Five tiers, one honest operational note: they should **not** all be kept
forever the same way.

- **Working** — expect to bulk-delete or let go stale; tag by session,
  clean up on session close
- **Session** — typically promoted (interesting parts become episodic) or
  discarded when the session ends, not kept indefinitely as-is
- **Episodic** — durable by default; retention policy is a business
  decision (e.g. "keep 2 years"), not a technical limitation
- **Semantic** — durable, actively maintained ground truth — treat edits
  here with the same care as any system-of-record update
- **Procedural** — durable, versioned like code; changes should be
  deliberate, not agent-driven writes

`tags` and `status` are the mechanism for all of the above — a scheduled
cleanup job is just an HQL query with a `tags` filter and a delete.

---

## 19. What's Real Today vs. Roadmap

No overclaiming — every query and pattern in Sections 4–13 above uses
only what's live:

| Capability | Status |
|---|---|
| Hyperedges, hypernodes, `tags`, free-form `attributes` | **Live** |
| Point-in-time (`at:`) queries in both HQL and SHQL | **Live** |
| HQL and SHQL, including the multi-hop join pattern in Section 11 | **Live** |
| MCP server exposing create/read/query as agent-callable tools | **Live** |
| Automatic tier-lifecycle enforcement (e.g. auto-expiring working memory) | **Not built** — `tags`-based, but the cleanup job itself is something you schedule, not something the platform does for you today |
| Automatic promotion of session memory to episodic on session close | **Not built** — an application-level pattern to implement on top of the live write path, not a built-in behavior |

---

## 20. Architecture Recap

```
┌─────────────────────────────────────────────────────────┐
│  AI Agent (any MCP-compatible model/framework)            │
└───────────────────────────┬─────────────────────────────┘
                             │  MCP (standard tool calls)
┌───────────────────────────▼─────────────────────────────┐
│  HypergraphAI MCP Server                                  │
│  hgai_hypernode_*, hgai_hyperedge_*, hgai_query_execute    │
└───────────────────────────┬─────────────────────────────┘
                             │
┌───────────────────────────▼─────────────────────────────┐
│  One Hypergraph — five tiers, distinguished by tags/type   │
│  working · session · episodic · semantic · procedural      │
└───────────────────────────┬─────────────────────────────┘
                             │
┌───────────────────────────▼─────────────────────────────┐
│  MongoDB (storage)                                         │
└─────────────────────────────────────────────────────────┘
```

One platform. One MCP surface. Five logical tiers as a tagging/typing
convention on top of it — not five separate systems an agent (or a
developer) has to integrate separately.

---

## 21. Getting Started

1. Stand up a graph per application/agent domain (not per session — reuse
   the pattern in Sections 6–9: session/episodic entities *reference into*
   one durable semantic graph)
2. Adopt a `memory-tier` tag convention early (`working` / `session` /
   `episodic` / `semantic` / `procedural`) — it's the whole mechanism
   Section 18's hygiene story depends on
3. Wire your agent's existing tool-calling loop to the MCP server — there
   is no separate memory SDK to learn
4. Start with just two tiers if that's all you need today (semantic +
   episodic covers most "don't re-derive what we already know" value) —
   the model doesn't require adopting all five on day one

For a from-scratch, fully worked engineering walkthrough (clean install
through querying), see `docs/decks/demo-alpha/deck-demo-alpha.md` in this
repository.

---

## 22. Key Takeaways

- AI agent memory isn't one problem — it's (at least) five, and treating
  it as one undifferentiated vector store is why most "AI memory" today
  is noisy and unreliable
- A single hyperedge naturally holds a multi-participant memory record
  (agent + session + evidence + conclusion) that SQL splits across tables
  and RDF splits across reified triples
- Point-in-time queries make "what did we know then" a first-class
  question, not an application-level workaround
- MCP means an agent's memory and an agent's tools are the **same
  interface** — no separate integration to build or maintain
- The payoff isn't storage for its own sake — it's not re-paying the cost
  of reasoning you've already done
