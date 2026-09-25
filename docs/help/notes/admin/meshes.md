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

The same operations are available as `hgai_mesh_*` [MCP tools](help:help-mcp-tools). Everything mesh-related is **admin-only**: because federation calls remote servers with the mesh's own stored credentials, a non-admin account cannot use a mesh id or dot-notation reference in an [SHQL](help:help-shql-overview) `from:` (it gets `403`), nor the `hgai_mesh_*` tools.

## Querying a whole mesh

```yaml
shql:
  from: alpha-bravo-mesh
  where:
    - node:
        bind: ?person
        node_type: Person
  select:
    - ?person.id
    - ?person.label
    - ?person.node_type
```

All servers are queried **concurrently** — total latency is the slowest server, not the sum. Unreachable servers are skipped and reported in the response's `errors`.

### Aggregates across servers

`aggregate:` (`count`, `group_by`, `sum`, `avg`, `min`, `max`, `count_numeric`) works over a whole mesh. Each server aggregates **its own graphs** — using storage-side aggregation where the query allows — and returns just its partial result; the partials are then merged exactly:

| Measure | Merged by |
|---|---|
| `count`, `sum`, `count_numeric` | adding |
| `min`, `max` | taking the smallest / largest |
| `avg` | merged `sum` ÷ merged `count_numeric` (never an average of averages) |
| `groups` / `group_measures` | union of groups, merged per group |

To make `avg` mergeable, each server is also asked for `sum` and `count_numeric` of the averaged fields; they don't appear in the result unless you requested them. With `limit: 0` no rows travel at all. The result's `meta.federation` lists the servers that answered (`servers`), the ones that failed (`errors` — their data is missing from **both** rows and aggregates) and whether the merge was used (`aggregate_merged`). `meta.truncated_by` includes each server's own truncation, prefixed with its id, and `meta.aggregate_pushdown` is `true` only if every server computed its part in storage. If a server cannot supply partials (an older version) or the query uses `distinct`, the aggregate is computed from the merged rows instead, as it always was. `POST /meshes/{id}/query` returns the merged result as `aggregate` in its response.

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
