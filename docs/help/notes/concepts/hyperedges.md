---
id: help-hyperedges
label: Hyperedges
name: hyperedges
description: Hyperedges are first-class relationships that connect any number of hypernodes — relation, members, flavor, and hyperkey.
tags: ["//Concepts", hyperedge, relationship, edge, model]
status: active
---

# Hyperedges

A **hyperedge** is a first-class semantic relationship that connects *n* hypernodes. Unlike an ordinary graph edge (limited to two endpoints), one hyperedge can list as many members as the fact needs.

| Field | Meaning |
|---|---|
| `relation` | Semantic relation type, e.g. `rel:member`, `rel:sibling`, `skos:broaderTransitive`, `rel:parent` |
| `members` | Ordered list of participating hypernodes — each with a `node_id`, a position `seq`, and optionally a role |
| `flavor` | How the member list decomposes into facts — `hub`, `symmetric`, `direct`, `transitive`, `inverse-transitive` (see [Edge flavors](help:help-edge-flavors)) |
| `attributes` | Arbitrary JSON document (e.g. `era: classic`) |
| `tags`, `status` | As for [hypernodes](help:help-hypernodes) |
| `valid_from`, `valid_to` | Validity window for [point-in-time queries](help:help-point-in-time) |
| `hyperkey` | A SHA-256 hash generated from the normalized edge structure |

## Hyperkey and de-duplication

The `hyperkey` is computed from the edge's relation and members, so two edges with the same structure produce the same key. A unique index on `(hyperkey, hypergraph)` prevents duplicate facts at the database level. You can leave the edge `id` blank and one will be generated.

## Example

```json
{
  "id": "edge:classic-stooges",
  "relation": "rel:member",
  "flavor": "hub",
  "label": "Classic Three Stooges Trio",
  "members": [
    { "node_id": "group:three-stooges", "seq": 0 },
    { "node_id": "person:moe",          "seq": 1 },
    { "node_id": "person:larry",        "seq": 2 },
    { "node_id": "person:curly",        "seq": 3 }
  ],
  "valid_from": "1932-07-02T16:01:00",
  "valid_to": "1946-07-03T15:59:00"
}
```

## Working with hyperedges

- **Web UI** — the **Hyperedges** screen, with member management.
- **REST** — `/api/v1/graphs/{graph}/edges` ([REST API](help:help-rest-api)).
- **MCP** — `hgai_hyperedge_list`, `_get`, `_create`, `_delete` ([MCP tools](help:help-mcp-tools)).
- **SHQL** — the `edge:` pattern, including positional `seq` matching ([patterns](help:help-shql-patterns)).
- Relation semantics such as *transitive* or *inverse-of* are declared by axiom hyperedges — see [Inferencing](help:help-inferencing).
