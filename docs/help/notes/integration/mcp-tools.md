---
id: help-mcp-tools
label: MCP tools reference
name: mcp-tools
description: Every hgai_* MCP tool grouped by area, with the arguments for the create/update tools.
tags: ["//Integration", mcp, tools, reference]
status: active
---

# MCP tools reference

Connect as described in [MCP server](help:help-mcp-server). Tools are grouped below; use `tools/list` for the authoritative, current list and schemas.

## Hypergraph tools

| Tool | Description |
|---|---|
| `hgai_hypergraph_list` | List hypergraphs, filtered by status (`active`, `archived`, `draft`, or all) |
| `hgai_hypergraph_get` | Get a hypergraph |
| `hgai_hypergraph_stats` | Node/edge counts and statistics |
| `hgai_hypergraph_create` | Create an `instantiated` or `logical` hypergraph |

## Hypernode tools

| Tool | Description |
|---|---|
| `hgai_hypernode_list` | List nodes in a graph, filtered by type and/or tags |
| `hgai_hypernode_get` | Get a node by id |
| `hgai_hypernode_create` | Create a node |
| `hgai_hypernode_update` | Update a node's label, attributes, tags or status |
| `hgai_hypernode_delete` | Delete a node |

## Hyperedge tools

| Tool | Description |
|---|---|
| `hgai_hyperedge_list` | List edges, filtered by relation or member node id |
| `hgai_hyperedge_get` | Get an edge by id or hyperkey |
| `hgai_hyperedge_create` | Create an n-ary edge |
| `hgai_hyperedge_delete` | Delete an edge |

## Query and inference tools

| Tool | Description |
|---|---|
| `hgai_query_execute` | Execute an [SHQL](help:help-shql-overview) query (top-level `shql:` key) |
| `hgai_query_validate` | Validate a query without running it |
| `hgai_infer_expand_edge` | Axiom expansion of one hyperedge ([Inferencing](help:help-inferencing)) |
| `hgai_infer_check_transitive` | Transitive reachability over an `owl:transitive` relation |

## Mesh, media and space tools

| Tool | Description |
|---|---|
| `hgai_mesh_list`, `hgai_mesh_get` | List / get meshes ([Meshes](help:help-meshes)) |
| `hgai_mesh_ping`, `hgai_mesh_sync` | Check reachability; refresh graph lists |
| `hgai_mesh_query` | Federated SHQL across a mesh |
| `hgai_media_upload`, `hgai_media_download`, `hgai_media_delete` | Media files ([Media](help:help-media)) |
| `hgai_space_list`, `hgai_space_get`, `hgai_space_create`, `hgai_space_add_member`, `hgai_space_list_graphs` | Spaces ([Spaces](help:help-spaces)) |

## Argument reference

**`hgai_hypergraph_create`** — `id` (slug), `label`, `description`, `graph_type` (`instantiated` | `logical`), `tags` (comma-separated).

**`hgai_hypernode_create`** — `graph_id`, `id`, `label`, `node_type`, `attributes_json` (a JSON *string*, e.g. `'{"city": "Paris"}'`), `tags` (comma-separated), `description`.

**`hgai_hypernode_update`** — `graph_id`, `node_id`, and optional `label`, `attributes_json` (replaces existing), `tags`, `status`.

**`hgai_hyperedge_create`** — `graph_id`, `relation`, `members_json` (a JSON array such as `[{"node_id": "a", "seq": 0}, {"node_id": "b", "seq": 1}]`), optional `edge_id`, `label`, `flavor`, `attributes_json`, `tags`.

**`hgai_query_execute`** — `query_yaml` (the SHQL text) and `use_cache` (default true).

Example call payload:

```json
{
  "name": "hgai_hypernode_create",
  "arguments": {
    "graph_id": "my-graph",
    "id": "person:john-doe",
    "label": "John Doe",
    "node_type": "Person",
    "attributes_json": "{\"born\": \"1990-05-15\", \"city\": \"New York\"}",
    "tags": "employee,developer"
  }
}
```
