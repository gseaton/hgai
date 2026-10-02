# Mutation Log

## Modified
- **hgai/api/routers/hypergraphs.py** — `tenant_id` added to the allowed sort fields of GET /graphs.
- **ui/index.html** — Sortable Tenant column header (hidden by default) in the Hypergraphs table.
- **ui/js/app.js** — `graphTenantColumnVisible()`; loadGraphs shows the column and cell only when visible, sizes colspans, drops a hidden column from the active sort; tenant count kept fresh by the tenant picker.
- **tests/test_tenancy_phase7.py** — Sort by tenant over HTTP; column visibility conditions.
- **tests/conftest.py** — Pins HGAI_MULTITENANCY_ENABLED, HGAI_TELEMETRY_ENABLED and the API-key settings so a developer's .env cannot change test results.
- **docs/help/notes/admin/tenants.md, docs/help/notes/web-ui/web-ui-tour.md** — Documented the column.
