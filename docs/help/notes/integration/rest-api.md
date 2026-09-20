---
id: help-rest-api
label: REST API
name: rest-api
description: The REST endpoints — hypergraphs, nodes, edges, inference, notes, media, SHQL, help, accounts, meshes.
tags: ["//Integration", api, rest, http, endpoints]
status: active
---

# REST API

Base URL: `http://localhost:8357/api/v1` (port 8000 under Docker Compose). Interactive documentation is at `/api/docs` on the same server. Every call needs authentication — see [Authentication](help:help-authentication). The full reference is `docs/api-reference.md`.

| Area | Endpoints |
|---|---|
| **Auth** | `POST /auth/token`, `GET /auth/me` |
| **Hypergraphs** | `GET/POST /graphs`; `GET/PUT/DELETE /graphs/{id}` |
| **Hypernodes** | `GET/POST /graphs/{g}/nodes`; `GET/PUT/DELETE /graphs/{g}/nodes/{id}` |
| **Hyperedges** | `GET/POST /graphs/{g}/edges`; `GET/PUT/DELETE /graphs/{g}/edges/{id}` |
| **Spaces** | `/spaces`, `/spaces/{s}/members`, `/spaces/{s}/graphs/{g}/nodes` and `/edges` |
| **Inference** | `POST /graphs/{g}/infer/transitive`, `/infer/expand`, `/infer/project` |
| **SHQL** | `POST /shql/query`, `/shql/validate`, `/shql/cache/invalidate` |
| **Notes** | `/notes`, `/notes/{id}`, `POST /notes/{id}/share`, `DELETE /notes/{id}/share/{username}` |
| **Media** | `/media`, `/media/{id}` (upload, download, update metadata, delete) |
| **Help** | `GET /help/topics`, `/help/topics/{id}`, `/help/home`, `/help/media/{path}` |
| **Accounts** *(admin)* | `/accounts`, `/accounts/{id}` |
| **Meshes** *(admin)* | `/meshes`, `/meshes/{id}`, `/meshes/{id}/ping`, `/sync`, `/query` |

## Lists

List endpoints accept `skip`, `limit`, `search`, `tags` and `sort` parameters and return `{items, total, …}` pages.

## Example

```bash
TOKEN=$(curl -s -X POST http://localhost:8357/api/v1/auth/token \
  -d "username=admin&password=pwd357" | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:8357/api/v1/graphs -H "Authorization: Bearer $TOKEN"
```

## Errors

Failures return an HTTP status with a JSON body containing a `detail` message; an expired or invalid token returns `401`.

Related: [MCP server](help:help-mcp-server), [Configuration](help:help-configuration).
