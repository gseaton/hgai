---
id: help-meshes
label: Meshes (federation)
name: meshes
description: Register several HypergraphAI servers in a mesh, then ping, sync and query them together with concurrent fan-out.
tags: ["//Administration", mesh, federation, distributed, dot-notation]
status: active
---

# Meshes

A **mesh** is a registry of HypergraphAI servers you can query together. Each mesh has an `id`, a `label`, and a list of servers, where each server has a `server_id`, `server_name`, base `url`, an optional `api_token` used to call it, and its known graph ids. Ids must not contain dots.

Administrators manage meshes in the **Meshes** screen or through `/api/v1/meshes`:

| Endpoint | Purpose |
|---|---|
| `GET/POST /meshes`, `GET/PUT/DELETE /meshes/{id}` | Manage meshes |
| `GET /meshes/{id}/ping` | Health-check every server |
| `POST /meshes/{id}/sync` | Refresh graph lists from the live servers |
| `POST /meshes/{id}/query` | Run a federated [SHQL](help:help-shql-overview) query |

The same operations are available as `hgai_mesh_*` [MCP tools](help:help-mcp-tools).

## Querying a whole mesh

```yaml
shql:
  from: alpha-bravo-mesh
  where:
    - node: { bind: ?person, node_type: Person }
  select: [?person.id, ?person.label, ?person.node_type]
```

All servers are queried **concurrently** — total latency is the slowest server, not the sum. Unreachable servers are skipped and reported in the response's `errors`.

## Dot-notation references

| Format | Meaning |
|---|---|
| `mesh.server.graph` | An unowned graph on one server |
| `mesh.server.space.graph` | A space-scoped graph on one server |
| `mesh.*.graph` | That graph on every server in the mesh |
| `mesh.*.space.graph` | That space graph on every server |
| `mesh.server.*` | All unowned graphs on one server |

Dots are prohibited in ids, so splitting on `.` is unambiguous. Local space graphs use a slash (`space/graph`); dots are reserved for mesh routing.

```yaml
shql:
  from: alpha-bravo-mesh.server-a.my-team.my-graph
```

Two local servers are easy to set up — see [Running locally](help:help-running-locally). Performance notes: [Indexes and performance](help:help-indexes-performance).
