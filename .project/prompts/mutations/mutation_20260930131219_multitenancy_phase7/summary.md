# Mutation Summary

## Intent
Implement Phase 7 (optional extensions) of the multi-tenancy plan. The phase is a list of items, several as large as earlier phases, so the user was asked which to do and chose the system auditor, per-tenant quotas and tenant-scoped API keys.

## What Changed and Why
- Auditor: a read-only system role, enforced in the graph/space checks and by one central request guard; private user content is blocked.
- Quotas: limits in Tenant.settings, checked at creation, 409 on excess, cached lookups so bulk imports stay cheap.
- API keys: hashed, tenant-bound, acting as agent accounts through the normal tenant boundary; refused while tenancy is off.
- Test infrastructure: a single session mongod fixture, because per-module servers had grown to 4.6 GB of /tmp per run and made the suite slow and flaky.

## Key Decisions
- Auditors cannot read notes, media, saved queries or chats: private content, and the tenant boundary would hide it anyway.
- Quotas apply to system admins too; soft limits, documented.
- Keys are tenant-only (no system-level stored keys) and need tenancy on.
- Not done: multi-tenant membership, tenant-scoped meshes, per-tenant databases/keys, tenant-aware federation.

## Verification
Full suite 1145 passed; 2 pre-existing mesh-ping failures. UI additions are syntax-checked and covered by marker tests, not re-checked in a browser.
