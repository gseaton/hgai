# Mutation Log

## Created
- **docs/architect/telemetry-20260929061557.md** — Implementation plan for OTEL-shaped usage/error telemetry across REST, SHQL, MCP, Web UI and the shell, with a configurable HTTP endpoint, event schema, privacy/data-minimization rules, settings, testing plan and phased rollout. No code changes.

## Modified (amendment)
- **docs/architect/telemetry-20260929061557.md** — Added local-storage destination throughout: architecture diagram and `select_exporter` destination logic (§2), a new §3a specifying the `__local-telemetry` hypergraph and its hypernode mapping (id/label = slug-timestamp, type = "OTEL", description = JSON message, attributes = full record) plus mesh/permission/listing isolation and retention, updated §5/§6/§8/§9/§10/§11 for the local path and new settings, renumbered nothing else (§3a inserted between §3 and §4).
