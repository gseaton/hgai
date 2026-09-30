# Response Summary

## Question / Intent
How a system admin creates and manages tenants.

## Answer / Recommendation
Enable HGAI_MULTITENANCY_ENABLED, then use the Tenants screen (create, edit label/quotas/status, suspend, delete an empty tenant, top-bar tenant picker), the Accounts screen (Tenant field, tenant_admin role), the API Keys screen, the REST routes (POST/PUT/DELETE /tenants, /tenants/{id}/usage, accounts with tenant_id), or hgsh (create/ls/update/delete tenant, use tenant, ls usage).

## Key Points
- Startup creates the default tenant and migrates existing records; old admin accounts become system admins.
- Another tenant's resources are 404, never 403; usernames, space ids and graph ids are unique server-wide (409 on clash), so use a tenant prefix.
- Moving an account drops its space memberships; its notes, media and saved queries stay behind.
- system_auditor is read-only across tenants.

## Context
Drawn from the implemented multi-tenancy phases 1 to 7 and the Tenants help topic.
