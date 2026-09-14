# HypergraphAI Concepts

## What is a Hypergraph?

An ordinary graph connects pairs of nodes via edges (one edge = exactly two nodes). A **hypergraph** extends this: a **hyperedge** can connect _any number_ of nodes simultaneously — 1, 2, 3, or _n_ nodes in a single edge.

```
Ordinary Graph:        Hypergraph:
  A ─── B               ╭─── A
                        │    B   ← edge/1.2.3
                        ╰─── C
```

This maps naturally to how humans and AI agents actually think about relationships:

- "Jane, Bob, and Carol are siblings" → one hyperedge connecting 3 people
- "The Three Stooges consist of Moe, Larry, and Curly" → one `has-member` hyperedge connecting 4 nodes (group + 3 people)
- "Jane reported to Sam that she saw John in Paris last week in the rain at a café on the Left Bank" → rich edge with multiple participants and attributes

---

## Core Concepts

### Hypernode

A **hypernode** is an entity — a noun in the knowledge graph. Every hypernode is a document with flexible JSON attributes.

```yaml
id: moe-howard
label: Moe Howard
type: Person
attributes:
  first_name: Moe
  last_name: Howard
  born: "1897-06-19"
  died: "1975-05-04"
  role: leader
tags:
  - stooge
  - comedian
status: active
valid_from: "1897-06-19T00:00:00Z"
valid_to: "1975-05-04T23:59:59Z"
```

Key fields:
- `id` — unique identifier within the hypergraph
- `label` — display name
- `type` — entity classification (Person, Organization, Concept, RelationType, ...)
- `attributes` — any JSON document
- `tags` — searchable string tags
- `status` — `active`, `draft`, or `archived`
- `valid_from` / `valid_to` — temporal existential qualifiers (real-world validity)

### Hyperedge

A **hyperedge** is a first-class semantic relationship — it's not just a connection; it's an entity in its own right with its own document attributes, tags, status, and temporal qualifiers.

```yaml
id: edge-stooges-original
relation: has-member
label: Three Stooges Original Lineup
flavor: hub
members:
  - node_id: three-stooges
    role: group
    seq: 0
  - node_id: moe-howard
    role: member
    seq: 1
    order: 1
  - node_id: larry-fine
    role: member
    seq: 2
    order: 2
  - node_id: curly-howard
    role: member
    seq: 3
    order: 3
attributes:
  era: classic
  shorts_count: 97
tags:
  - original
  - classic
status: active
valid_from: "1932-01-01T00:00:00Z"
valid_to:   "1946-12-31T23:59:59Z"
```

Key fields:
- `relation` — the semantic type of the relationship (e.g., `has-member`, `sibling`, `broader`)
- `members` — ordered list of participating hypernodes with optional roles
- `flavor` — relationship pattern (see below)
- `hyperkey` — auto-generated SHA-256 hash ID from (relation + members + graph)
- `valid_from` / `valid_to` — when this relationship was valid in the real world

### Hyperedge Flavors

| Flavor | Description | Example |
|--------|-------------|---------|
| `hub` | One hub node connects to multiple member nodes | Group membership |
| `symmetric` | All members are equivalent | Siblings, colleagues |

A directed chain (A reports to B, B reports to C, ...) is not a single N-ary
fact — each link is its own independent fact, with its own potential
validity window and provenance — so it's modeled as separate two-member
`hub` edges rather than a dedicated flavor. Reasoning across such a chain
(e.g. "is A transitively contained in C?") is a relation-level property
(declared via an `owl:transitive` axiom, see Semantic Inferencing below),
not a per-edge flavor.

### Hypergraph

A **hypergraph** is a named container for hypernodes and hyperedges. It can be:
- **Instantiated** — a physical collection stored in MongoDB
- **Logical** — a virtual composition of other hypergraphs (union view)

Logical hypergraphs enable querying across multiple graphs as if they were one.

### Hyperkey

Every hyperedge is assigned a **hyperkey** — a deterministic SHA-256 hash computed from:
1. The normalized `relation` type
2. Sorted list of member node IDs
3. The parent `hypergraph_id`

This allows deduplication and consistent referencing of the same semantic relationship.

---

## Temporal Support

HypergraphAI natively supports **point-in-time (PIT) queries**. Every hypernode and hyperedge has:
- `valid_from` — when the entity/relationship came into existence in the real world
- `valid_to` — when it ceased to exist

You can query the state of a hypergraph at any specific moment:

```yaml
shql:
  from: presidents
  at: "1963-11-22T00:00:00Z"
  where:
    - edge:
        bind: ?e
        relation: holds-office
  select:
    - ?e.members
```

This returns whoever held office on November 22, 1963 — a PIT query across all `holds-office` hyperedges that were valid on that date.

---

## Semantic Inferencing

Relation semantics — which relations are transitive, symmetric, each other's inverse, or broader/narrower than one another — are never hardcoded. They're declared as ordinary **axiom hyperedges** asserting one of a small, fixed set of control-vocabulary relations between `RelationType` hypernodes:

| Axiom relation | Meaning |
|---|---|
| `owl:transitive` | This relation's facts form a transitive chain (A→B, B→C implies A→C) |
| `owl:symmetric` | This relation's facts are bidirectional (A→B implies B→A) |
| `owl:inverse-of [R, R']` | Every fact on relation R also implies the reverse fact on relation R' |
| `skos:broaderTransitive` / `narrowerTransitive` | This relation is narrower/broader than another — facts project up through the hierarchy |

The inference engine (`hgai/core/inference.py`) recognizes these strings; it never hardcodes a specific domain relation, so adding a new inference rule is a data change (assert an axiom hyperedge), not a code change. Computed live at query time — nothing inferred is ever persisted, and inferred results are tagged `_inferred: true` (plus `_source_edge`/`_axiom` for axiom expansion, or `_transitive`/`_transitive_path` for transitive-closure derivations). `owl:transitive` is expanded the same general way as the other three axioms — a whole-relation closure computed once per relation rather than per edge — so it surfaces in any `infer: true` query, not only a targeted two-endpoint check.

Enable inferencing per query with `infer: true`:

```yaml
shql:
  from: taxonomy
  infer: true
  where:
    - edge:
        bind: ?e
        relation: broader
  select:
    - ?e.members
    - ?e._inferred
```

See the [README's Inferencing section](../README.md#inferencing) for the full mechanics and worked examples.

---

## SHQL — Semantic Hypergraph Query Language

SHQL is HypergraphAI's query language — a SPARQL-inspired, YAML-based pattern-matching language. Every query starts with the `shql:` key, matches `node`/`edge` patterns against `?variable` bindings (a variable shared across patterns is an implicit join), and projects fields with `select:`.

### Basic Structure

```yaml
shql:
  from: <graph-id>           # Required: graph ID, list of IDs, or mesh dot-refs
  at: <ISO-8601 datetime>    # Optional: point-in-time qualifier
  where:                      # Ordered list of patterns
    - node: { ... }            # hypernode pattern
    - edge: { ... }            # hyperedge pattern
    - filter: "<expression>"   # expression filter, e.g. "?var.field < 10"
    - optional: [ ... ]        # left outer join — patterns that may not match
    - union:                   # set union of alternative branches
        - patterns: [ ... ]
  select:                     # Fields to return
    - ?var                     # whole bound entity
    - ?var.field                # single field
    - "*"                      # everything (default)
  order_by: ?var.field        # Optional: sort key(s) — a single field or a list for
                               # multi-key sort; each may end in " asc"/" desc" (default asc)
  limit: 500                  # Optional: max results (default 500)
  offset: 0                   # Optional: pagination offset
  distinct: true               # Optional: deduplicate result rows
  infer: true                  # Optional: opt-in axiom expansion + transitive closure
  aggregate:                   # Optional: aggregation, computed pre-pagination
    count: true
    group_by: <projected-row-key>
  as: <alias>                  # Optional: result alias name
```

A node or edge pattern binds a matched entity to a `?variable`; the same variable used in two different patterns is an implicit join — both patterns must agree on the same entity. See the [README's SHQL section](../README.md#shql--semantic-hypergraph-query-language) for the full Node/Edge Pattern syntax, FILTER expressions, and a dozen worked examples.

### Multi-Graph Composition

```yaml
shql:
  from:
    - graph-1
    - graph-2
    - graph-3
  where:
    - node: ?n
  select: ["*"]
```

Logical hypergraphs automatically expand their `composition` list, so you can also:

```yaml
shql:
  from: my-logical-graph   # Expands to all composed physical graphs
  where:
    - edge: ?e
```

### Mesh Dot-Notation

Query graphs on remote mesh servers directly from `from:` using dot-notation: `{mesh_id}.{server_id}.{graph_id}`

Use `*` as a wildcard in any position:

| `from:` value | Meaning |
|---|---|
| `abc.srv1.alpha` | Mesh `abc`, server `srv1`, graph `alpha` |
| `abc.*.alpha` | Mesh `abc`, all servers that have graph `alpha` |
| `abc.srv1.*` | Mesh `abc`, server `srv1`, all its graphs |
| `abc.*.*` | All servers and all graphs in mesh `abc` |

Dot-refs can be mixed with local graph IDs in the same `from:` list:

```yaml
shql:
  from:
    - local-graph                      # local graph (no dots)
    - my-mesh.server-a.remote-graph    # specific graph on one server
    - my-mesh.*.shared-graph           # same graph across all servers
  where:
    - node:
        bind: ?n
  select:
    - ?n.id
    - ?n.label
    - ?n._mesh_server_id               # added to each result from a mesh server
```

**Note:** graph IDs, server IDs, and mesh IDs must not contain `.` — it is reserved as the dot-notation delimiter.

---

## RBAC — Role-Based Access Control

| Role | Description |
|------|-------------|
| `admin` | Full system access — accounts, all graphs, all operations |
| `user` | Read/write to permitted graphs |
| `agent` | API/MCP access for AI agents (same as user, typically) |
| `readonly` | Read-only access |

Permissions can be further scoped per account:
```json
{
  "permissions": {
    "graphs": ["graph-a", "graph-b"],
    "operations": ["read", "query"]
  }
}
```

---

## MCP Integration

All HypergraphAI operations are exposed as **MCP (Model Context Protocol) server tools** at `/mcp/`. AI agents (Claude, etc.) can use these tools to:

- Read and write hypernodes and hyperedges
- Execute SHQL queries
- Manage hypergraphs
- Build and traverse semantic knowledge structures

```json
// MCP client configuration
{
  "mcpServers": {
    "hgai": {
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Authorization": "Bearer <token>"
      }
    }
  }
}
```

Available MCP tool groups:
- `hgai_hypergraph_*` — Graph management
- `hgai_hypernode_*` — Node CRUD
- `hgai_hyperedge_*` — Edge CRUD
- `hgai_query_*` — SHQL query execution
- `hgai_infer_*` — Inference primitives (`check_transitive`, axiom expansion) without composing a full query
- `hgai_media_*` — Media asset management
- `hgai_mesh_*` — Cross-server mesh federation
- `hgai_space_*` — Space management

---

## Spaces (Multi-Tenant Namespaces)

**Spaces** are organizational containers that group hypergraphs for multi-tenant deployments. Each space has a set of **members** with assigned roles that control what operations they can perform.

### Space Roles

| Role     | Operations Permitted                                              |
|----------|------------------------------------------------------------------|
| `owner`  | read, write, delete, admin, query, export, import + manage space |
| `admin`  | read, write, delete, query, export, import + manage members      |
| `member` | read, write, query, export, import                               |
| `viewer` | read, query, export                                              |

### Access Resolution

Space membership is the **sole gate** for space-scoped graphs — a `permissions.graphs` wildcard (e.g. `["*"]`) does not grant access to a space's graphs on its own. When a request arrives, access is checked in this order:

1. **Global admin role** — full access to everything
2. **Space membership** — when the graph belongs to a space, the account must be a member of that space; non-members are rejected regardless of `permissions.graphs`
3. **Direct account permissions** — `permissions.graphs` list or `"*"` wildcard, applies only to unowned (non-space) graphs

This ensures a `["*"]` permissions wildcard cannot leak across tenant boundaries.

Graph IDs are unique **within a space**. Two spaces can both contain a graph named `my-graph` with no conflict. The flat `/graphs/*` endpoints address only unowned graphs. Space-scoped graphs live at `/spaces/{space_id}/graphs/{graph_id}`.

### Example: Creating Space-Scoped Graphs

```bash
# Create a space
curl -X POST /api/v1/spaces \
  -H "Authorization: Bearer <token>" \
  -d '{"id": "research-team", "label": "Research Team"}'

# Add a member
curl -X POST /api/v1/spaces/research-team/members \
  -d '{"username": "alice", "role": "member"}'

# Create a graph inside the space
curl -X POST /api/v1/spaces/research-team/graphs \
  -d '{"id": "my-graph", "label": "Research Graph"}'

# Full node/edge CRUD
curl /api/v1/spaces/research-team/graphs/my-graph/nodes
```

### Querying Space-Scoped Graphs

Use `space_id/graph_id` slash notation in SHQL `from:` fields:

```yaml
shql:
  from: research-team/my-graph
  where:
    - edge: ?e
```

```yaml
shql:
  from:
    - research-team/my-graph
    - engineering/my-graph    # same ID, different space
    - shared-graph            # unowned graph
```

For remote space-scoped graphs via mesh dot-notation, use 4 components:

```
mesh.server.research-team.my-graph
```
