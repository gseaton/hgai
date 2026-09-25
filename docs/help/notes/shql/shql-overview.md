---
id: help-shql-overview
label: SHQL overview
name: shql-overview
description: What SHQL is and the overall structure of a query — from, where, select, order_by, limit, infer, aggregate.
tags: ["//Query Language (SHQL)", shql, query, yaml, structure]
status: active
---

# SHQL — Semantic Hypergraph Query Language

SHQL (pronounced *"shekel"*) is HypergraphAI's query language. It is a **pattern-matching** language inspired by SPARQL, written in YAML: you describe patterns of nodes and edges with `?variable` placeholders, and the engine returns every way the patterns match. Shared variables act as implicit joins. It also supports OPTIONAL, UNION, filters, [point-in-time](help:help-point-in-time) queries, aggregation and [inferencing](help:help-inferencing).

## Where to run it

- The [Query screen](help:help-query-screen) in the Web UI
- `POST /api/v1/shql/query` (and `/validate`) — [REST API](help:help-rest-api)
- The `hgai_query_execute` / `hgai_query_validate` [MCP tools](help:help-mcp-tools) and the [shell](help:help-shell)
- Saved as [parameterized queries](help:help-parameterized-queries)

## Query structure

```yaml
shql:
  from: <graph-id>        # required — one graph id, or a list of them
  at: <iso-datetime>      # optional — point-in-time
  where:                  # ordered list of patterns
    - node:  { ... }      # hypernode pattern
    - edge:  { ... }      # hyperedge pattern
    - filter: "<expression>"
    - optional: [ ... ]   # left outer join
    - union:              # alternatives
        - patterns: [ ... ]
        - patterns: [ ... ]
  select:                 # fields to return
    - ?var                # the whole bound entity
    - ?var.label          # a single field
    - ?var.attributes.city  # a nested attribute
  order_by: ?var.field    # or a list; each may end in asc/desc
  limit: 100              # default 500 (0 is allowed with aggregate: rows omitted)
  offset: 0
  distinct: true          # remove duplicate rows
  infer: true             # opt-in axiom expansion (see Inferencing)
  aggregate:
    count: true
    group_by: var.field
    sum: var.field          # also avg, min, max
  as: result_alias
```

## Choosing what to query: `from:`

| `from:` value | Meaning |
|---|---|
| `my-graph` | An unowned local graph |
| `alpha/alpha-hg` | A graph inside space `alpha` ([Spaces](help:help-spaces)) |
| `[a, b/c]` | Several graphs at once (any mix) |
| `my-mesh.server.graph` and friends | Graphs on other servers ([Meshes](help:help-meshes)) |

## Variables

A variable starts with `?` and binds a matched entity. Using the same variable in two patterns forces them to agree on the same node — that is a join. Details: [patterns](help:help-shql-patterns).

## Next

[Node and edge patterns](help:help-shql-patterns) → [Filters](help:help-shql-filters) → [OPTIONAL, UNION, aggregate and more](help:help-shql-advanced) → [Worked examples](help:help-shql-examples).
