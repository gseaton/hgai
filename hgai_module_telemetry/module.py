"""Telemetry module descriptor for HypergraphAI."""


class TelemetryModule:
    """Telemetry module.

    Phase 1 of docs/architect/telemetry-20260929061557.md: OTEL-shaped usage
    and error telemetry, off by default, exported to a configurable HTTP
    endpoint. Exposes one admin-only status endpoint at
    /api/v1/telemetry/status; the REST instrumentation itself is an ASGI
    middleware (see hgai_module_telemetry.middleware), mounted directly on
    the app rather than through this router.
    """

    name = "telemetry"
    version = "0.1.0"
    description = (
        "Telemetry — OTEL-shaped usage and error events, off by default, "
        "exported to a configurable endpoint or (a later phase) stored locally"
    )

    def get_router(self):
        from .api_router import router
        return router
