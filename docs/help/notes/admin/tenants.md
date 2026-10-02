---
id: help-tenants
label: Tenants (multi-tenancy)
name: tenants
description: Isolate groups of accounts from each other with tenants, tenant admins and system admins; what is and is not isolated.
tags: ["//Administration", tenant, multi-tenancy, isolation, rbac, admin]
status: active
---

# Tenants

A **tenant** is the top-level isolation boundary. Every account belongs to exactly one tenant (for example `alpha`) and can reach only that tenant's [spaces](help:help-spaces), graphs, notes, media and saved queries. **System admins** sit above tenants and reach everything.

Tenant isolation is **off by default**. Until you turn it on, everything runs in one implicit tenant called `default` and the server behaves as it always has.

## Turning it on

Set `HGAI_MULTITENANCY_ENABLED=true` (see [Configuration](help:help-configuration)) and restart. On every start the server makes sure the `default` tenant exists and stamps every existing record with a tenant: existing accounts, spaces and graphs move into `default`, the old `admin` accounts become system admins, and data owned by a system admin stays system level. The step is safe to repeat.

## Roles

| Level | Role | What it can do |
|---|---|---|
| System | `system_admin` (the old `admin` role) | Everything, in every tenant. Creates and manages tenants. Manages meshes, AI agent vendors and models, telemetry. |
| System | `system_auditor` | **Read-only** in every tenant, for audit and support. See below. |
| Tenant | `tenant_admin` | Everything inside its own tenant: its accounts, spaces and graphs. Cannot see any other tenant. |
| Tenant | `user`, `agent`, `readonly` | As before, inside its own tenant only. |
| Space | `owner`, `admin`, `member`, `viewer` | As before, inside one space of its own tenant. |

A tenant admin cannot grant `admin` or move an account to another tenant, and cannot see system accounts. Only a system admin can.

### System auditor

A system auditor can read graphs (nodes, edges, stats), run SHQL queries, export, and list spaces, accounts and tenants across every tenant. It cannot change anything: every create, update, delete and import is refused (`403`), including through MCP. It also cannot reach users' own **notes, media, saved queries or AI chats**, which are private content rather than audit material. A system admin grants the role when creating an account (`system_role: system_auditor`, or the *System role* field in the account editor); a tenant admin cannot.

## The boundary

The tenant check comes **before** every other check. A `["*"]` graph permission or a space membership never reaches across tenants. This applies on every surface: REST, SHQL (`from:` graphs, including every graph a logical graph composes), the MCP tools and the AI chat agent. Another tenant's resource is reported as **not found** (`404`), never as forbidden, so ids in other tenants cannot be probed.

Suspending a tenant locks out **all** of its accounts at once; system admins are not affected.

## Managing tenants

System admins use the **Tenants** screen, `hgsh`, or the API. See [Web UI tour](help:help-web-ui).

| Endpoint | Purpose |
|---|---|
| `GET/POST /tenants` | List (a tenant admin sees only its own) and create |
| `GET /tenants/{id}` | Read (any account can read its own tenant) |
| `PUT /tenants/{id}` | Change label, description, status, settings |
| `DELETE /tenants/{id}` | Delete an **empty** tenant. `default` cannot be deleted or suspended. |

In the Web UI a system admin also gets a tenant picker in the top bar to scope lists to one tenant. With tenancy on and more than one tenant, the **Hypergraphs** list shows a sortable **Tenant** column for system admins. It is hidden when the picker is scoped to one tenant, when the server has only one tenant, and for every other account, which is locked to its own tenant anyway. `GET /graphs` accepts `sort=tenant_id`. The shell has `use tenant <id>` and `use tenant all`, plus `ls tenants`, `create tenant`, `update tenant` and `delete tenant`. `GET /accounts`, `/spaces` and `/graphs` accept `?tenant_id=` for system admins.

A new account goes into the tenant its creator names (system admin) or the creator's own tenant (tenant admin). Moving an account to another tenant removes its space memberships; the notes, media and saved queries it owns stay in the old tenant.

## Quotas

A tenant can be given limits, kept in its settings: `max_accounts`, `max_spaces`, `max_graphs` (including graphs in spaces), `max_nodes` and `max_edges` (summed over all of the tenant's graphs). Leave one out for no limit. Set them in the tenant editor or with `PUT /tenants/{id}`:

```json
{ "settings": { "quotas": { "max_graphs": 20, "max_nodes": 1000000 } } }
```

Creating something past a limit returns `409` with a message such as `Tenant 'alpha' has reached its limit of 20 graphs (currently 20)`. The limits apply to whoever creates the thing, a system admin included, and only while tenancy is enforced. They are **soft**: they are checked without locking, so two simultaneous creations can overshoot slightly, and a changed limit takes effect within a few seconds. `GET /tenants/{id}/usage` (and `ls usage` in the shell) shows usage against the limits. A tenant that has no node or edge limit pays nothing extra for checking.

## Tenant API keys

The two keys set with `HGAI_PRIMARY_API_KEY` and `HGAI_SECONDARY_API_KEY` are full system admin. For machines that should reach only one tenant, issue a **tenant API key** instead: it acts as an `agent` account of that tenant, limited to the operations it was issued with (`read`, `query`, `write`, `delete`, `export`, `import`; never `admin`), with an optional expiry.

| Endpoint | Purpose |
|---|---|
| `POST /api-keys` | Issue a key. A system admin names the `tenant_id`; a tenant admin's keys use its own. **The secret is returned once.** |
| `GET /api-keys` | List keys (prefix, tenant, operations, last use; never the secret) |
| `DELETE /api-keys/{id}` | Revoke a key |

Manage keys in the **API Keys** screen (system admins and tenant admins): *New API Key* asks for a label, the tenant (system admins only), the operations and an optional expiry, then shows the secret once with a copy button. Use it as `Authorization: Bearer hgai_...` on REST and MCP. Only a hash is stored. A key sees unowned graphs of its tenant; to reach a space's graphs, add the key as a member of that space under the name `apikey:<id>` (only a space of the same tenant is accepted). A key cannot manage accounts, tenants or other keys. Keys stop working when revoked, expired, or their tenant is suspended, and they are refused altogether while tenancy is off, since nothing would confine them. A tenant with keys cannot be deleted until they are revoked.

## What is isolated, and what is not

Isolated per tenant: accounts, spaces, graphs (and their nodes and edges), notes and note sharing, media, saved queries, AI chat sessions. Notes can only be shared with accounts of the same tenant, and a "public" note is public within its tenant.

Shared across the whole server:

- **Usernames, space ids and graph ids are unique server-wide.** Creating one that exists in another tenant returns `409`, which reveals that the id is taken. Use a tenant prefix, such as `alpha-research`.
- **Meshes and federated queries** are system-admin only. A federated query run by a system admin can span tenants by design. Media reached through a mesh is refused to tenant accounts.
- **AI agent vendors and models** and the telemetry status are system-level.
- Isolation is **logical**: tenants share one database and the server enforces the boundary. It is not a substitute for separate deployments where a customer requires physical separation; you can run one server per tenant and join them with a [mesh](help:help-meshes).

## Telemetry

When [telemetry](help:help-telemetry) is on, each event carries a `tenant` field, hashed like the account id unless `HGAI_TELEMETRY_INCLUDE_ACCOUNT_IDS=true`. Events with no tenant, such as those from a system admin, say `__system`. The local `__local-telemetry` graph is system level: only system admins can read it.
