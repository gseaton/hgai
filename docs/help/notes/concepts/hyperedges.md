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
| `relation` | Semantic relation type, e.g. `has-member`, `sibling`, `broader`, `rel:president-of` |
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
  "relation": "has-member",
  "flavor": "hub",
  "members": [
    { "node_id": "three-stooges", "seq": 0 },
    { "node_id": "moe-howard",    "seq": 1 },
    { "node_id": "larry-fine",    "seq": 2 }
  ],
  "attributes": { "era": "classic" },
  "tags": ["original"]
}
```

## Working with hyperedges

- **Web UI** — the **Hyperedges** screen, with member management.
- **REST** — `/api/v1/graphs/{graph}/edges` ([REST API](help:help-rest-api)).
- **MCP** — `hgai_hyperedge_list`, `_get`, `_create`, `_delete` ([MCP tools](help:help-mcp-tools)).
- **SHQL** — the `edge:` pattern, including positional `seq` matching ([patterns](help:help-shql-patterns)).
- Relation semantics such as *transitive* or *inverse-of* are declared by axiom hyperedges — see [Inferencing](help:help-inferencing).
