# Mutation Summary

## Intent
Implement Phase 1 (model, storage, migration, compatibility switch) of docs/architecture/hypergraph-ai-multi-tenancy-20260930120844.md.

## Context
Phase 1 is additive: no enforcement (Phase 2), no API routes (Phase 3). Legacy `admin` in roles is kept so existing auth checks keep working.

## What Changed and Why
Tenant entity and store, tenant_id fields, system_role, indexes, an idempotent startup migration into a `default` tenant, and the HGAI_MULTITENANCY_ENABLED flag (stored, not yet read by enforcement code).

## Key Decisions
- Kept global-unique unowned graph index; added non-unique (tenant_id, id). The swap to unique per-tenant is deferred to Phase 3 because graph lookups are not tenant-aware yet.
- Explicit null tenant_id means system level (e.g. __local-telemetry graph, data owned by system accounts); the migration only touches records with no tenant_id field, making it idempotent.
- Space graphs take their space's tenant during migration.
- New records created after startup are not stamped until Phase 3 or next boot; missing tenant reads as default.

## Verification
Full suite: 1022 passed; 2 pre-existing mesh-ping failures unrelated.
