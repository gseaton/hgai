# HypergraphAI API Reference

Base URL: `http://localhost:8000/api/v1`

Interactive API docs: `http://localhost:8000/api/docs` (Swagger UI)

All endpoints (except `/auth/token`) require a JWT Bearer token in the `Authorization` header.

---

## Authentication

### POST /auth/token

Obtain a JWT access token.

**Request** (form-encoded):
```
username=admin&password=pwd357&grant_type=password
```

**Response:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 28800,
  "username": "admin",
  "roles": ["admin"]
}
```

### GET /auth/me

Get current authenticated user info.

---

## Hypergraphs

> **Routing note:** The flat `/graphs/*` endpoints operate on **unowned graphs** only (graphs with no `space_id`). For space-scoped graphs use the nested routes under `/spaces/{space_id}/graphs/*`. The same graph ID may exist in multiple spaces without conflict.

### GET /graphs

List unowned hypergraphs.

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `status` | string | `active` | Filter by status |
| `tags` | string[] | - | Filter by tags |
| `space_id` | string | - | Filter by owning space |
| `skip` | int | `0` | Pagination offset |
| `limit` | int | `50` | Max results (max 500) |

**Response:**
```json
{
  "total": 3,
  "skip": 0,
  "limit": 50,
  "items": [
    {
      "id": "hello-world",
      "label": "Hello, World!",
      "type": "instantiated",
      "status": "active",
      "node_count": 8,
      "edge_count": 4,
      "tags": ["example"],
      "attributes": {},
      "system_created": "2025-01-01T00:00:00Z"
    }
  ]
}
```

### POST /graphs

Create a hypergraph.

**Body:**
```json
{
  "id": "my-graph",
  "label": "My Graph",
  "description": "Optional description",
  "type": "instantiated",
  "tags": ["tag1"],
  "attributes": {}
}
```

### GET /graphs/{id}
### PUT /graphs/{id}
### DELETE /graphs/{id}
### GET /graphs/{id}/stats
### POST /graphs/{id}/export
### POST /graphs/{id}/import

---

## Hypernodes

### GET /graphs/{graph_id}/nodes

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `node_type` | string | - | Filter by entity type |
| `status` | string | `active` | Filter by status |
| `tags` | string[] | - | Filter by tags |
| `search` | string | - | Text search in label |
| `skip` | int | `0` | Pagination |
| `limit` | int | `50` | Max results |

### POST /graphs/{graph_id}/nodes

**Body:**
```json
{
  "id": "my-node",
  "label": "My Node",
  "type": "Person",
  "description": "Optional",
  "attributes": {
    "first_name": "Jane",
    "last_name": "Doe"
  },
  "tags": ["person", "staff"],
  "status": "active",
  "valid_from": "2020-01-01T00:00:00Z",
  "valid_to": null,
}
```

### GET /graphs/{graph_id}/nodes/{node_id}
### PUT /graphs/{graph_id}/nodes/{node_id}
### DELETE /graphs/{graph_id}/nodes/{node_id}

---

## Hyperedges

### GET /graphs/{graph_id}/edges

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `relation` | string | - | Filter by relation type |
| `flavor` | string | - | Filter by edge flavor |
| `status` | string | `active` | Filter by status |
| `tags` | string[] | - | Filter by tags |
| `node_id` | string | - | Filter edges containing this node |
| `skip` | int | `0` | Pagination |
| `limit` | int | `50` | Max results |

### POST /graphs/{graph_id}/edges

**Body:**
```json
{
  "id": "optional-custom-id",
  "relation": "has-member",
  "label": "Optional label",
  "flavor": "hub",
  "members": [
    {"node_id": "group-node", "role": "group", "seq": 0},
    {"node_id": "member-1",   "role": "member", "seq": 1, "order": 1},
    {"node_id": "member-2",   "role": "member", "seq": 2, "order": 2}
  ],
  "attributes": {"context": "value"},
  "tags": ["tag1"],
  "status": "active",
  "valid_from": "2020-01-01T00:00:00Z",
  "valid_to": null
}
```

**Response includes:**
- `hyperkey` — auto-generated SHA-256 key

### GET /graphs/{graph_id}/edges/{edge_id}
### PUT /graphs/{graph_id}/edges/{edge_id}
### DELETE /graphs/{graph_id}/edges/{edge_id}

---

## HQL Query

### POST /query

Execute an HQL query.

The `from` field accepts:
- A local graph ID: `"my-graph"`
- A list of local graph IDs: `["graph-1", "graph-2"]`
- Mesh dot-notation refs: `"mesh-id.server-id.graph-id"` (wildcards `*` supported in any position)
- A mix of local IDs and dot-notation refs in the same list

Graph IDs, server IDs, and mesh IDs must not contain `.` (reserved as the dot-notation delimiter).

**Body:**
```json
{
  "hql": "hql:\n  from: my-graph\n  match:\n    type: hyperedge\n  return:\n    - members",
  "use_cache": true
}
```

**Response:**
```json
{
  "alias": "result",
  "count": 3,
  "items": [...],
  "meta": {
    "graph_ids": ["my-graph"],
    "match_type": "hyperedge",
    "pit": null,
    "cached": false
  }
}
```

### POST /query/validate

Validate an HQL query without executing.

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "parsed": {
    "from": "my-graph",
    "match": {"type": "hyperedge"}
  }
}
```

### POST /query/cache/invalidate

Flush the query cache.

---

## Accounts (Admin Only)

### GET /accounts
### POST /accounts

**Body:**
```json
{
  "username": "alice",
  "password": "securepassword",
  "email": "alice@example.com",
  "roles": ["user"],
  "permissions": {
    "graphs": ["graph-a", "graph-b"],
    "operations": ["read", "query", "write"]
  },
  "tags": [],
  "status": "active"
}
```

### GET /accounts/{username}
### PUT /accounts/{username}
### DELETE /accounts/{username}

---

## Meshes (Admin Only)

### GET /meshes
### POST /meshes

**Body:**
```json
{
  "id": "my-mesh",
  "label": "My Mesh",
  "description": "Multi-server mesh",
  "servers": [
    {
      "server_id": "hgai-server-1",
      "server_name": "Server 1",
      "url": "http://server1:8000",
      "api_token": "token-abc",
      "graphs": ["graph-1", "graph-2"],
      "status": "active"
    }
  ]
}
```

### GET /meshes/{id}
### PUT /meshes/{id}
### DELETE /meshes/{id}

---

## System

### GET /health

```json
{
  "status": "ok",
  "server_id": "hgai-local",
  "server_name": "HypergraphAI Local",
  "version": "0.1.0"
}
```

### GET /api/v1/server/info

```json
{
  "server_id": "hgai-local",
  "server_name": "HypergraphAI Local",
  "version": "0.1.0",
  "capabilities": ["hypernodes", "hyperedges", "hypergraphs", "hql", "mcp", "mesh", "temporal", "inference"]
}
```

---

## MCP Server

The MCP (Model Context Protocol) server is available at:
```
http://localhost:8000/mcp/
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `hgai_hypergraph_list` | List hypergraphs |
| `hgai_hypergraph_get` | Get a hypergraph |
| `hgai_hypergraph_stats` | Get hypergraph statistics |
| `hgai_hypergraph_create` | Create a hypergraph |
| `hgai_hypernode_list` | List hypernodes |
| `hgai_hypernode_get` | Get a hypernode |
| `hgai_hypernode_create` | Create a hypernode |
| `hgai_hypernode_update` | Update a hypernode |
| `hgai_hypernode_delete` | Delete a hypernode |
| `hgai_hyperedge_list` | List hyperedges |
| `hgai_hyperedge_get` | Get a hyperedge |
| `hgai_hyperedge_create` | Create a hyperedge |
| `hgai_hyperedge_delete` | Delete a hyperedge |
| `hgai_query_execute` | Execute an HQL query |
| `hgai_query_validate` | Validate an HQL query |

---

## Spaces

Spaces are multi-tenant namespaces for organizing hypergraphs. Members are assigned roles (`owner`, `admin`, `member`, `viewer`) that control permitted operations.

### GET /spaces

List spaces. Admins see all spaces; other users see only spaces they are members of.

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `skip` | int | `0` | Pagination offset |
| `limit` | int | `50` | Max results (max 500) |

### POST /spaces

Create a new space. The creator is automatically added as `owner`.

```json
{ "id": "research-team", "label": "Research Team", "description": "..." }
```

### GET /spaces/{space_id}

Get space details including member list. Requires `viewer` role or higher.

### PUT /spaces/{space_id}

Update space metadata (`label`, `description`, `tags`, `attributes`, `status`). Requires `admin` role or higher.

### DELETE /spaces/{space_id}

Delete a space. Requires `owner` role.

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `delete_graphs` | bool | `false` | Also delete all graphs in the space |

### GET /spaces/{space_id}/members

List space members with their roles. Requires `viewer` role or higher.

### POST /spaces/{space_id}/members

Add or update a member. Requires `admin` role or higher.

```json
{ "username": "alice", "role": "member" }
```

### PUT /spaces/{space_id}/members/{username}

Update a member's role. Requires `admin` role or higher.

```json
{ "role": "admin" }
```

### DELETE /spaces/{space_id}/members/{username}

Remove a member from a space. Requires `admin` role or higher.

### GET /spaces/{space_id}/graphs

List all hypergraphs in the space. Requires `viewer` role or higher.

| Query Param | Type | Default | Description |
|-------------|------|---------|-------------|
| `skip` | int | `0` | Pagination offset |
| `limit` | int | `50` | Max results (max 500) |

### POST /spaces/{space_id}/graphs

Create a hypergraph scoped to the space. The same graph ID may be reused across different spaces. Requires `member` role or higher. The `space_id` field in the request body is ignored — the path parameter always wins.

### GET /spaces/{space_id}/graphs/{graph_id}

Get a space-scoped hypergraph. Requires `viewer` role or higher.

### PUT /spaces/{space_id}/graphs/{graph_id}

Update a space-scoped hypergraph. Requires `write` permission or `member` space role or higher.

### DELETE /spaces/{space_id}/graphs/{graph_id}

Delete a space-scoped hypergraph and all its nodes/edges. Requires `delete` permission or `admin` space role or higher.

### GET /spaces/{space_id}/graphs/{graph_id}/stats

Stats for a space-scoped hypergraph.

### POST /spaces/{space_id}/graphs/{graph_id}/export / import

Export or import nodes/edges for a space-scoped hypergraph.

### GET /spaces/{space_id}/graphs/{graph_id}/nodes

### POST /spaces/{space_id}/graphs/{graph_id}/nodes

### GET|PUT|DELETE /spaces/{space_id}/graphs/{graph_id}/nodes/{node_id}

Full node CRUD mirroring `/graphs/{graph_id}/nodes/*` but scoped to a space-owned graph.

### GET /spaces/{space_id}/graphs/{graph_id}/edges

### POST /spaces/{space_id}/graphs/{graph_id}/edges

### GET|PUT|DELETE /spaces/{space_id}/graphs/{graph_id}/edges/{edge_id}

Full edge CRUD mirroring `/graphs/{graph_id}/edges/*` but scoped to a space-owned graph.

---

## Error Responses

All errors follow the format:
```json
{
  "detail": "Human-readable error message"
}
```

| HTTP Code | Meaning |
|-----------|---------|
| `400` | Bad Request (invalid input or HQL) |
| `401` | Unauthorized (missing or invalid token) |
| `403` | Forbidden (insufficient permissions) |
| `404` | Not Found |
| `409` | Conflict (duplicate ID) |
| `422` | Validation Error (Pydantic) |
| `500` | Internal Server Error |
