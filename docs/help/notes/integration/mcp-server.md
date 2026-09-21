---
id: help-mcp-server
label: MCP server
name: mcp-server
description: Connect AI agents and MCP clients such as Claude to HypergraphAI — endpoint, configuration, discovery, and calling tools.
tags: ["//Integration", mcp, agent, claude, tools, model-context-protocol]
status: active
---

# MCP server

HypergraphAI exposes its operations as **MCP (Model Context Protocol)** tools, so AI agents can read, query and update hypergraphs directly. The server is mounted at:

```
http://localhost:8357/mcp/         (http://localhost:8000/mcp/ under Docker Compose)
```

## Configure a client

For Claude Desktop or any MCP client that supports HTTP servers and headers:

```json
{
  "mcpServers": {
    "hgai": {
      "url": "http://localhost:8357/mcp/",
      "headers": { "Authorization": "Bearer <your-token-or-api-key>" }
    }
  }
}
```

Use a login token or an [API key](help:help-authentication). Never commit a real key to source control.

## Authorization

Every tool call runs **as the account that owns the credential**, under the same rules the REST API applies (see [Accounts and roles](help:help-accounts-roles) and [Spaces](help:help-spaces)):

| Tools | The caller needs |
|---|---|
| `hgai_hypergraph_get`, `_stats`; `hgai_hypernode_list`, `_get`; `hgai_hyperedge_list`, `_get`; `hgai_infer_*` | access to the graph and the `read` operation |
| `hgai_hypernode_create`, `_update`; `hgai_hyperedge_create` | access to the graph and `write` |
| `hgai_hypernode_delete`, `hgai_hyperedge_delete` | access to the graph and `delete` |
| `hgai_query_execute` | access to **every** graph in `from:` and the `query` operation (see [SHQL permissions](help:help-shql-advanced)) |
| `hgai_hypergraph_list` | nothing — but only graphs the caller can access are listed |
| `hgai_space_get`, `hgai_space_list_graphs` / `hgai_space_add_member` | space role `viewer` / `admin` (or higher); `hgai_space_list` shows only the caller's spaces |
| `hgai_mesh_*` (including `hgai_mesh_query`) | the `admin` role |
| `hgai_hypergraph_create`, `hgai_space_create`, `hgai_media_*`, `hgai_query_validate` | any authenticated account (as on REST) |

"Access to the graph" means the graph is in the account's `permissions.graphs` (or `["*"]`) for an unowned graph, or the account is a member of the owning space; admins pass every check. A refused call returns a normal tool result — HTTP 200 — of the form `{"error": "Access to graph 'eden' not permitted", "type": "PermissionDenied"}`, so an agent can see and report it. The graph tools address unowned graphs; query a space's graph with `hgai_query_execute` and `from: space_id/graph_id`.

Things to know:

- **API keys are full-admin credentials** and bypass every check. To give an agent limited access, create an account with the permissions you want and give the agent that account's login token instead. Inactive accounts and expired tokens are rejected with `401`.
- Writes made through MCP are recorded in the audit trail under the **caller's username** (`api-key` for an API key), not a generic agent name.
- An account's permissions are read when the call is made, so a change takes effect immediately.

## Discover the tools

```bash
curl -X POST http://localhost:8357/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer <credential>" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
```

## Call a tool

```bash
curl -s -X POST http://localhost:8357/mcp/ \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer <credential>" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call",
       "params":{"name":"hgai_hypernode_get",
                 "arguments":{"graph_id":"hello-world","node_id":"person:moe"}}}'
```

Results come back as text content (usually JSON). Errors are returned as tool output — for example `{"error": "Node 'x' not found in graph 'y'"}` — with HTTP 200, not as HTTP errors.

## From Python

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client("http://localhost:8357/mcp/",
        headers={"Authorization": "Bearer <credential>"}) as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("hgai_hypergraph_list", {"status": "active"})
```

The full list of tools is in [MCP tools](help:help-mcp-tools). The Web UI's own [AI Chat](help:help-ai-chat) agent uses these same tools.
