# Mutation Summary

## Intent
Implement Phase 3 (API and resource scoping) of the multi-tenancy plan.

## What Changed and Why
Tenant routes; tenant-admin delegation on accounts; tenant-filtered lists (graphs filtered in storage so paging is right) and boundary checks for spaces, notes, media and saved queries; same-tenant-only space membership and note sharing; MCP parity for spaces and media.

## Key Decisions
- Unowned graph ids stay globally unique: nodes/edges are keyed by graph ref, so per-tenant ids would share data. Deviation from plan, recorded in the plan doc; it means a 409 on create can reveal an id exists in another tenant.
- Media dedup is per tenant; mesh-proxied media is refused to tenant accounts.
- Owner-only per-account data (SHQL history, chat) needed no enforcement beyond stamping.
- Fixed a pre-existing bug: PUT /accounts always failed (version set and $inc conflict).

## Verification
Full suite: 1060 passed; 2 pre-existing mesh-ping failures unrelated.
