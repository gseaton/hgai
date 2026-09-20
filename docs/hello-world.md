# Hello, World! — Your First HypergraphAI Hypergraph

This guide walks you through creating a simple hypergraph about the Three Stooges comedy group, demonstrating hypernodes, hyperedges, semantic relations, and temporal queries.

---

## Prerequisites

HypergraphAI server running locally:
```bash
docker-compose up -d
# or
uvicorn hgai.main:app --reload
```

You can use the **Web UI**, the **hgai shell**, or the **REST API**. All three approaches are shown.

---

## Step 1: Create a Hypergraph

The hypergraph is the container for your knowledge.

### Web UI
1. Go to `http://localhost:8000/ui/`
2. Log in as `admin` / `pwd357`
3. Click **Hypergraphs** → **New Hypergraph**
4. Fill in: ID = `hello-world`, Label = `Hello, World!`
5. Click **Save**

### hgai Shell
```
hgai> connect http://localhost:8000 -u admin
hgai> create graph
  id: hello-world
  label: Hello, World!
  description: A simple example hypergraph
  tags: [example, demo]
---
```

### REST API
```bash
curl -X POST http://localhost:8000/api/v1/graphs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "hello-world",
    "label": "Hello, World!",
    "description": "A simple example hypergraph",
    "tags": ["example", "demo"]
  }'
```

---

## Step 2: Create Hypernodes (Entities)

### The Group Node

```bash
curl -X POST http://localhost:8000/api/v1/graphs/hello-world/nodes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "three-stooges",
    "label": "Three Stooges",
    "type": "Group",
    "attributes": {
      "formed": 1925,
      "genre": "comedy",
      "medium": ["film", "television", "stage"]
    },
    "tags": ["entertainment", "comedy", "classic"]
  }'
```

### The Person Nodes

```bash
# Moe Howard
curl -X POST http://localhost:8000/api/v1/graphs/hello-world/nodes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "moe-howard",
    "label": "Moe Howard",
    "type": "Person",
    "attributes": {
      "first_name": "Moe",
      "last_name": "Howard",
      "born": "1897-06-19",
      "died": "1975-05-04",
      "role": "leader"
    },
    "tags": ["stooge", "comedian"],
    "valid_from": "1897-06-19T00:00:00Z",
    "valid_to": "1975-05-04T23:59:59Z"
  }'
```

Repeat for `larry-fine`, `curly-howard`, and `shemp-howard`.

> **Want ready-made data instead?** The repository ships example hypergraphs as ordinary export files in `scripts/seeds/` (`hello-world` — Stooges, Rat Pack and Beatles lineups — and `eden`, a small family tree). Load them with:
> ```bash
> python scripts/seed_data.py            # docker-compose exec hgai python scripts/seed_data.py
> ```
> or import a file from **Hypergraphs → Import**. The seeds use ids such as `person:moe` and `rel:member`, so the queries in *this* tutorial (which use `moe-howard`, `has-member`, …) apply to the data you create by hand, not to the seed. If you have loaded the seeds, give the graph you create here a different ID in Step 1 (for example `hello-tutorial`) so the two don't mix; the SHQL examples in the README and Help use the seed data.

---

## Step 3: Create Hyperedges (Semantic Relationships)

### Original Lineup (1932–1946): Moe, Larry, Curly

Note: This single hyperedge connects **4 nodes** simultaneously — the group and 3 members.

```bash
curl -X POST http://localhost:8000/api/v1/graphs/hello-world/edges \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "edge-stooges-original",
    "relation": "has-member",
    "label": "Three Stooges Original Lineup",
    "flavor": "hub",
    "members": [
      {"node_id": "three-stooges", "role": "group",  "seq": 0},
      {"node_id": "moe-howard",    "role": "member", "seq": 1, "order": 1},
      {"node_id": "larry-fine",    "role": "member", "seq": 2, "order": 2},
      {"node_id": "curly-howard",  "role": "member", "seq": 3, "order": 3}
    ],
    "attributes": {"era": "classic", "shorts_count": 97},
    "tags": ["original", "classic"],
    "valid_from": "1932-01-01T00:00:00Z",
    "valid_to":   "1946-12-31T23:59:59Z"
  }'
```

### Siblings Relationship (Symmetric)

Moe, Shemp, and Curly are all Horwitz brothers — a symmetric hyperedge.

```bash
curl -X POST http://localhost:8000/api/v1/graphs/hello-world/edges \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "relation": "sibling",
    "label": "Horwitz Brothers",
    "flavor": "symmetric",
    "members": [
      {"node_id": "moe-howard",   "role": "sibling", "seq": 1},
      {"node_id": "shemp-howard", "role": "sibling", "seq": 2},
      {"node_id": "curly-howard", "role": "sibling", "seq": 3}
    ],
    "attributes": {"family": "Horwitz"},
    "tags": ["family", "siblings"]
  }'
```

---

## Step 4: Query Your Hypergraph

Queries are written in **SHQL** — match `node`/`edge` patterns against `?variable` bindings, then `select:` the fields you want. See [concepts.md](concepts.md) and the [README's SHQL section](../README.md#shql--semantic-hypergraph-query-language) for the full language reference.

### Who were the Three Stooges? (All eras)

```yaml
shql:
  from: hello-world
  where:
    - edge:
        bind: ?e
        relation: has-member
  select:
    - ?e.id
    - ?e.relation
    - ?e.members
    - ?e.attributes
```

### Point-in-Time: Who were the Stooges in 1940?

```yaml
shql:
  from: hello-world
  at: "1940-06-01T00:00:00Z"
  where:
    - edge:
        bind: ?e
        relation: has-member
  select:
    - ?e.members
    - ?e.attributes
```

**Result**: Only the `edge-stooges-original` edge matches (Moe, Larry, Curly) because it was valid from 1932 to 1946. The Shemp era and comeback era edges are excluded.

### Point-in-Time: Who were the Stooges in 1950?

```yaml
shql:
  from: hello-world
  at: "1950-01-01T00:00:00Z"
  where:
    - edge:
        bind: ?e
        relation: has-member
  select:
    - ?e.members
```

**Result**: The `edge-stooges-shemp` edge matches (Moe, Larry, Shemp) — Curly had retired due to illness.

### Find all siblings

```yaml
shql:
  from: hello-world
  where:
    - edge:
        bind: ?e
        relation: sibling
        flavor: symmetric
  select:
    - ?e.members
    - ?e.attributes
```

### Filter by tags

```yaml
shql:
  from: hello-world
  where:
    - edge:
        bind: ?e
        tags: [original]
  select:
    - ?e.id
    - ?e.relation
    - ?e.members
    - ?e.tags
```

### Count edges by relation type

```yaml
shql:
  from: hello-world
  where:
    - edge:
        bind: ?e
  select:
    - ?e.relation
  aggregate:
    count: true
    group_by: e.relation
```

---

## Step 5: Use the hgai Shell

```bash
python shell/hgai_shell.py

hgai> connect http://localhost:8000 -u admin
  Connected to http://localhost:8000 as 'admin'
  Roles: admin

hgai> use hello-world
  Active graph set to: hello-world

admin@http://localhost:8000 [hello-world] hgai> ls nodes
  Hypernodes (8 total)
  ID                  Label              Type          Status
  ──────────────────  ─────────────────  ────────────  ──────
  three-stooges       Three Stooges      Group         active
  moe-howard          Moe Howard         Person        active
  ...

admin@http://localhost:8000 [hello-world] hgai> get node moe-howard

  id: moe-howard
  label: Moe Howard
  type: Person
  attributes:
    first_name: Moe
    last_name: Howard
    born: '1897-06-19'
  ...

admin@http://localhost:8000 [hello-world] hgai> shql
  Enter SHQL query (YAML format, end with line containing just ---):
  where:
    - edge:
        bind: ?e
        relation: has-member
  select:
    - ?e.members
  ---

  SHQL 'result': 3 results
```

---

## What You've Learned

1. **Hypernodes** are flexible entity documents with attributes, tags, and temporal qualifiers
2. **Hyperedges** connect _n_ nodes simultaneously as first-class entities with their own attributes
3. **Temporal queries** let you ask "who/what was true at this specific moment in time?"
4. **Semantic flavors** (hub, symmetric) capture the nature of relationships
5. **SHQL** provides a SPARQL-inspired YAML query language — variable bindings, implicit joins, and multi-hop traversal — for flexible hypergraph queries

---

## Next Steps

- Read [concepts.md](concepts.md) for deeper understanding of the hypergraph model
- Explore [api-reference.md](api-reference.md) for the full REST API
- Build a custom module: [module-development.md](module-development.md)
- Try the MCP server tools with Claude or another AI agent
