# Mutation Summary

## Intent
Show which tenant owns each graph to a system admin, sortable, without cluttering the view when it adds nothing.

## What Changed and Why
The column appears only for a system admin, with tenancy on, not scoped to a tenant in the top-bar picker, and when the server has more than one tenant. Every other account is locked to its own tenant, so it never sees it. The backend needed only to allow sorting by tenant_id. If the column becomes hidden while it is the active sort, the sort is dropped so the list does not stay ordered by something invisible.

## Key Decisions
- "Locked to one tenant" is read as: a tenant-bound account, a system admin scoped to one tenant, or a server with one tenant.
- Also fixed test hermeticity: the developer's .env now turns tenancy and telemetry on, which made 70 tests fail; the suite now pins those settings.

## Verification
Browser, live server: column shown for an unscoped system admin with correct values; clicking the header sorted ascending then descending; scoping to one tenant hid it and cleared the sort; a tenant admin never saw it; no console errors. Full suite 1148 passed; 2 pre-existing mesh-ping failures.
