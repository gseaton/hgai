# Mutation Log

## Created
- **hgai/models/tenant.py** — Tenant models (TenantBase/Create/Update/InDB/Response, TenantStatus), DEFAULT_TENANT_ID, SYSTEM_TENANT_ID, SYSTEM_GRAPH_IDS, id validation.
- **hgai/core/tenant_engine.py** — Tenant CRUD, ensure_default_tenant, run_tenancy_migration, effective_tenant_id, validate_account_tenancy.
- **hgai_module_storage_mongodb/stores/tenants.py** — MongoTenantStore.
- **hgai_module_storage_mongodb/tenancy_migration.py** — Idempotent startup migration stamping tenant_id and system_role.
- **tests/test_tenancy_phase1.py** — 21 tests: models, store CRUD, validation, migration, idempotency, indexes (real mongod).

## Modified
- **hgai/models/account.py** — Added Role.tenant_admin, SystemRole, account system_role and tenant_id fields, validator mapping legacy admin to system_admin; AccountUpdate fields.
- **hgai/models/space.py, hypergraph.py, note.py, media.py, parameterized_query.py, hgai_module_agentchat/models.py** — Added optional tenant_id.
- **hgai_module_storage/filters.py** — Added TenantFilters, TenantPatch.
- **hgai_module_storage/backend.py** — Added TenantStore ABC, StorageBackend.tenants and migrate_tenancy.
- **hgai_module_storage_mongodb/backend.py** — Wired tenants store and migrate_tenancy.
- **hgai_module_storage_mongodb/indexes.py** — Added tenants indexes and tenant_id indexes on accounts, spaces, hypergraphs, notes, media, parameterized_queries.
- **hgai/config.py, .env.example, README.md, docs/help/notes/admin/configuration.md** — Added HGAI_MULTITENANCY_ENABLED (default false).
- **hgai/main.py** — Startup runs run_tenancy_migration after admin bootstrap.
