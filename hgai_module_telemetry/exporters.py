"""Pluggable telemetry destinations (plan §2), mirroring
hgai_module_storage.backend's pluggable-backend pattern.

`NullExporter` and `HTTPExporter` (`hgai-envelope` protocol only —
`otlp-http-json` falls back to it with a warning; see the plan's §1 and
Phase 6) shipped in Phase 1. `LocalHypergraphExporter` (plan §3a — writes
into the `__local-telemetry` hypergraph) and `CompositeExporter` (fans a
batch out to more than one destination) are Phase 3a.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from hgai.config import Settings

from .envelope import build_envelope

logger = logging.getLogger(__name__)

_HTTP_TIMEOUT = 10.0

# One AsyncClient reused across every export call, same shared-client shape
# as hgai_module_mesh/engine.py's get_http_client/close_http_client.
_http_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=_HTTP_TIMEOUT)
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
    _http_client = None


class Exporter(ABC):
    """One telemetry destination. `export` raises on failure — the caller
    (hgai_module_telemetry.engine's export loop) owns retry/backoff and
    must never let a destination failure propagate into the request path
    that called `emit()`."""

    @abstractmethod
    async def export(self, records: List[Dict[str, Any]]) -> None:
        """Ship a batch of event records (plan §3). Raise on failure."""


class NullExporter(Exporter):
    """Discards every batch. Used both when telemetry is disabled outright
    (in which case the background task never even starts — this is only
    reachable defensively) and, in Phase 1, when telemetry is enabled but
    no destination is configured yet (see `select_exporter`)."""

    async def export(self, records: List[Dict[str, Any]]) -> None:
        return


class HTTPExporter(Exporter):
    """Posts the `hgai-envelope` wire format to `settings.telemetry_endpoint`."""

    def __init__(self, settings: Settings):
        self._settings = settings
        if settings.telemetry_protocol != "hgai-envelope":
            # otlp-http-json is Phase 6; warn once at construction (start-up
            # time), not per export, and proceed with the implemented protocol.
            logger.warning(
                f"HGAI_TELEMETRY_PROTOCOL={settings.telemetry_protocol!r} is not yet implemented "
                "(planned for a later phase) — using 'hgai-envelope' instead."
            )

    async def export(self, records: List[Dict[str, Any]]) -> None:
        settings = self._settings
        headers = {"Content-Type": "application/json"}
        if settings.telemetry_api_key:
            headers["Authorization"] = f"Bearer {settings.telemetry_api_key}"
        body = build_envelope(records, settings)
        response = await get_http_client().post(settings.telemetry_endpoint, json=body, headers=headers)
        response.raise_for_status()


class LocalHypergraphExporter(Exporter):
    """Writes into the `__local-telemetry` hypergraph via the platform's own
    storage layer (plan §3a) — no network involved at all."""

    async def export(self, records: List[Dict[str, Any]]) -> None:
        from . import local_storage
        await local_storage.write_records(records)


class CompositeExporter(Exporter):
    """Fans a batch out to every given exporter independently — a
    local-storage failure and an HTTP-export failure must never block or
    duplicate-retry each other (plan §2). Raises only if *every* destination
    failed, so the engine's outer retry/backoff (`engine._export_batch`)
    fires only when the batch made it nowhere at all; a batch that reached
    at least one destination is not retried, which would otherwise
    duplicate-write the destination(s) that already succeeded.
    """

    def __init__(self, exporters: List[Exporter]):
        self._exporters = exporters

    async def export(self, records: List[Dict[str, Any]]) -> None:
        failures = []
        for exp in self._exporters:
            try:
                await exp.export(records)
            except Exception as e:
                failures.append((type(exp).__name__, e))
        if failures and len(failures) == len(self._exporters):
            detail = "; ".join(f"{name}: {e}" for name, e in failures)
            raise RuntimeError(f"every telemetry destination failed: {detail}")
        for name, e in failures:
            logger.warning(f"Telemetry destination {name} failed (other destination(s) still succeeded): {e}")


def select_exporter(settings: Settings) -> Exporter:
    """The exporter(s) to use for the lifetime of this process (plan §2).

    Local storage is used whenever no external endpoint is configured (an
    insecure, refused endpoint counts as "no endpoint" here — see below) so
    enabling telemetry always does something useful, and additionally
    whenever `HGAI_TELEMETRY_LOCAL_ENABLED=true` even with a working
    endpoint, so both destinations can run at once.
    """
    endpoint = settings.telemetry_endpoint
    if endpoint and not endpoint.startswith("https://") and not settings.telemetry_allow_insecure:
        logger.warning(
            f"HGAI_TELEMETRY_ENDPOINT={endpoint!r} is not https:// and HGAI_TELEMETRY_ALLOW_INSECURE "
            "is not set — treating this as no endpoint configured."
        )
        endpoint = None

    exporters: List[Exporter] = []
    if endpoint:
        exporters.append(HTTPExporter(settings))
    if not endpoint or settings.telemetry_local_enabled:
        exporters.append(LocalHypergraphExporter())

    if not exporters:
        return NullExporter()
    return exporters[0] if len(exporters) == 1 else CompositeExporter(exporters)
