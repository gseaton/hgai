# Mutation Summary

## Intent
Plan tenant-level isolation: accounts assigned to a Tenant see only that tenant's spaces; system admins span all; existing roles pushed down to tenant level.

## Context
Read hgai/models/account.py, space.py, hgai/core/auth.py, space_engine.py, api/deps.py, routers, Mongo indexes, SHQL permission checks, agentchat and notes ownership. Enforcement already funnels through auth.py chokepoints, and space membership is already the sole gate for space graphs.

## What Changed and Why
One new planning document; no code changed.

## Key Decisions
- Single tenant per account in v1; global usernames; global space ids in v1.
- Tenant boundary evaluated before roles and wildcards; cross-tenant returns 404.
- HGAI_MULTITENANCY_ENABLED flag and idempotent migration to a default tenant for backward compatibility.
- Existing admin becomes system_admin; unowned graphs become tenant-level graphs.
- Meshes, agent vendors and telemetry graph stay system-level.
