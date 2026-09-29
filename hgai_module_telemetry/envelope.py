"""The `hgai-envelope` wire format (plan §1, §3): one self-contained OTEL-
shaped JSON body — resource + scope + a batch of records — posted straight to
the exact configured `HGAI_TELEMETRY_ENDPOINT`.

`otlp-http-json` (standard OTLP/HTTP JSON, per-signal endpoint suffixes) is
Phase 6 and not implemented here — see hgai_module_telemetry.exporters.
"""

from typing import Any, Dict, List

from hgai.config import Settings

SERVICE_VERSION = "0.1.0"


def build_envelope(records: List[Dict[str, Any]], settings: Settings) -> Dict[str, Any]:
    return {
        "resource": {
            "service.name": "hgai",
            "service.version": SERVICE_VERSION,
            "service.instance.id": settings.server_id,
            "deployment.environment": settings.telemetry_environment,
            # A real per-deployment "how was this instance provisioned" flag
            # doesn't exist as a setting yet; this is a best-effort guess
            # (hosted iff the endpoint is HypergraphAI's own domain) rather
            # than a new config surface for a single cosmetic resource
            # attribute — revisit if a real need for it shows up downstream.
            "hgai.deployment.mode": (
                "hgai-hosted"
                if settings.telemetry_endpoint and "hypergra.ai" in settings.telemetry_endpoint
                else "self-hosted"
            ),
        },
        "scope": {"name": "hgai.telemetry", "version": "1"},
        "records": records,
    }
