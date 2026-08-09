---
title: "HypergraphAI — Developer Implementation Deck"
description: "Hands-on cookbook for AI software engineers implementing agent context/memory on HypergraphAI: quickstart, integration paths, query recipes, agent-loop patterns, and gotchas"
---

# HypergraphAI for AI Software Engineers

### How to Implement Agent Context & Memory on HypergraphAI

*A hands-on cookbook, not a strategy deck. Every command and query below
has been checked against the actual codebase — copy-paste, don't
transcribe.*

**Format:** each `---` is one slide. Open in Marp/reveal-md/Slidev, or read
top-to-bottom.

---

## Slide 1 — Mental Model in 60 Seconds

# Three Primitives You'll Actually Write Code Against

```python
# hypernode — an entity
{"id": "task:deploy-checkout-v2", "label": "Deploy checkout v2",
 "type": "Task", "attributes": {"priority": "high"}}

# hyperedge — an n-ary, first-class relationship (not a pointer)
{"relation": "decision:blocked-by", "flavor": "hub",
 "members": [
   {"node_id": "task:deploy-checkout-v2", "seq": 0},
   {"node_id": "task:migrate-db-schema",  "seq": 1},
 ],
 "attributes": {"rationale": "schema migration must land first"}}

# hypergraph — the named container both live in
```

If you've modeled a fact that needed a join table or a synthetic "event"
node to express in a property graph, that fact is probably **one
hyperedge** here. That's the whole pitch — everything else in this deck is
"how do I actually use that."

---

## Slide 2 — Quickstart

# Running Server in Under 2 Minutes

```bash
git clone <repo-url> && cd hgai
cp .env.example .env
docker compose up -d

curl http://localhost:8000/health
# {"status": "ok", "server_id": "...", "version": "0.1.0"}

docker compose exec hgai python scripts/seed_data.py   # optional sample data
```

Default admin: `admin` / `pwd357` — **rotate this immediately**, it's a
literal default in `hgai/config.py`, not a placeholder.

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -d "username=admin&password=pwd357" \
  -H "Content-Type: application/x-www-form-urlencoded"
# → {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 28800}
```

**Port gotcha:** Docker Compose maps the app to **8000**. The `hgai` CLI's
own default (`HGAI_PORT`, no Docker) is **8357**. Check which one you're
actually running before copy-pasting a command that hardcodes a port.

---

## Slide 3 — Three Ways to Talk to It

# Pick the Integration Path That Matches Your Caller

| Path | Who it's for | Auth |
|---|---|---|
| **REST API** (`/api/v1/*`) | Your own backend code, scripts, CI | JWT (user) or API key (service) |
| **MCP** (`/mcp/`) | An AI agent framework (Claude, or anything MCP-speaking) | API key, bearer header |
| **hgai-shell** (CLI) | You, interactively, iterating on schema/queries | JWT via `connect` |

**There is no bundled Python SDK today.** You'll either call the REST API
directly (`httpx`/`requests`), use an MCP client library, or shell out to
`hgai-shell` for interactive work. This deck's recipes are written as
plain `httpx` calls so they work regardless of your framework.

---

## Slide 4 — Recipe: A Minimal Python Client

# The Wrapper You'll Actually Write

```python
import httpx

class HGAIClient:
    def __init__(self, base_url: str, token: str):
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )

    def create_node(self, graph: str, **fields) -> dict:
        r = self._http.post(f"/api/v1/graphs/{graph}/nodes", json=fields)
        r.raise_for_status()
        return r.json()

    def create_edge(self, graph: str, **fields) -> dict:
        r = self._http.post(f"/api/v1/graphs/{graph}/edges", json=fields)
        r.raise_for_status()
        return r.json()

    def query(self, hql_yaml: str, use_cache: bool = True) -> dict:
        r = self._http.post("/api/v1/query",
            json={"hql": hql_yaml, "use_cache": use_cache})
        r.raise_for_status()
        return r.json()

client = HGAIClient("http://localhost:8000", token="eyJ...")
```

Fifteen lines gets you CRUD + query. Everything else in this deck builds
on this shape — swap in an async client (`httpx.AsyncClient`) if your
agent loop is async, which it probably is.

---

## Slide 5 — Recipe: Modeling Your Agent's Memory

# Design the Schema Before You Write the Loop

Worked example — a coding agent that makes decisions and touches files:

| Node type | Example `id` | Purpose |
|---|---|---|
| `Task` | `task:deploy-checkout-v2` | A unit of work the agent is executing |
| `Decision` | *(usually a hyperedge, not a node — see below)* | A choice the agent made, with rationale |
| `Artifact` | `file:checkout/api.py` | A code artifact the agent read or changed |
| `Agent` | `agent:deploy-advisor` | The acting agent itself, as a queryable entity |

| Relation (hyperedge) | Flavor | Members | Use |
|---|---|---|---|
| `decision:made` | `hub` | agent, task, artifact(s) | "who decided what, touching what" |
| `decision:blocked-by` | `direct` | blocking task, blocked task | dependency chains |
| `task:completed` | `hub` | agent, task | completion events, temporally bounded |

**Rule of thumb:** if you're about to create a node whose only purpose is
to be pointed at by exactly one edge, you probably want a hyperedge with
richer `attributes` instead — that's the whole reason hyperedges exist.

---

## Slide 6 — Recipe: Write Path (Agent Asserts a Fact)

# Capture the Decision, Not Just the Outcome

```python
client.create_edge("ops-memory",
    relation="decision:made",
    flavor="hub",
    members=[
        {"node_id": "agent:deploy-advisor", "seq": 0},
        {"node_id": "task:deploy-checkout-v2", "seq": 1},
        {"node_id": "region:us-east-1", "seq": 2},
    ],
    attributes={
        "rationale": "lowest observed p99 latency in last 24h window",
        "confidence": 0.82,
    },
    valid_from="2026-08-08T14:32:00Z",
)
```

Equivalent `curl`:
```bash
curl -X POST http://localhost:8000/api/v1/graphs/ops-memory/edges \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"relation": "decision:made", "flavor": "hub",
       "members": [{"node_id": "agent:deploy-advisor", "seq": 0},
                    {"node_id": "task:deploy-checkout-v2", "seq": 1}],
       "attributes": {"rationale": "...", "confidence": 0.82}}'
```

The `id` is optional — omit it and the platform derives a deterministic
`hyperkey` (SHA-256 of relation + sorted members + graph), so re-asserting
the *same* fact twice is naturally idempotent rather than a duplicate row.

---

## Slide 7 — Recipe: Read Path — HQL Cookbook

# Filter/Aggregate Queries You'll Write Constantly

**Recent decisions for a task:**
```yaml
hql:
  from: ops-memory
  match: { type: hyperedge, relation: "decision:made" }
  where: { members: { node_id: "task:deploy-checkout-v2" } }
  return: [id, attributes, valid_from]
  as: recent_decisions
```

**Only the agent's own decisions (positional match — first member is the agent):**
```yaml
hql:
  where:
    members:
      seq: 0
      node_id: "agent:deploy-advisor"
```
`seq` + another member field together bind to the *same* array slot
(compiles to Mongo `$elemMatch`) — this is "first member is X," not "X is
a member somewhere," which matters the moment an edge has 3+ members.

**Count decisions by confidence bucket:**
```yaml
hql:
  from: ops-memory
  match: { type: hyperedge, relation: "decision:made" }
  aggregate: { count: true, group_by: "attributes.confidence" }
```

---

## Slide 8 — Recipe: Read Path — SHQL Cookbook

# Multi-Hop Joins Without Writing the Join Yourself

**"What tasks were blocked, and by what, with the blocker's owner?"**
```yaml
shql:
  from: ops-memory
  where:
    - edge: ?block
      relation: "decision:blocked-by"
      members:
        - { bind: ?blocker, seq: 0 }
        - { bind: ?blocked, seq: 1 }
    - node: ?blocker_node
      bind: ?blocker
  select: [?blocked, ?blocker, ?blocker_node.attributes.owner]
```

**OPTIONAL — tasks with or without a recorded decision:**
```yaml
shql:
  where:
    - node: ?t
      node_type: Task
    - optional:
        - edge: ?d
          relation: "decision:made"
          members: [{ node_id: ?t }]
  select: [?t.id, ?d.attributes.rationale]
```

`?d.attributes.rationale` comes back `null` for tasks with no decision
edge yet — no separate "does this exist" query needed first.

---

## Slide 9 — Recipe: Temporal Recall

# "What Did We Know When We Decided This?"

Every query — HQL or SHQL — takes an optional `at:` for point-in-time:

```yaml
shql:
  from: ops-memory
  at: "2026-08-08T14:35:00Z"        # moments after the decision above
  where:
    - edge: ?d
      relation: "decision:made"
      members: [{ node_id: "task:deploy-checkout-v2" }]
  select: [?d.attributes.rationale, ?d.attributes.confidence]
```

This isn't a bolted-on audit log query — `valid_from`/`valid_to` are real
fields on every node and edge, and the PIT clause is threaded through the
same query engine as every other filter. Use this for "replay the state
the agent reasoned from," not just "when was this edited."

**Known limit:** transitive-relation walks (`hgai/core/inference.py`)
don't yet thread `pit` through multi-hop traversal — direct PIT filtering
on `match`/`where` (as above) works today; PIT-aware transitive closure
does not yet.

---

## Slide 10 — Wiring Into an Agent Loop

# Recall → Act → Record, as an Explicit Pattern

```python
async def agent_turn(client: HGAIClient, task_id: str):
    # 1. RECALL — pull relevant prior decisions before reasoning
    context = client.query(f"""
      hql:
        from: ops-memory
        match: {{ type: hyperedge, relation: "decision:made" }}
        where: {{ members: {{ node_id: "{task_id}" }} }}
        return: [attributes, valid_from]
    """)

    # 2. ACT — the agent reasons using `context["items"]` as grounding
    decision = run_agent_reasoning(task_id, prior_context=context["items"])

    # 3. RECORD — the new decision becomes queryable for the *next* turn
    client.create_edge("ops-memory",
        relation="decision:made", flavor="hub",
        members=[{"node_id": "agent:deploy-advisor", "seq": 0},
                 {"node_id": task_id, "seq": 1}],
        attributes={"rationale": decision.rationale,
                     "confidence": decision.confidence})
```

The important property: turn N+1's "recall" step sees turn N's "record"
step — memory persists *because it's a real write*, not because it's
still in the same context window.

---

## Slide 11 — MCP Integration for Agent Frameworks

# Native Tool Access, No Custom Integration Layer

Point an MCP-compatible client (Claude Desktop, or your own agent
framework's MCP client) at the server directly:

```json
{
  "mcpServers": {
    "hgai": {
      "url": "http://localhost:8000/mcp/",
      "headers": { "Authorization": "Bearer <your-api-key>" }
    }
  }
}
```

The agent now has 25 tools available natively —
`hgai_hyperedge_create`, `hgai_query_execute`, `hgai_mesh_query`, etc. —
without you writing a single tool-calling wrapper. The recall/record
pattern from Slide 10 becomes tool calls the model makes itself:

```
Agent: [calls hgai_query_execute with the HQL from Slide 7]
Agent: [reasons over the returned decisions]
Agent: [calls hgai_hyperedge_create to record its new decision]
```

**Gotcha carried over from the architect track:** API keys are full-admin,
unscoped. If you don't want an agent able to delete other teams' graphs,
put a scoping proxy in front of the MCP endpoint — there's no config flag
for this today.

---

## Slide 12 — Testing Your Integration

# Validate Before You Execute, Iterate in the Shell

**Dry-run a query without executing it:**
```bash
curl -X POST http://localhost:8000/api/v1/query/validate \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"hql": "hql:\n  from: ops-memory\n  match: {type: hyperedge}"}'
# → {"valid": true, "errors": [], "parsed": {...}}
```

**Interactive iteration with `hgai-shell`** — much faster than curl/Postman
round-tripping while you're still figuring out a schema:
```
$ hgai-shell
> connect http://localhost:8000 -u admin -p
> use ops-memory
> create node          # opens a YAML editor for you
> query -f my-query.hql
> export -o fixture.yaml   # snapshot current state as a test fixture
```

**In your own test suite:** the query engines are pure functions under the
HTTP layer (`hgai_module_hql/engine.py`, `hgai_module_shql/engine.py`) —
you can unit-test query-building logic without a running MongoDB by
importing them directly, the same way this project's own test suite does.

---

## Slide 13 — Gotchas You Will Hit

# Save Yourself the Debugging Session

| Gotcha | What actually happens | What to do |
|---|---|---|
| No `hyperedge_update` MCP tool | Only create/delete are exposed to agents via MCP | Use REST `PUT /graphs/{g}/edges/{id}` from your own backend, or delete+recreate from the agent |
| API keys are full-admin | No per-key scoping exists | Front the MCP endpoint with your own scoping proxy if agents need narrower access |
| Single member-field filters are "contains anywhere" | `where: {members: {node_id: X}}` matches X at *any* position | Add `seq` alongside it if you need a specific position — see Slide 7 |
| Query cache is graph-scoped, not query-scoped | A write to graph `X` evicts *all* cached queries touching `X`, not just the one you changed | Fine for correctness; don't assume fine-grained cache hits under heavy write load |
| Hyperkey is derived from relation + members + graph | Re-creating the "same" edge with different `attributes` but identical members is deduplicated at the DB layer | Pass an explicit `id` if you actually want two distinct edges for the same relation+members |
| Docker vs local default ports differ | 8000 (compose) vs 8357 (`hgai` CLI default) | Check `HGAI_PORT`/your compose file before assuming a port |

---

## Slide 14 — Federation for Developers

# Querying Across Servers Without an ETL Job

Dot-notation in `from:` addresses a remote graph through a registered
mesh, fanned out concurrently (not sequentially) under the hood:

```yaml
hql:
  from: team-mesh.server-b.other-teams-memory   # graph on a specific remote server
  match: { type: hyperedge, relation: "decision:made" }
```

```yaml
hql:
  from: team-mesh.*.ops-memory   # same graph name, every server in the mesh
  return: [id, "_mesh_server_id"]   # tells you which server each result came from
```

Useful pattern: keep each team's agent memory on its own server/graph, and
only federate a query when you actually need cross-team recall — you're
not forced into one physical database to get this.

---

## Slide 15 — Local Dev Loop

# Fast Iteration Without Re-Deploying

```bash
# Auto-reload on code changes (local dev, not Docker)
HGAI_RELOAD=true hgai --mongo-connection mongodb://localhost:27017

# Or via env var in .env
HGAI_RELOAD=true
```

**Seeding a repeatable dataset for local testing:**
```bash
python scripts/seed_data.py     # baseline hello-world graph
```

**Round-tripping a schema you're iterating on:**
```
hgai-shell> export -o snapshot.yaml     # save current state
hgai-shell> import -f snapshot.yaml     # restore it after wiping a test graph
```

This import/export pair is also how you'd move a schema you designed
locally into a shared dev/staging graph — no migration tooling required
for early-stage schema iteration.

---

## Slide 16 — Performance Tips While You're Modeling

# Design With the Indexes in Mind, Not Against Them

Indexed today: `hypergraph_id+status`, `hypergraph_id+type` (nodes),
`hypergraph_id+relation`, `members.node_id` (edges), `tags` (multikey),
and `valid_from`/`valid_to` (sparse, PIT). Anything else you filter on
inside `attributes.*` is **not** indexed — every `where: {attributes.x: ...}`
filter is a collection scan today.

**Practical guidance:**
- Put your hottest filter fields (`type`, `relation`, `status`, `tags`,
  `node_id` membership) where they're already indexed — don't bury them
  inside `attributes` if you'll filter on them constantly
- Batch imports (`import -f`) beat one-node-at-a-time creates for seeding
  — same underlying store calls, far fewer round trips
- Query caching is on by default (`HGAI_CACHE_ENABLED`, 300s TTL) — pass
  `use_cache: false` when testing write-then-immediately-read-back logic,
  or you may be reading a cache entry from before your write in fast test
  loops (graph-scoped invalidation is synchronous per-write, but is scoped
  to whole-graph, not the specific query you just ran)

---

## Slide 17 — Cheat Sheet

# Quick Reference

**REST**
```
POST /api/v1/auth/token                   Login → JWT
GET/POST/PUT/DELETE /api/v1/graphs/{id}/{nodes|edges}[/{id}]
POST /api/v1/query          {"hql": "..."}      Execute HQL
POST /api/v1/query/validate {"hql": "..."}      Dry-run HQL
POST /api/v1/shql/query     {"shql": "..."}     Execute SHQL
POST /api/v1/shql/validate  {"shql": "..."}     Dry-run SHQL
```

**HQL skeleton**
```yaml
hql:
  from: <graph>[/space]         # or a list; or mesh dot-notation
  at: "<ISO8601>"               # optional, point-in-time
  match: { type: hyperedge|hypernode|any, relation: ..., flavor: ... }
  where: { <field>: <value|operator-dict>, members: { seq: N, node_id: ... } }
  return: [<fields>]
  aggregate: { count: true, group_by: <field> }
  limit: N | skip: N | distinct: true
  as: <alias>
```

**SHQL skeleton**
```yaml
shql:
  from: <graph(s)>
  at: "<ISO8601>"
  where:
    - node: ?v | { bind: ?v, id: ..., node_type: ... }
    - edge: ?v | { bind: ?v, relation: ..., members: [...] }
    - filter: { <OP>: [...] }
    - optional: [ ...sub-patterns... ]
    - union: [ [...branch A...], [...branch B...] ]
  select: [?v, ?v.field, ?v.nested.path]
  order_by: ?v.field | limit: N
```

**MCP tool families:** `hgai_hypergraph_*` `hgai_hypernode_*`
`hgai_hyperedge_*` (no `_update`) `hgai_query_*` `hgai_mesh_*` `hgai_space_*`

---

## Slide 18 — Where to Go Deeper

# This Deck Is a Cookbook, Not the Full Reference

- `README.md` — full API reference, HQL/SHQL language spec, MongoDB index
  reference, mesh/performance internals
- `docs/api-reference.md` — endpoint-by-endpoint REST reference
- `docs/module-development.md` — writing your own `hgai_module_*` if you
  need custom relation types or connectors
- `docs/decks/demo-alpha/` — a full worked demo with real import data and
  14 phases of HQL/SHQL query examples against it
- `notes/decks/hgai-tech-architect.md` — the architecture/security/ops
  deck if you need to answer "should we adopt this" questions, not just
  "how do I write against it"

**Fastest path to a working pilot:** Slide 2 (quickstart) → Slide 5 (model
your schema) → Slide 10 (wire the recall/record loop) → Slide 13 (read the
gotchas *before* you hit them, not after).
