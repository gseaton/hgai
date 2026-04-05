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
| `direct` | Directed from first to last member | Reports-to chain |
| `transitive` | A→B and B→C implies A→C | Ancestry, containment |
| `inverse-transitive` | Inverse of transitive | Descendant-of |

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
hql:
  from: presidents
  at: "1963-11-22T00:00:00Z"
  match:
    type: hyperedge
    relation: holds-office
  return:
    - members
```

This returns whoever held office on November 22, 1963 — a PIT query across all `holds-office` hyperedges that were valid on that date.

---

## Semantic Inferencing (SKOS)

HypergraphAI supports SKOS (Simple Knowledge Organization System) semantic relationships for inferencing:

| SKOS Relation | Meaning |
|---------------|---------|
| `broader` | This concept is more specific than the broader concept |
| `narrower` | This concept subsumes the narrower concept |
| `related` | Associative (non-hierarchical) relationship |

These relationships support **transitive closure** — if A is broader than B, and B is broader than C, then A is transitively broader than C.

Enable inferencing in HQL with `infer: true`:

```yaml
hql:
  from: taxonomy
  match:
    type: hypernode
    id: mammal
  infer: true
  return:
    - id
    - label
    - _inferred
```

---

## HQL — Hypergraph Query Language

HQL is a YAML-based declarative query language. Every query starts with the `hql:` key.

### Basic Structure

```yaml
hql:
  from: <graph-id>          # Required: graph ID, list of IDs, or mesh dot-refs
  at: <ISO-8601 datetime>   # Optional: point-in-time qualifier
  match:                     # Optional: entity matching conditions
    type: hypernode|hyperedge|any
    relation: <relation>     # (hyperedge only)
    flavor: <flavor>         # (hyperedge only)
    node_type: <type>        # (hypernode only)
    nodes:                   # (hyperedge only) filter by member nodes
      - <node-id>
  where:                     # Optional: additional filters
    tags:
      - <tag>
    status: active
    attributes.<path>: <value>
  return:                    # Optional: fields to return (* for all)
    - id
    - label
    - members
    - attributes
  as: <alias>               # Optional: result alias name
  limit: 500                # Optional: max results
  skip: 0                   # Optional: pagination offset
  aggregate:                 # Optional: aggregation operations
    count: true
    group_by: <field>
```

### Multi-Graph Composition

```yaml
hql:
  from:
    - graph-1
    - graph-2
    - graph-3
  match:
    type: hypernode
  return: ["*"]
```

Logical hypergraphs automatically expand their `composition` list, so you can also:

```yaml
hql:
  from: my-logical-graph   # Expands to all composed physical graphs
  match:
    type: hyperedge
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
hql:
  from:
    - local-graph                      # local graph (no dots)
    - my-mesh.server-a.remote-graph    # specific graph on one server
    - my-mesh.*.shared-graph           # same graph across all servers
  match:
    type: hypernode
  return:
    - id
    - label
    - _mesh_server_id                  # added to each result from a mesh server
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
- Execute HQL queries
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
- `hgai_query_*` — HQL query execution
