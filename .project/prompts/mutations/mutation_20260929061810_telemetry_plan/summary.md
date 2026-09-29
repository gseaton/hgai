# Mutation Summary

## Intent
Produce a grounded implementation plan for OpenTelemetry-shaped usage and error telemetry, to later support analysis of hot spots, most/least-used features, per-account usage and bug reports, with a configurable POST endpoint as in the request's example URL.

## Context
Read hgai/main.py (module mounting, lifespan), hgai_module_mesh/scheduler.py (background-task pattern to reuse), hgai_module_storage/backend.py (pluggable-backend pattern to reuse for an Exporter), hgai/core/auth.py and hgai/models/account.py (account/role model), hgai_module_mcp/server.py (30 MCP tools, no central call hook — FastMCP inspected to confirm), hgai_module_agentchat/crypto.py (existing Fernet-encryption-at-rest precedent), hgai/config.py and .env.example (settings convention), and the marketing docs (regulated/self-hosted market positioning that shapes the privacy defaults).

## What Changed and Why
The plan proposes a new optional module, hgai_module_telemetry, mirroring existing module conventions: fire-and-forget emit() into a bounded queue, a background exporter task modeled on the mesh sync scheduler, and a pluggable Exporter interface (Null vs HTTP) modeled on the storage backend abstraction. It resolves a real ambiguity in the request — OTLP's protocol requires per-signal endpoint suffixes (/v1/traces, /v1/logs), but the example URL is a single path — by defining two protocols: a default "hgai-envelope" that posts one OTEL-shaped JSON body to the exact configured URL (matching the request literally), and an additive "otlp-http-json" option for customers with real OTEL collectors. It instruments REST via one new middleware, SHQL via its existing execute_shql chokepoint (reusing meta.truncated/aggregate_pushdown/paging_pushdown from this session's earlier aggregation work), MCP via a decorator over the 30 tools, and the Web UI by relaying through the server (never posting to the external endpoint directly from the browser). Telemetry defaults to off and hashes account/graph/space ids by default, argued from the product's own stated regulated/self-hosted markets.

## Key Decisions
- Off by default, HTTPS-only, hashed identifiers by default — privacy defaults argued directly from this repo's own marketing docs (defense/financial-crime/healthcare verticals, "data stays in the customer's store" positioning).
- No content (query text, entity/note/chat data) leaves the process in any mode — a hard rule, not a configurable redaction filter.
- Browser posts to a server-side relay route, not directly to the external endpoint — avoids exposing a telemetry API key to the browser and avoids trusting client-claimed identity.
- Error fingerprinting uses a message *template*, not the raw message, so errors carrying customer data (e.g. a graph id) don't fragment into unique fingerprints per customer.
- Left open for the product owner: whether hosted-vs-self-hosted enables telemetry by default, whether a receiving service exists yet, per-account opt-out, and retention of hashed ids downstream.

## Amendment: local storage destination
### Intent
Add a local, endpoint-free fallback: store telemetry as hypernodes in a dedicated `__local-telemetry` hypergraph when no external endpoint is configured, or whenever explicitly enabled alongside one.

### Context
Checked hgai/models/hypergraph.py (id validator forbids dots, not underscores — `__local-telemetry` is a valid id), hgai/models/hypernode.py and hgai/core/engine.py (create_hypernode's exact field set and side effects: mutations, increment_counts, cache invalidation), hgai/core/auth.py::filter_accessible_graphs (confirms an unowned graph is invisible to non-admins by default with no new access-control code needed), hgai_module_mesh/engine.py::_local_graph_ids (the federation fan-out enumeration that would otherwise leak this graph to mesh peers), and hgai/core/media.py::sweep_orphaned_media / hgai_module_storage/backend.py (the existing grace-period GC precedent reused for retention).

### What changed and why
Added a pluggable `LocalHypergraphExporter` alongside the existing Null/HTTP exporters, selected by new logic: local storage is used whenever no endpoint is configured (so enabling telemetry is never a no-op for lack of a URL) and/or whenever `HGAI_TELEMETRY_LOCAL_ENABLED=true` even with an endpoint set (both can run together via the existing `CompositeExporter` idea). Each OTEL record becomes one hypernode via the platform's own `create_hypernode`, with `type: "OTEL"`, `id`/`label` a deterministic 4-token slug plus a UTC timestamp, `description` the JSON-dumped record, and `attributes` the structured record itself (making it directly aggregatable with SHQL's existing `aggregate:` pushdown). Flagged two required safety properties, not just designed but called out as must-check at implementation time: exclusion from mesh federation's "all local graphs" fan-out (a real cross-tenant leak path if missed) and confirmation that the existing unowned-graph permission model already keeps it admin-only with zero new access-control code. Added a retention sweep (new setting, new small storage method) since per-event hypernodes are otherwise unbounded growth, unlike the external-endpoint path.

### Key decisions
- Local storage composes with, rather than replaces, the external endpoint (both can be active); the master `HGAI_TELEMETRY_ENABLED` switch still gates everything, so this doesn't relax the existing opt-in-by-default privacy posture on its own.
- Surfaced, but did not unilaterally adopt, the observation that local-only telemetry is inherently more private than any external destination (data never leaves the deployment's own database) and could arguably be a friendlier default — added as a new open question for the product owner rather than changing the previously-agreed default.
- Reused existing conventions throughout rather than inventing new ones: `created_by="system"` (already used by inference materialization and agent-chat catalog seeding), the unowned-graph + permissions model (already used by every other admin-only graph), and the media GC sweep's grace-period pattern (for retention).
