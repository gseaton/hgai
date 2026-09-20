---
id: help-spaces
label: Spaces (multi-tenant namespaces)
name: spaces
description: Spaces group hypergraphs for multi-tenant use, with member roles and space-scoped references.
tags: ["//Concepts", space, tenant, rbac, namespace]
status: active
---

# Spaces

A **space** groups hypergraphs for multi-tenant deployments. Because graph ids are unique *per space*, teams `team-a` and `team-b` can each have a graph named `my-graph` without conflict.

## Referencing space graphs

| Where | Form |
|---|---|
| SHQL `from:` (local) | `space_id/graph_id`, e.g. `alpha/alpha-hg` |
| REST | `/api/v1/spaces/{space_id}/graphs/{graph_id}` (nodes and edges below it) |
| Mesh (remote server) | `mesh.server.space.graph` — four components |

Flat `/graphs/*` routes address only **unowned** graphs.

## Space roles

| Role | Permitted operations |
|---|---|
| `owner` | read, write, delete, admin, query, export, import + manage the space |
| `admin` | read, write, delete, query, export, import + manage members |
| `member` | read, write, query, export, import |
| `viewer` | read, query, export |

## Access control

Space membership is the **sole gate** for a space's graphs — a `permissions.graphs` wildcard (`["*"]`) does *not* grant access to a space you don't belong to. Access is resolved in order: (1) global `admin` bypasses everything; (2) for a space graph, you must be a space member; (3) `permissions.graphs` applies only to unowned graphs. See [Accounts and roles](help:help-accounts-roles) for managing members.

MCP tools: `hgai_space_list`, `hgai_space_get`, `hgai_space_create`, `hgai_space_add_member`, `hgai_space_list_graphs` ([MCP tools](help:help-mcp-tools)).
