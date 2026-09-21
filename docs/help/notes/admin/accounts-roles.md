---
id: help-accounts-roles
label: Accounts and roles
name: accounts-roles
description: RBAC roles, the default admin account, managing accounts and space memberships.
tags: ["//Administration", accounts, rbac, roles, permissions, admin]
status: active
---

# Accounts and roles

## Default administrator

A fresh install has one account: **admin** / **pwd357**. **Change this password immediately after first login.**

## Roles

| Role | Description |
|---|---|
| `admin` | Full system access, including account management; bypasses all access checks |
| `user` | Read/write access to permitted hypergraphs |
| `agent` | API/MCP-only access for AI agents |
| `readonly` | Read-only access |

Beyond roles, an account has `permissions.graphs` (which unowned graphs it may use — wildcards such as `["*"]` are allowed) and [space](help:help-spaces) memberships. Access to a space's graphs comes **only** from space membership. These checks apply everywhere data is reached: the REST CRUD, export/import and inference endpoints, the SHQL query endpoint (needs the `query` operation on every `from:` graph) and the MCP tools (see [MCP server](help:help-mcp-server)). Federated (mesh) queries and the `hgai_mesh_*` tools are admin-only.

## Managing accounts (administrators)

In the **Accounts** screen you can create, edit, and delete accounts. Editing an account also shows a **Space Memberships** tab where you can change a member's role (inline dropdown), remove them from a space, or assign the account to another space. Deleting an account removes it from every space automatically.

REST equivalents (admin only): `/api/v1/accounts` (CRUD) plus:

```bash
# From the space: add alice as a member
curl -X POST http://localhost:8357/api/v1/spaces/my-team/members/alice \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"role": "member"}'

# From the account: assign alice to a space
curl -X POST http://localhost:8357/api/v1/accounts/alice/spaces/my-team \
  -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"role": "member"}'

# List / remove
curl http://localhost:8357/api/v1/accounts/alice/spaces -H "Authorization: Bearer <token>"
curl -X DELETE http://localhost:8357/api/v1/accounts/alice/spaces/my-team -H "Authorization: Bearer <token>"
```

See also [Authentication](help:help-authentication).
