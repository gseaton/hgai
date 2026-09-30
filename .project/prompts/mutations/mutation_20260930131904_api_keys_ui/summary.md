# Mutation Summary

## Intent
Close the two gaps left after Phase 7: browser-verify the System role select and quota fields, and add the missing Web UI screen for tenant API keys.

## What Changed and Why
A new API Keys screen and modal. The secret is shown once and cleared when the dialog closes. System admins choose the tenant; tenant admins' keys use their own and the selector is hidden. The previously unverified UI was exercised in a real browser against a live server with tenancy on.

## Key Decisions
- The screen is visible to tenant admins (data-tenant-admin) since they can manage their own tenant's keys.
- Revoke reuses the app's confirm dialog rather than a native one.

## Verification
Browser, live server: tenant editor saved and reloaded quotas; System role select created a system_auditor account; API Keys screen created a key (secret shown once, cleared on close), listed it, the key authenticated and stamped its tenant on a graph it created, and revoke made it return 401; a tenant admin saw no tenant selector and got an own-tenant key. Full suite 1146 passed; 2 pre-existing mesh-ping failures.
