# Mutation Log

## Created
- **tests/test_tenancy_phase2.py** — 19 tests on real mongod: stamping at creation, tenant boundary (access, perform, space role, filter), tenant admin, system admin, REST 404 mapping, flag-off behavior, tenant suspension, role gates, account creation.

## Modified
- **hgai/core/auth.py** — Added TenantBoundaryError, is_system_admin, is_tenant_admin, multitenancy_on, can_administer_tenant, require_system_admin (require_admin kept as alias), require_tenant_admin; tenant boundary evaluated first in can_access_graph, can_perform, check_graph_permission, check_space_role, filter_accessible_graphs; authenticate_account and authenticate_token reject accounts of a suspended or missing tenant.
- **hgai/core/tenant_engine.py** — Added tenant_for_new_record.
- **hgai/core/engine.py, hgai/core/space_engine.py** — create_hypergraph and create_space stamp tenant_id.
- **hgai/api/deps.py** — TenantBoundaryError maps to 404.
- **hgai/api/routers/accounts.py** — Create assigns default tenant, validates tenant when tenancy is on; uses require_system_admin.
- **hgai/api/routers/hypergraphs.py** — List uses filter_accessible_graphs.
- **hgai/api/routers/notes.py, spaces.py, media.py; hgai_module_agentchat/api_router.py, hgai_module_mcp/server.py, hgai_module_mesh/api_router.py, hgai_module_shql/engine.py, hgai_module_telemetry/api_router.py** — Replaced raw "admin" role checks and require_admin with is_system_admin and require_system_admin.
- **README.md** — Access order notes the tenant boundary.
