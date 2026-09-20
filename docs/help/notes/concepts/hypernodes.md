---
id: help-hypernodes
label: Hypernodes
name: hypernodes
description: Hypernodes are the entities (nouns) of a hypergraph — their fields, types, tags, status and validity dates.
tags: ["//Concepts", hypernode, entity, node, model]
status: active
---

# Hypernodes

A **hypernode** represents an entity — a person, organization, concept, place, or even a *relation type*. It has flexible, document-based attributes.

| Field | Meaning |
|---|---|
| `id` | Human-readable identifier, unique within its hypergraph (e.g. `person:moe`, `group:three-stooges`) |
| `label` | Display label |
| `type` | Entity type, e.g. `Person`, `Organization`, `Concept`, `Group`, `RelationType` |
| `description` | Optional prose description |
| `attributes` | Arbitrary JSON document — add any properties you like |
| `tags` | List of string tags for grouping and filtering |
| `status` | `active`, `draft`, or `archived` |
| `valid_from`, `valid_to` | Optional validity window used by [point-in-time queries](help:help-point-in-time) |

Example:

```json
{
  "id": "person:moe",
  "label": "Moe",
  "type": "Person",
  "description": "Moe Howard",
  "attributes": { "role": "leader" },
  "tags": ["stooge", "comedian"],
  "status": "active"
}
```

## Working with hypernodes

- **Web UI** — the **Hypernodes** screen: pick a hypergraph, then create, edit, filter, sort and delete. Media can be attached to a node ([Media](help:help-media)).
- **REST** — `GET/POST /api/v1/graphs/{graph}/nodes`, `GET/PUT/DELETE /api/v1/graphs/{graph}/nodes/{id}` ([REST API](help:help-rest-api)).
- **MCP** — `hgai_hypernode_list`, `_get`, `_create`, `_update`, `_delete` ([MCP tools](help:help-mcp-tools)).
- **SHQL** — match with a `node:` pattern ([patterns](help:help-shql-patterns)).

Nodes are linked to one another only through [hyperedges](help:help-hyperedges).
