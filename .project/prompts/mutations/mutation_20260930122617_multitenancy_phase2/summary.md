# Mutation Summary

## Intent
Implement Phase 2 (auth chokepoint) of docs/architecture/hypergraph-ai-multi-tenancy-20260930120844.md.

## Context
All graph and space authorization already funnels through hgai/core/auth.py, used by REST, SHQL and MCP, so enforcement was centralized there. Everything is gated on HGAI_MULTITENANCY_ENABLED, default off.

## What Changed and Why
Tenant boundary runs before roles, space membership and wildcards; tenant_admin gets full rights in its tenant; cross-tenant REST access returns 404; suspended or missing tenant blocks login and token auth; system-only routes use require_system_admin. New spaces and graphs are stamped with the creator's tenant so enforcement has data to check.

## Key Decisions
- Stamping at creation pulled forward from Phase 3: without it, new graphs would read as system-level and be denied.
- tenant_admin powers apply only while the flag is on, so a stray role cannot widen access in legacy mode.
- Hypergraph list route now uses filter_accessible_graphs; this also closes a pre-existing gap where a "*" holder saw non-member space graphs.
- Remaining for Phase 3: tenant routes, tenant-filtered space list, notes/media/saved-query/chat tenant enforcement, unique per-tenant graph index, same-tenant-only space membership.

## Verification
Full suite: 1041 passed; 2 pre-existing mesh-ping failures unrelated.
