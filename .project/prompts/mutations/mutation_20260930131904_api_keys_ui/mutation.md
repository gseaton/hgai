# Mutation Log

## Modified
- **ui/index.html** — API Keys sidebar link and screen (table, tenant-admin visible), New API Key modal with a one-time secret view.
- **ui/js/api.js** — listApiKeys, createApiKey, revokeApiKey, getTenantUsage.
- **ui/js/app.js** — API Keys screen: load, create (tenant select for system admins only, operations, expiry), one-time secret with copy and clear on close, revoke through the confirm dialog.
- **tests/test_tenancy_phase5.py** — data-tenant-admin marker count updated (7).
- **tests/test_tenancy_phase7.py** — Added API Keys UI marker test.
- **README.md, docs/help/notes/admin/tenants.md, docs/help/notes/web-ui/web-ui-tour.md, docs/architecture/hypergraph-ai-multi-tenancy-20260930120844.md** — Documented the screen; recorded the browser verification.
