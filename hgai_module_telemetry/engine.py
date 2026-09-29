"""The telemetry queue, `emit()` API, and background export loop.

Mirrors hgai_module_mesh/scheduler.py's shape (`start_scheduler`/
`stop_scheduler` wired into hgai/main.py's lifespan) and
hgai_module_storage's pluggable-backend habit (`select_exporter`, see
exporters.py) — see docs/architect/telemetry-20260929061557.md §2.

Module-level state (not a class) matches this codebase's existing singleton
patterns for one-per-process resources (hgai_module_mesh/engine.py's shared
HTTP client, hgai_module_mesh/scheduler.py's `_sync_task`).
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional

from hgai.config import Settings

from .exporters import Exporter, NullExporter, select_exporter

logger = logging.getLogger(__name__)

_queue: Optional[asyncio.Queue] = None
_exporter: Exporter = NullExporter()
_settings: Optional[Settings] = None
_task: Optional[asyncio.Task] = None

# Visible on GET /api/v1/telemetry/status (plan §5.4) — a kill switch is only
# a kill switch if "is this thing sending data" is answerable without reading
# source or config files.
_stats: Dict[str, Any] = {
    "dropped_queue_full": 0,
    "batches_sent": 0,
    "batches_failed": 0,
    "records_sent": 0,
    "last_export_at": None,
    "last_export_outcome": None,
}

_MAX_EXPORT_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 1.0


def emit(record: Dict[str, Any]) -> None:
    """Enqueue one event record (events.build_event's shape). Fire-and-forget:
    never awaited, never raises, returns in well under a millisecond.

    A no-op whenever telemetry isn't running — `_queue` is only set by
    `start_scheduler` when `settings.telemetry_enabled` is true, so a caller
    never needs its own enabled-check before calling this.
    """
    if _queue is None:
        return
    try:
        if _settings is not None and _settings.telemetry_sample_rate < 1.0 and record.get("kind") == "usage":
            # Errors are never sampled (plan §5/§7) — only "usage" events are
            # thinned, and only probabilistically, so this stays O(1) and
            # allocation-free on the common (kept) path.
            if random.random() >= _settings.telemetry_sample_rate:
                return
        try:
            _queue.put_nowait(record)
        except asyncio.QueueFull:
            # Bounded queue, oldest-drop (plan §2/§5.4): never grow without
            # bound, and never block the caller waiting for room.
            try:
                _queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            else:
                _stats["dropped_queue_full"] += 1
            try:
                _queue.put_nowait(record)
            except asyncio.QueueFull:
                pass
    except Exception:
        # Telemetry must never be the reason a request fails (plan §2).
        logger.debug("telemetry emit() failed", exc_info=True)


def _destination_name(exp: Exporter) -> str:
    from .exporters import CompositeExporter
    if isinstance(exp, CompositeExporter):
        return "+".join(type(e).__name__ for e in exp._exporters)
    return type(exp).__name__


def status() -> Dict[str, Any]:
    """Snapshot for GET /api/v1/telemetry/status."""
    return {
        "enabled": _settings.telemetry_enabled if _settings else False,
        "destination": _destination_name(_exporter),
        "endpoint_host": _endpoint_host(),
        "protocol": _settings.telemetry_protocol if _settings else None,
        "queue_depth": _queue.qsize() if _queue is not None else 0,
        "queue_max_size": _settings.telemetry_queue_max_size if _settings else None,
        **_stats,
    }


def _endpoint_host() -> Optional[str]:
    """Host only, never the full URL — an embedded telemetry API key must
    never be a query parameter (plan §5.5), but even a bare URL with no
    token is unnecessary to expose on an otherwise-unauthenticated-adjacent
    status surface; the host alone answers "where is this going" for an
    admin without republishing the full configured value."""
    if not _settings or not _settings.telemetry_endpoint:
        return None
    from urllib.parse import urlparse
    return urlparse(_settings.telemetry_endpoint).hostname


async def _export_batch(records: List[Dict[str, Any]]) -> None:
    """Export one batch with capped exponential backoff; drop (not requeue)
    on final failure so a persistently-unreachable endpoint can never grow
    the queue without bound (plan §2)."""
    for attempt in range(_MAX_EXPORT_ATTEMPTS):
        try:
            await _exporter.export(records)
            _stats["batches_sent"] += 1
            _stats["records_sent"] += len(records)
            _stats["last_export_at"] = time.time()
            _stats["last_export_outcome"] = "ok"
            return
        except Exception as e:
            if attempt + 1 == _MAX_EXPORT_ATTEMPTS:
                _stats["batches_failed"] += 1
                _stats["last_export_at"] = time.time()
                _stats["last_export_outcome"] = f"{type(e).__name__}: {e}"
                logger.warning(f"Telemetry export failed after {_MAX_EXPORT_ATTEMPTS} attempts, dropping batch of {len(records)}: {e}")
                return
            await asyncio.sleep(_BACKOFF_BASE_SECONDS * (2 ** attempt))


async def _export_loop(settings: Settings) -> None:
    """Drains `_queue`, batching by size or by flush interval, whichever
    comes first — same batching shape as hgai_module_mesh/scheduler.py's
    interval loop, but event-driven (via Queue.get) rather than a fixed
    sleep, so a full batch ships immediately instead of waiting out the rest
    of the interval."""
    logger.info(f"Telemetry export loop started (destination: {type(_exporter).__name__})")
    loop = asyncio.get_event_loop()
    try:
        while True:
            batch: List[Dict[str, Any]] = []
            deadline = loop.time() + settings.telemetry_flush_interval_seconds
            while len(batch) < settings.telemetry_batch_size:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    break
                try:
                    batch.append(await asyncio.wait_for(_queue.get(), timeout=remaining))
                except asyncio.TimeoutError:
                    break
            if batch:
                try:
                    await _export_batch(batch)
                except Exception:
                    logger.warning("Telemetry export loop iteration failed", exc_info=True)
    except asyncio.CancelledError:
        pass


def start_scheduler(settings: Settings) -> None:
    """Start the background export task. No-op if telemetry is disabled —
    `_queue` stays None, so `emit()` is a guaranteed no-op too."""
    global _queue, _exporter, _settings, _task
    _settings = settings
    if not settings.telemetry_enabled:
        return
    _queue = asyncio.Queue(maxsize=settings.telemetry_queue_max_size)
    _exporter = select_exporter(settings)
    _task = asyncio.create_task(_export_loop(settings))
    logger.info("Telemetry background export task created")


def stop_scheduler() -> None:
    global _task, _queue
    if _task and not _task.done():
        _task.cancel()
    _task = None
    _queue = None
