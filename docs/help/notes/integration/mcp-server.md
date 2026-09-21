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

> **Authorization caveat.** The MCP endpoint authenticates the caller — any valid API key or login token is accepted — but tool calls are **not** checked against the account's roles, per-graph permissions or space memberships (an API key is a full-admin credential; a login token for even a `readonly` account can read and write every graph through MCP). The REST CRUD, export/import and inference endpoints do enforce permissions. Until per-caller authorization is added to MCP, expose `/mcp/` only to trusted callers (network isolation or a gateway), and treat every MCP credential as administrative.

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
