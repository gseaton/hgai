"""HypergraphAI Telemetry module.

Phase 1 (foundation) of docs/architect/telemetry-20260929061557.md: emits
OTEL-shaped usage and error events for hot-spot, feature-usage, per-account
and error/bug-report analysis. Off by default — a self-hosted operator must
opt in (`HGAI_TELEMETRY_ENABLED=true`).

What Phase 1 ships:
  - A fire-and-forget `emit()` API (hgai_module_telemetry.engine) backed by a
    bounded in-memory queue and a background batching/export task, mirroring
    hgai_module_mesh/scheduler.py's shape.
  - `HTTPExporter`, posting the `hgai-envelope` wire format (see §1 of the
    plan) to a configurable `HGAI_TELEMETRY_ENDPOINT`.
  - REST instrumentation: one ASGI middleware records every request as a
    usage or error event (hgai_module_telemetry.middleware).
  - An admin-only status endpoint, `GET /api/v1/telemetry/status`.

Not yet implemented (later phases of the same plan): SHQL/MCP/Web-UI/shell
instrumentation (Phases 2-4), the `__local-telemetry` local-storage
destination (Phase 3a), the Help/settings-doc rollout (Phase 5), and the
`otlp-http-json` protocol (Phase 6).
"""

from .module import TelemetryModule

__all__ = ["TelemetryModule"]
