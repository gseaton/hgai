# Mutation Summary

## Intent
Implement Phase 4 (SHQL, MCP, federation) of the multi-tenancy plan.

## Context
SHQL, MCP and the agent-chat toolkit already funnel through the auth chokepoint that Phase 2 made tenant-aware, so the work was auditing each path, closing gaps, and proving isolation with tests.

## What Changed and Why
Audited every SHQL graph reference, cache ordering, all 30 MCP tools and the REST route table. Closed two gaps: creating a logical graph that composes another tenant's graph, and POST /graphs accepting a client-supplied space_id (a pre-existing way to write into any space). Added tests including a route-inventory guard that fails on an unauthenticated or unguarded route.

## Key Decisions
- No change to SHQL/MCP code paths themselves: enforcement was already central; duplicating checks would risk divergence.
- Composition is validated at creation as well as query time, to stop id probing.
- Federation stays system-admin only.

## Verification
Full suite: 1087 passed; 2 pre-existing mesh-ping failures unrelated.
