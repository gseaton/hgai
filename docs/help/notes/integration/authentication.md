---
id: help-authentication
label: Authentication (JWT and API keys)
name: authentication
description: Logging in with JWT tokens, and machine-to-machine API keys with zero-downtime rotation.
tags: ["//Integration", auth, jwt, api-key, security, token]
status: active
---

# Authentication

HypergraphAI supports two methods. Both are sent as `Authorization: Bearer <credential>`.

## 1. JWT tokens (interactive users)

Log in to obtain a token — this is what the Web UI does:

```bash
curl -X POST http://localhost:8357/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=pwd357"
```

The response contains `access_token`, `token_type` and `expires_in`. Tokens live for `HGAI_TOKEN_EXPIRE_MINUTES` (default 480). Then:

```bash
curl http://localhost:8357/api/v1/graphs -H "Authorization: Bearer <access_token>"
```

## 2. API keys (machines, agents, MCP clients)

API keys are stateless — no login step — and grant **full admin access**, so guard them.

```bash
python -c "import secrets; print(secrets.token_hex(32))"     # generate one
```

Put it in `.env`:

```bash
HGAI_PRIMARY_API_KEY=your-generated-api-key
HGAI_SECONDARY_API_KEY=optional-second-key-for-rotation
```

and use it directly as the Bearer value.

### Rotation

Two keys are accepted so you can rotate with no downtime: (1) set the new key as `HGAI_SECONDARY_API_KEY`; (2) switch clients to it; (3) move it to `HGAI_PRIMARY_API_KEY` and remove the old key.

## Roles

What an authenticated *account* may do through the **REST CRUD, export/import and inference** endpoints depends on its roles and permissions — see [Accounts and roles](help:help-accounts-roles). The **SHQL query** endpoint and the **MCP** tools currently only require authentication (no per-graph permission check), so treat any credential that can reach them as broadly privileged. To let an MCP client authenticate, see [MCP server](help:help-mcp-server).

**Important:** change the default `admin` password immediately after installation, and set a strong `HGAI_SECRET_KEY` ([Configuration](help:help-configuration)).
