# Mutation Summary

## Intent
Identify who performed each telemetry event with a top-level `actor` field, `__system` when no account acted.

## Context
All emitters (REST, SHQL, MCP, errors, ingest) build records via `build_event` with an `account` dict from `account_field` (None when no account).

## What Changed and Why
`build_event` now derives `actor` from the account dict's `id_hash`, or `__system` if None. One central change covers every surface.

## Key Decisions
- `actor` reuses `id_hash`, so it is hashed unless `HGAI_TELEMETRY_INCLUDE_ACCOUNT_IDS=true`, preserving the privacy default.
- Unauthenticated requests also have no account, so they report `__system`; no separate anonymous value was introduced.

## Verification
Full suite: 1001 passed; 2 pre-existing mesh-ping failures unrelated.
