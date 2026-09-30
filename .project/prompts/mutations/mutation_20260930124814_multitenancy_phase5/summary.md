# Mutation Summary

## Intent
Implement Phase 5 (UI, shell, telemetry, docs) of the multi-tenancy plan.

## What Changed and Why
/auth/me now tells clients about tenancy, so the UI shows tenancy controls only when the server enforces it. Web UI: Tenants screen, tenant picker, tenant name, tenant-aware account editor, and a restricted admin view for tenant admins. Shell: tenant commands and a tenant scope. Telemetry events gain a hashed tenant. Documentation added across README, API reference and Help.

## Key Decisions
- UI reads tenancy state from /auth/me at session start; if it fails, tenancy UI stays hidden.
- Tenant admin sees only Spaces and Accounts (data-tenant-admin markers); all other admin areas stay system-admin only.
- Tenant in telemetry is hashed with the account-id setting rather than adding a new flag.
- `use graph <id>` added so a graph named "tenant" stays reachable.

## Verification
Full suite 1101 passed; 2 pre-existing mesh-ping failures. UI checked manually in Chrome against a live server (tenancy on) as system admin, tenant admin and user; no console errors.
