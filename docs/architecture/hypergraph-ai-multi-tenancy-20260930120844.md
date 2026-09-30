# HypergraphAI Multi-Tenancy Plan

Status: proposed plan, not implemented. Generated 2026-09-30.

## 1. Goal

Introduce a top-level **Tenant** entity so that:

- Every non-system account belongs to exactly one tenant (for example `Alpha`) and can only see and act on that tenant's spaces, graphs and data.
- System-wide admin (root) accounts span all tenants and spaces.
- The roles that exist today (`admin`, `user`, `agent`, `readonly` plus the four space roles) are pushed down to the tenant level, while a small set of **system roles** remains above tenants.
- Existing single-tenant deployments keep working unchanged.

## 2. Current State (what the plan builds on)

| Area | Today | Source |
|---|---|---|
| Account roles | Global: `admin`, `user`, `agent`, `readonly`. `admin` bypasses every check. | `hgai/models/account.py`, `hgai/core/auth.py` |
| Account permissions | `permissions.graphs` (list or `*`) and `permissions.operations`, account-wide. | `AccountPermissions` |
| Spaces | Namespaces with members and space roles (`owner`, `admin`, `member`, `viewer`). Space membership is the sole gate for space graphs. Space ids are globally unique. | `hgai/models/space.py`, `hgai/core/space_engine.py` |
| Graphs | Either in a space (`space_id` set) or **unowned** (`space_id` null, id globally unique, gated by `permissions.graphs`). | `hgai_module_storage_mongodb/indexes.py` |
| Enforcement | One chokepoint: `check_graph_permission`, `can_access_graph`, `can_perform`, `check_space_role`, `filter_accessible_graphs`. Used by REST deps, SHQL and MCP. | `hgai/core/auth.py`, `hgai/api/deps.py` |
| Account admin | All `/accounts` routes require `admin`. | `hgai/api/routers/accounts.py` |
| Owner-scoped data | Notes (owner plus ACL), agent chat sessions and prompt history (per account). | `hgai/core/notes.py`, `hgai_module_agentchat` |
| Global resources | Meshes (admin only), agent chat vendors and models (admin write), audit log, query cache, media, parameterized queries. | various |
| API keys | Two configured keys map to a synthetic full-admin account. | `_api_key_account` |

The existing space gate already proves the pattern: membership, not a wildcard, decides access. Multi-tenancy lifts that idea one level up and makes it mandatory.

## 3. Target Model

```
System (root)
  |
  +-- Tenant "Alpha"
  |     +-- Accounts (tenant roles)
  |     +-- Spaces (space roles, as today)
  |     |     +-- Graphs -> nodes, edges
  |     +-- Tenant-level graphs (today's "unowned" graphs, now tenant scoped)
  |     +-- Tenant-owned data: notes, media, saved queries, chat sessions
  |
  +-- Tenant "Bravo"  (same shape, fully isolated from Alpha)
  |
  +-- System-level resources: meshes, agent vendors and models, telemetry graph, tenants themselves
```

### 3.1 The Tenant entity

New `tenants` collection, following the conventions of `spaces` (`TimestampedModel`, `Status`).

| Field | Type | Notes |
|---|---|---|
| `id` | string | Slug, unique. No dots (same rule as space ids). Reserved: `__system`. |
| `label` | string | Display name. |
| `description` | string | Optional. |
| `status` | `active` or `suspended` | Suspension blocks all tenant accounts (see 5.2). |
| `attributes`, `tags` | document, list | Free-form, like other entities. |
| `settings` | document | Reserved for later: quotas, allowed features, default space role. |

Tenant ids should be immutable once created, because they are stamped onto other records.

### 3.2 Tenant stamped on resources

| Resource | Change |
|---|---|
| Account | `tenant_id` (required for tenant accounts, null for system accounts). |
| Space | `tenant_id` (required, immutable). |
| Hypergraph | `tenant_id`, denormalized from its space, or set directly for tenant-level graphs. Null only for system-level graphs. |
| Notes, media, parameterized queries, SHQL history, chat sessions, prompt history, audit log entries | `tenant_id` of the owning account or resource. |
| Query cache entries | Key already includes the graph reference. Confirm it cannot collide across tenants (see 7.4). |

Nodes and edges are addressed through their graph, so they inherit tenancy from the graph check. Stamping `tenant_id` on them is not required in v1.

## 4. Role Model

### 4.1 Two role layers

**System roles** (on the account, apply across tenants):

| Role | Meaning |
|---|---|
| `system_admin` | Root. Access to all tenants, spaces and graphs. Creates and manages tenants. Replaces today's global `admin`. |
| `system_auditor` (optional, phase 7) | Read-only across all tenants for audit and support. |

**Tenant roles** (on the account, scoped to its tenant):

| Role | Replaces | Meaning |
|---|---|---|
| `tenant_admin` | `admin` (scoped) | Manage accounts, spaces and tenant-level graphs within the tenant. Cannot see other tenants. |
| `user` | `user` | Read and write per the tenant's spaces and grants. |
| `agent` | `agent` | API and MCP only, same as today, confined to the tenant. |
| `readonly` | `readonly` | Read-only within the tenant. |

**Space roles** (`owner`, `admin`, `member`, `viewer`) are unchanged and remain scoped to one space. A space role can never reach outside the space's tenant.

### 4.2 Account model changes

```
AccountBase:
  system_role:  Optional[SystemRole]        # None for tenant accounts
  tenant_id:    Optional[str]               # None only for system accounts
  roles:        List[Role]                  # now tenant roles: tenant_admin, user, agent, readonly
  permissions:  AccountPermissions          # graphs/operations now resolved inside the tenant only
```

Invariants, enforced in the account engine and validated in the model:

1. `system_role` set implies `tenant_id` may be null.
2. `system_role` not set implies `tenant_id` is required and must reference an active tenant.
3. A `tenant_admin` needs a `tenant_id`.

**Single tenant per account in v1.** This keeps the login flow, tokens and UI simple and the isolation argument easy to state. A person who works for two tenants gets two accounts. Multi-tenant membership is a listed extension (phase 7) and the plan avoids painting into a corner: `tenant_id` can later become a `memberships` list with an "active tenant" chosen at login.

### 4.3 Migration of existing roles

| Existing | Becomes |
|---|---|
| Account with `admin` | `system_role = system_admin`, `tenant_id = null` |
| Account with `user`, `agent` or `readonly` | Same role, `tenant_id = "default"` |
| `permissions.graphs` entries for unowned graphs | Unchanged, now interpreted inside the account's tenant |
| Configured API keys | Remain `system_admin` (see 6.4 for tenant-scoped keys) |

The literal role value `admin` is accepted on read and normalized to `system_admin`, so stored data, tokens and scripts written against the current model keep working during the transition.

## 5. Access Resolution

### 5.1 New order of evaluation

For any request against a resource (graph, space, note, media, and so on):

1. **System admin.** `system_role == system_admin` passes everything.
2. **Tenant boundary.** Resolve the resource's `tenant_id`. If it differs from the account's `tenant_id`, deny. This check comes before any role, space or wildcard logic, so `permissions.graphs = ["*"]` can never cross tenants.
3. **Tenant admin.** A `tenant_admin` passes everything inside its tenant.
4. **Space membership.** For space graphs, the account must be a member of the space (as today), and the space role decides the operations.
5. **`permissions.graphs` and `permissions.operations`.** Apply to tenant-level graphs only, as today, but inside the tenant.

The existing space rule is preserved exactly. The tenant boundary is added in front of it.

### 5.2 Tenant status

`authenticate_token` already rejects inactive accounts. It will also reject an account whose tenant is suspended or missing, so suspending a tenant locks out every tenant account immediately without touching each one. Tokens stay valid only as long as the account and tenant are active, because the account is reloaded from storage on every request.

### 5.3 Do not trust the token

JWTs carry `sub` and `roles` today, and the server reloads the account on each request. Keep that. A `tenant_id` claim may be added for convenience (UI display, logging) but **authorization must always use the freshly loaded account**, so a stale or forged claim cannot widen access.

### 5.4 Denial behavior

For a resource in another tenant, return **404**, not 403, so a caller cannot probe which ids exist in other tenants. Within a tenant, keep today's 403 semantics.

## 6. Implementation Plan

### Phase 0. Decisions (before code)

Confirm the open questions in section 10. The plan assumes the recommended answers.

### Phase 1. Model, storage and migration

1. Add `Tenant` models (`hgai/models/tenant.py`): create, update, response, `TenantStatus`.
2. Add a `TenantStore` ABC to `hgai_module_storage/backend.py` and a MongoDB implementation in `hgai_module_storage_mongodb/stores/tenants.py`. Keep all storage access behind the abstract interface, as the storage rules require.
3. Add `tenant_id` to `SpaceBase`, `HypergraphBase`, `AccountBase` and the owner-scoped models listed in 3.2. Add `system_role` to accounts and the new role enums.
4. Indexes (`indexes.py`):
   - `tenants.id` unique.
   - Tenant-level graphs: replace the global unique `id` (where `space_id` is null) with unique `(tenant_id, id)`.
   - Space-graph unique `(id, space_id)` is unchanged, since a space belongs to one tenant.
   - `tenant_id` index on accounts, spaces, hypergraphs, notes, media, parameterized queries.
5. **Startup migration** (idempotent, safe to run on every boot, like `ensure_indexes`):
   - Create tenant `default` if missing.
   - Stamp `tenant_id = "default"` on every existing space, unowned graph, non-admin account and owner-scoped record that lacks one.
   - Convert accounts holding `admin` to `system_admin`.
   - Log counts of what changed.
6. **Compatibility switch** `HGAI_MULTITENANCY_ENABLED` (default `false`). When false, everything runs in the implicit `default` tenant, the tenant UI and routes are hidden, and behavior matches today. When true, tenants are enforced and the admin UI exposes them. This lets the code ship and be tested before any deployment turns it on.

### Phase 2. Auth chokepoint

All enforcement already funnels through `hgai/core/auth.py`, so most of the work is here:

1. Replace the repeated `"admin" in account.roles` checks with helpers: `is_system_admin(account)` and `is_tenant_admin(account)`. Audit every call site (`grep` for `"admin" in`), including `require_admin`, `can_access_graph`, `can_perform`, `check_space_role`, `filter_accessible_graphs`, `require_admin_role`, and the MCP and mesh modules.
2. Add `check_tenant_boundary(account, resource_tenant_id)` and call it first in each function of 5.1.
3. Resolve a graph's tenant without an extra query where possible: spaces and graphs carry `tenant_id`, and `space_id` is usually already known to the caller.
4. `filter_accessible_graphs`: drop other tenants' graphs first, then apply the existing space and permission logic.
5. `require_admin` splits into `require_system_admin` (tenants, meshes, vendors, global settings) and `require_tenant_admin` (account and space management inside a tenant).
6. `authenticate_token`: reject accounts whose tenant is suspended or missing (5.2).

### Phase 3. API

| Route group | Change |
|---|---|
| `/tenants` (new) | System admin: create, list, get, update, suspend, delete. Tenant admin: read own tenant. |
| `/accounts` | System admin manages all accounts. Tenant admin manages accounts in its own tenant only, cannot grant `system_admin` or create accounts in another tenant. Creating an account requires a `tenant_id` unless it is a system account. |
| `/spaces` | Create stamps the caller's tenant. List is filtered to the caller's tenant (system admin may pass `tenant_id`). Membership can only add accounts of the same tenant. |
| `/graphs` (flat, unowned) | Now tenant-level graphs: created in and listed from the caller's tenant. System admin may target a tenant explicitly. |
| Hypernodes, hyperedges, inference, import, export | Inherit the graph check. Verify import endpoints that create graphs stamp the tenant. |
| Notes and media | Stamp tenant. Note sharing (ACL grants) only to accounts in the same tenant. |
| Parameterized queries, SHQL history | Stamp tenant and filter by it. |
| Meshes, agent vendors | System admin only, as today (see 7.2). |
| Agent chat sessions | Owner-only as today, plus tenant stamp. |

### Phase 4. SHQL, MCP, federation

1. **SHQL `from:`**: `_check` in `hgai_module_shql/engine.py` already calls `check_graph_permission` per graph reference. With the tenant boundary inside that function, a cross-tenant `space/graph` reference is denied. Add tests for mixed-tenant `from:` lists. Bare (unowned) graph ids must resolve **within the caller's tenant** first, so two tenants can each have a graph named `people`.
2. **MCP**: tools call the same chokepoint, so they inherit the boundary. `hgai_hypergraph_list`, `hgai_space_list` and the other list tools must be checked for tenant filtering. Agent accounts are ordinary tenant accounts with the `agent` role.
3. **Federation and mesh**: stays system-admin-only in v1. A federated query by a system admin can span tenants by design. Tenant-scoped meshes are a later extension.
4. **Agent chat MCP toolkit**: it forwards a per-account bearer token, so the tenant boundary applies through the normal auth path. Add a test that an agent session for tenant A cannot reach tenant B data.

### Phase 5. UI, shell, telemetry

1. **Web UI**: a Tenants admin screen for system admins. A tenant picker ("all tenants" or one tenant) for system admins, so they can act within one tenant. Tenant admins see their tenant's Accounts and Spaces screens. Regular users see no tenant controls, only a tenant name in the header.
2. **Shell (`hgsh`)**: tenant commands for system admins, and a `--tenant` or `use tenant` option.
3. **Telemetry**: add a `tenant` attribute to events (hashed by default, like account and graph ids), so usage and errors can be analyzed per tenant. The `actor` field is already present (`__system` when no account acted). The local `__local-telemetry` graph is a **system-level graph** with null tenant, reachable only by system admins.
4. **Docs**: README, API reference, help topics (Accounts, Spaces, Configuration), and a new admin help topic for tenants.

### Phase 6. Tests

Add a tenant isolation suite with two tenants, `alpha` and `bravo`, each with a tenant admin, a user, an agent and a read-only account, plus a system admin. Cover at least:

- Every list endpoint returns only the caller's tenant data.
- Direct get, update and delete by id across tenants returns 404 on every router.
- `permissions.graphs = ["*"]` does not cross tenants.
- A tenant admin cannot create accounts in another tenant or grant `system_admin`.
- Space membership cannot add an account from another tenant.
- SHQL with cross-tenant `from:`, and with a bare graph name existing in both tenants.
- MCP tools and the agent chat toolkit.
- Note sharing across tenants is refused.
- Suspended tenant locks out its accounts and only them.
- System admin sees everything and can act per tenant.
- Migration: existing data ends up in `default`, old `admin` accounts become `system_admin`, running it twice changes nothing.
- With `HGAI_MULTITENANCY_ENABLED=false`, the existing suite passes unmodified.

### Phase 7. Later extensions (not in v1)

- Multi-tenant membership with an active tenant per session.
- Tenant-scoped API keys for machine-to-machine access (the two configured keys stay system-level).
- `system_auditor` role.
- Per-tenant quotas (graphs, nodes, storage, request rate) using `Tenant.settings`.
- Tenant-scoped meshes and agent model enablement.
- Stronger isolation options: per-tenant database or collection prefix, per-tenant encryption keys.
- Tenant-aware mesh federation.

## 7. Design Decisions and Trade-offs

### 7.1 Usernames stay globally unique

Login has no tenant field today, so a global username is what makes sign-in work. Per-tenant usernames would need a tenant in the login form or a tenant-specific login URL. Recommended for v1: global uniqueness, with operators using a convention such as `alice@alpha` if they need to.

### 7.2 Global resources stay system-level

Meshes, agent chat vendors (they hold encrypted provider keys), and the telemetry graph are system concerns. Exposing them per tenant multiplies the security surface for little v1 benefit.

### 7.3 Space ids: globally unique or per tenant

- **Keep globally unique (recommended v1).** Space references (`space/graph`, mesh dot-notation) stay unchanged, with no SHQL or federation format change. Cost: two tenants cannot both have a space named `ops`.
- **Unique per tenant.** Friendlier naming, but every space reference needs tenant context, which touches SHQL parsing, mesh notation and the UI. Defer.

Tenant-level graphs, by contrast, become unique per tenant in v1, because the flat `/graphs/{id}` routes can resolve the tenant from the caller.

### 7.4 Denormalize `tenant_id` onto graphs

A graph's tenant is derivable through its space, but the check runs on every request. Stamping it on the graph avoids a second lookup and gives tenant-level graphs a home. The cost is keeping it consistent: a space's tenant is immutable, and moving a graph between spaces is only allowed within a tenant. Verify the query cache key (graph reference based) cannot return one tenant's cached result to another tenant, in particular for tenant-level graphs that share an id across tenants. If it can, include `tenant_id` in the key.

### 7.5 Logical, not physical, isolation

v1 isolates tenants by enforcement in the application and by stamped ids and indexes in a shared database. That is the same model spaces use today. It is appropriate for trusted-operator deployments. It is not a substitute for physical separation where a customer requires it. Phase 7 lists stronger options, and a deployment that needs hard separation today can run a separate server per tenant and join them with the existing mesh.

## 8. Security Risks and Mitigations

| Risk | Mitigation |
|---|---|
| A route misses the tenant check (the main risk) | All checks go through one chokepoint. Inventory every router and MCP tool. Add the tenant isolation test suite and a test that enumerates routes and fails if a graph- or tenant-scoped route has no access dependency. |
| Existence leaks via 403 versus 404 | Cross-tenant returns 404 (5.4). |
| Wildcard permissions crossing tenants | Tenant boundary is evaluated before permissions (5.1). |
| Tenant admin escalation | Tenant admins cannot set `system_role` or `tenant_id` to another tenant. Enforced in the account engine, not only the router. |
| Stale or forged token claims | Authorize from the reloaded account only (5.3). |
| Cache or history leakage across tenants | Tenant in cache key where needed, tenant stamp and filter on history and saved queries. |
| Import or restore writing to the wrong tenant | Imports stamp the caller's tenant. System admin imports must name the tenant explicitly. |
| Orphaned data on tenant deletion | Deleting a tenant requires it to be empty, or an explicit cascade that mirrors `delete_space(delete_graphs=True)`. |
| Audit gaps | Include `tenant_id` in audit entries and require tenant administration actions to be audited under the caller. |

## 9. Rollout

1. Ship Phases 1 to 4 with `HGAI_MULTITENANCY_ENABLED=false`. Existing deployments see no change except the new fields and the `default` tenant.
2. Enable the flag in a test environment, create two tenants, run the isolation suite.
3. Turn on for a pilot deployment. Reassign accounts and spaces from `default` to real tenants using a system admin tool (a move operation that re-stamps an account, or a space with its graphs, to another tenant).
4. Document the operator procedure and the rollback (disable the flag; data remains stamped and harmless).

## 10. Open Questions

1. Should an account ever belong to more than one tenant in v1? Recommended: no.
2. Should space ids stay globally unique in v1? Recommended: yes.
3. Should tenants be able to hold tenant-level graphs outside spaces, or should everything live in a space? Recommended: keep tenant-level graphs, because today's unowned graphs map to them and migration is trivial.
4. Is a shared, read-only "reference" graph visible to all tenants needed (for example a common vocabulary)? If so, add an explicit `shared` flag on system-level graphs, read-only for tenants.
5. Should tenant admins be able to create API keys or agent accounts for their own tenant in v1? Agent accounts: yes, through normal account creation. Tenant-scoped API keys: later.
6. Is logical isolation sufficient for the first multi-tenant customers, or is a per-tenant database required from the start?

## 11. Implementation Notes

### Phase 3 findings

- **Unowned graph ids stay globally unique (deviation from 7.3/6 Phase 1).** The plan made tenant-level graph ids unique per tenant. Implementation showed nodes and edges are keyed by the graph reference (`hypergraph_id` is the bare graph id for an unowned graph), so two tenants sharing an id would share node and edge collections. Making ids per-tenant requires tenant-qualified graph references throughout storage, SHQL and mesh notation. Phase 3 therefore keeps the existing global unique index and only adds a non-unique `(tenant_id, id)` index. Consequence: creating a graph or space whose id exists in another tenant returns 409, which reveals that the id exists. Operators should use a tenant prefix convention.
- **Media dedup is per tenant.** Identical bytes uploaded by two tenants are two records. Global dedup would hand one tenant another tenant's media id.
- **Mesh-proxied media** (`server/id`) uses the mesh's admin credentials, so tenant accounts may not fetch it while tenancy is enforced.
- **Moving an account between tenants** drops its space memberships. Data it owns (notes, media, saved queries) stays in the old tenant.
- **Per-account data** (SHQL history, chat sessions and messages) is already owner-only. Chat sessions are stamped with the owner's tenant; SHQL history needed no change.
- **Fixed an existing bug:** `PUT /accounts/{username}` always failed, because the update carried `version` and the store also `$inc`s it.

### Phase 4 findings

- **SHQL, MCP and the agent-chat toolkit needed no new enforcement code.** Every `from:` graph, every member of a logical graph, and every MCP graph or space tool already goes through `check_graph_permission` / `check_space_role`, which carry the tenant boundary since Phase 2. SHQL authorizes before it reads the result cache, so a cached result is never served across tenants. The toolkit calls the MCP endpoint with the account's own bearer token, so it takes the same path. What Phase 4 added is proof (tests) and the gaps below.
- **Gap closed: composing another tenant's graph.** A logical graph could reference another tenant's graph at creation; query time denied it, but the reference itself could be created and used to probe ids. REST create and update (unowned and space graphs) and both import routes now reject it with 400, unless the caller is a system admin.
- **Existing hole closed: `POST /graphs` honoured a client-supplied `space_id`.** That placed a graph in any space, including another tenant's, without membership. The route now forces the graph to be unowned.
- **Errors do not reveal other tenants' graphs.** A cross-tenant graph in SHQL and MCP is reported as "not found", not "not permitted".
- **Federation stays system-admin only**: mesh references in SHQL and every `hgai_mesh_*` tool. Tenant-scoped meshes remain a Phase 7 item.
- **Route inventory test** walks all REST routes (including those of included routers) and fails if any route other than the four public ones lacks an authentication dependency, or any route addressed by `{graph_id}` or `{space_id}` lacks an access guard.

### Phase 5 findings

- **`GET /auth/me` carries tenancy** (`multitenancy_enabled`, `tenant_id`, `system_role`, `tenant_label`). The Web UI reads it once per session start instead of trusting the login response, and hides all tenancy UI when the server does not enforce tenancy or the call fails.
- **Web UI.** Tenants screen (system admin), a top-bar tenant picker that scopes graph, space and account lists, the tenant name in the sidebar for other users, and a Tenant field and `tenant_admin` role in the account editor. A tenant admin sees only the Spaces and Accounts screens, for its own tenant. Checked by hand in a browser against a live server with a system admin, a tenant admin and a regular user.
- **Shell.** `ls/get/create/update/delete tenant`, `use tenant <id>|all`, `--tenant`; `use graph <id>` reaches a graph whose id is `tenant`.
- **Telemetry.** Events carry `tenant`, hashed like the account id; `__system` when no tenant applies.
- **Docs.** New *Tenants* Help topic; README, API reference, Accounts, Spaces, Configuration, Web UI tour, Glossary, FAQ and Telemetry topics updated.

### Phase 6 findings

- **Plan item to implementation.** Every bullet of the Phase 6 test list is covered: list endpoints, cross-tenant get/update/delete, wildcard and membership, tenant-admin limits, membership across tenants, SHQL, MCP, note sharing, suspension, system admin, migration, and the flag-off suite. Phases 2 to 5 tested the pieces by calling functions directly. `tests/test_tenancy_isolation_e2e.py` adds the missing layer: real HTTP through the ASGI app, real tokens, real status codes.
- **Generated from the route table.** The cross-tenant check walks every route addressed by `{graph_id}` or `{space_id}` (50 method/path pairs today) and requests Bravo's resources as an Alpha user and as an Alpha tenant admin, expecting 404. A route added later is covered automatically; a route that skips the boundary fails the test.
- **Bug found and fixed: paging totals.** `GET /graphs` filtered by access after paging, so for an ordinary account `total` was the size of the filtered page, not the real count. The access rule (space membership, `permissions.graphs`) is now applied in storage together with the tenant filter, so `total`, `skip` and `limit` are exact.
- **Bare graph names in two tenants** (plan item) does not apply: ids are unique server-wide (see Phase 3). A clash returns 409, which a test pins down.
- **Not covered:** the MCP endpoint over HTTP with a bearer token. The MCP session manager can start only once per process and `tests/test_authz.py` already uses it, with faked accounts. Tool-level isolation is tested with a real database in Phase 4, and token-to-account resolution (including tenant suspension) in Phase 2.

### Phase 7 findings

Implemented from section 6 Phase 7: the system auditor, per-tenant quotas and tenant-scoped API keys. **Not implemented** (left for later, each as large as an earlier phase): multi-tenant membership with an active tenant per session, tenant-scoped meshes and agent model enablement, per-tenant databases or encryption keys, and tenant-aware mesh federation.

- **System auditor** (`system_role: system_auditor`). Reads graphs, SHQL, export, spaces, accounts and tenants in every tenant; every write is refused. Enforced in two places: the graph and space checks (`can_perform`, `check_graph_permission`, `check_space_role`, which ignore the account's own `permissions.operations`), and one central guard on every authenticated REST request that refuses anything that is not a read, apart from a short list of read-only POSTs (`/shql/query`, `/shql/validate`, `/export`, `/infer/transitive`, `/infer/expand`, and the two telemetry and history calls). MCP's unguarded create and delete tools check separately. Notes, media, saved queries and AI chats are blocked outright: a tenant's private content is not audit material, and the tenant boundary would hide it anyway.
- **Quotas** (`Tenant.settings.quotas`: accounts, spaces, graphs, nodes, edges). Checked at creation, returning `409`. Soft by design: no locking, so concurrent creations can overshoot. Node and edge checks run on every create, so a tenant's limits and a graph's tenant are cached for five seconds; a tenant with no node or edge limit pays only that cached lookup. Applies to system admins too, since the limit belongs to the tenant.
- **API keys.** `hgai_` plus 32 random bytes, stored as a SHA-256 hash with a short prefix to recognise it, looked up by hash. A key becomes a synthetic `agent` account named `apikey:<id>` in its tenant, limited to the operations it was issued with, so it passes through the same tenant boundary as any account. Refused when revoked, expired, its tenant is suspended, or tenancy is off. Data a key creates (notes, media, graphs) is stamped with the key's tenant, and a key can join spaces of its own tenant only. The two configured keys are unchanged and still full system admin. Manage them in the Web UI's API Keys screen (see the UI note below), the API, or `hgsh` (`ls/create/delete apikey`).
- **Test suite.** `tests/conftest.py` now holds one session-wide `mongod` fixture. Each test module had started its own server, and the tenancy modules had grown that to 4.6 GB of journal files in `/tmp` per run, enough to make later runs slow and skip.

### Phase 7 follow-up: Web UI

The Phase 7 UI work was checked in a browser against a live server (tenancy on). Quota fields in the tenant editor save and reload correctly; the System role select creates a `system_auditor` account (no tenant, shown as "system" in the list); the new **API Keys** screen (system admin, and tenant admin for its own tenant) creates a key, shows the secret once in a dialog that clears it on close, lists keys with prefix, operations, expiry and last use, and revokes through the standard confirm dialog. A created key authenticated, created a graph stamped with its tenant, and was refused with 401 once revoked. A tenant admin sees no tenant selector and gets its own tenant's key.

