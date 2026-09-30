# Mutation Log

## Created
- **hgai/models/api_key.py, hgai/core/api_keys.py, hgai/api/routers/api_keys.py, hgai_module_storage_mongodb/stores/api_keys.py** — Tenant-scoped API keys: models, creation and resolution, REST routes, Mongo store.
- **tests/test_tenancy_phase7.py** — 29 tests: system auditor (HTTP, MCP, functions), quotas, API keys, shell and UI hooks.
- **tests/conftest.py** — One session-wide mongod fixture.

## Modified
- **hgai/models/account.py, hgai/core/tenant_engine.py** — SystemRole.system_auditor; is_system_account covers any system role; QuotaExceededError, enforce_quota (cached), tenant_usage, key-aware tenant_for_new_record, tenant_of_owner, check_member_tenant.
- **hgai/core/auth.py** — Auditor helpers (is_system_auditor, sees_all_tenants), central read-only guard, require_tenant_reader, auditor handling in every graph/space check, stored API key authentication.
- **hgai/models/tenant.py** — TenantQuotas and settings validation.
- **hgai/core/engine.py, space_engine.py, api/routers/accounts.py** — Quota checks on graphs, spaces, accounts, nodes, edges.
- **hgai/api/routers/{tenants,accounts,hypergraphs,spaces}.py** — Reader dependency for auditors; usage endpoint; tenant_id filter for auditors.
- **hgai/main.py** — Quota 409 handler; api-keys router.
- **hgai_module_mcp/server.py** — Write tools refuse auditors.
- **hgai_module_storage/backend.py, filters.py (unchanged here), hgai_module_storage_mongodb/{backend,indexes}.py, stores/tenants.py** — ApiKeyStore, usage(), count_references includes api_keys, indexes.
- **shell/hgai_shell.py** — ls apikeys/usage, create/delete apikey.
- **ui/index.html, ui/js/app.js** — System role select in account editor; quota inputs in tenant editor.
- **tests/storage_fixtures.py and 9 test modules** — mongod fixture moved to conftest (imports removed).
- **README.md, docs/api-reference.md, docs/help/notes/admin/{tenants,accounts-roles}.md, docs/architecture/hypergraph-ai-multi-tenancy-20260930120844.md** — Documentation and Phase 7 findings.
