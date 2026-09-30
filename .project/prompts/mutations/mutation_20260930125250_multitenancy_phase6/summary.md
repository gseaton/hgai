# Mutation Summary

## Intent
Implement Phase 6 (tests) of the multi-tenancy plan.

## Context
Phases 2 to 5 already added unit-level tenancy tests that call functions directly. The gap was real HTTP behavior and a guarantee that new routes cannot skip the tenant boundary.

## What Changed and Why
A new end-to-end suite drives the real app over HTTP and generates its cross-tenant checks from the route table. It found a real bug: GET /graphs reported `total` as the size of the filtered page for ordinary accounts because access filtering happened after paging. The access rule now runs in storage with the tenant filter.

## Key Decisions
- Checks are generated from the route table rather than hand-listed, so they scale with the API.
- The MCP endpoint over HTTP is not retested: its session manager can start once per process and is already used by tests/test_authz.py.
- Bare graph names in two tenants is not tested as isolation; ids are server-wide unique (Phase 3), so a test pins the 409.

## Verification
Full suite 1115 passed; 2 pre-existing mesh-ping failures.
