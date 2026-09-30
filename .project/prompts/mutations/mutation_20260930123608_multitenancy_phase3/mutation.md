# Mutation Log

## Created
- **hgai/api/routers/tenants.py** — Tenant CRUD routes (system admin writes; tenant admin lists own; accounts read own); delete requires an empty tenant.
- **tests/test_tenancy_phase3.py** — 19 tests: tenant API, tenant-admin account management, spaces/graphs listing, membership, notes, media, saved queries, flag off.

## Modified
- **hgai/core/auth.py** — Added tenant_scope, check_record_tenant, space_visibility.
- **hgai/core/tenant_engine.py** — Added tenant_of_owner, check_member_tenant, delete_tenant.
- **hgai/api/routers/accounts.py** — Rewritten: tenant admins manage own tenant's accounts only, cannot grant admin/system_role or assign another tenant; moves drop space memberships; space assignment tenant-scoped; fixed update crash (version conflict).
- **hgai/api/routers/spaces.py, hypergraphs.py, notes.py, media.py, parameterized_queries.py** — Tenant filtering and boundary checks; same-tenant-only membership and note sharing.
- **hgai/core/engine.py, space_engine.py, notes.py, parameterized_queries.py, media.py** — Tenant filter params, owner stamping, check_media_tenant.
- **hgai_module_mcp/server.py** — Space list/add-member and media tools respect tenants.
- **hgai_module_agentchat/api_router.py, store.py** — Chat sessions stamped with owner's tenant; agent vendors/models use require_system_admin.
- **hgai_module_storage/filters.py, backend.py** — tenant_id filters; TenantStore.count_references; MediaStore.put tenant_id.
- **hgai_module_storage_mongodb/stores/{hypergraphs,spaces,accounts,notes,parameterized_queries,media,media_s3,tenants}.py** — Apply tenant filters; media dedup scoped per tenant; count_references.
- **hgai/main.py** — Registered tenants router.
- **tests/test_tenancy_phase2.py** — set_tenancy helper patches settings so router-bound flag reads are covered.
- **tests/test_authz.py** — Stub query now carries tenant_id.
- **README.md, docs/architecture/hypergraph-ai-multi-tenancy-20260930120844.md** — Tenants API docs; Phase 3 implementation notes.
