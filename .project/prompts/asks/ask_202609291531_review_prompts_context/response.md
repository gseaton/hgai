# Response Summary

## Question / Intent
Get up to speed on the most recent project work by reviewing `.project/prompts`.

## Answer / Recommendation
Most recent work (2026-09-29) is the telemetry feature, delivered as a plan plus phases 1-5 and a README/Help docs pass (mutations `telemetry_plan`, `phase1`-`phase5`, `phase3a`, `readme_help_docs`). Before that, asks covered storage aggregation, SHQL candidate limits, and SPARQL-to-SHQL planning.

## Key Points
- Plan: docs/architect/telemetry-20260929061557.md; new optional module `hgai_module_telemetry`, off by default, hashed ids, no content leaves the process, pluggable exporters (Null/HTTP/local hypergraph `__local-telemetry`).
- Phase 3a added local storage with mesh-federation exclusion and retention sweep.
- Phase 5 added the admin/telemetry.md help topic; the later docs pass added the README section and Help home/glossary/FAQ entries.
- Last recorded test run: 1001 passed, 2 pre-existing unrelated mesh-ping failures deselected.
- Open product questions from the plan: default-on for hosted vs self-hosted, receiving service, per-account opt-out, downstream retention of hashed ids.
- README's MCP module description still says "14 tools" (actual 30); noted, not fixed.

## Context
Working tree has uncommitted telemetry changes on main. The hgai MCP server failed to connect (ECONNREFUSED) this session.
