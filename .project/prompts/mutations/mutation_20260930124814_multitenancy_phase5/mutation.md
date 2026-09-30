# Mutation Log

## Created
- **docs/help/notes/admin/tenants.md** — New Tenants help topic.
- **tests/test_tenancy_phase5.py** — 14 tests: /auth/me tenancy fields, telemetry tenant, shell tenant commands, UI wiring markers.

## Modified
- **hgai/models/account.py, hgai/api/routers/auth.py** — MeResponse; GET /auth/me returns multitenancy_enabled and tenant_label.
- **hgai_module_telemetry/events.py** — account dict and events carry a hashed `tenant` (`__system` when none).
- **shell/hgai_shell.py** — tenant CRUD client methods; ls/get/create/update/delete tenant; `use tenant <id>|all`; `use graph <id>`; `--tenant`; tenant scope in prompt and list calls; help text.
- **ui/js/api.js** — tenancy session info (refreshMe), tenant API, tenant scope applied to graph/space/account lists, isTenantAdmin.
- **ui/js/app.js** — async initApp with refreshMe; tenancy-aware visibility; tenant picker; Tenants screen; account editor tenant field and tenant_admin role; Tenant column.
- **ui/index.html** — Tenants sidebar link, screen and modal; tenant picker; sidebar tenant name; account modal tenant and tenant_admin fields; data-tenant-admin markers.
- **README.md, docs/api-reference.md, docs/help/notes/{admin/accounts-roles,admin/configuration,admin/telemetry,concepts/spaces,web-ui/web-ui-tour,home,reference/glossary,reference/faq}.md** — Multi-tenancy documentation.
- **docs/architecture/hypergraph-ai-multi-tenancy-20260930120844.md** — Phase 5 findings.
- **tests/test_telemetry.py** — Event shape includes `tenant`.
