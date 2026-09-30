# Mutation Log

## Created
- **tests/test_tenancy_isolation_e2e.py** — 15 end-to-end tests through the ASGI app with real tokens: every graph/space-addressed route generated from the route table returns 404 cross-tenant (alice and tenant admin), notes/media/queries/tenants/accounts, list endpoints and paging totals, system admin scoping, creation stamping, logical-graph composition, SHQL over HTTP, tenant suspension, flag-off behavior, global id uniqueness.

## Modified
- **hgai_module_storage/filters.py** — Added GraphAccess and HypergraphFilters.access.
- **hgai_module_storage_mongodb/stores/hypergraphs.py** — List applies the access filter in the query.
- **hgai/core/auth.py** — Added graph_access_for.
- **hgai/core/engine.py** — list_hypergraphs takes an access filter.
- **hgai/api/routers/hypergraphs.py** — List filters by access in storage, so total and paging are exact.
- **docs/architecture/hypergraph-ai-multi-tenancy-20260930120844.md** — Phase 6 findings.
