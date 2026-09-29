"""The `__local-telemetry` hypergraph (plan §3a): local storage destination
for telemetry, used whenever no external endpoint is configured or
`HGAI_TELEMETRY_LOCAL_ENABLED=true`.

Each OTEL event becomes one hypernode, written through the platform's own
`hgai.core.engine.create_hypernode` — the same path every other hypernode
goes through, so it gets the same audit trail and is queryable with SHQL
like any other data, no separate telemetry store required.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# No dot (hypergraph ids may not contain one — reserved for mesh dot-notation,
# hgai/models/hypergraph.py) and a leading `__` to read unambiguously as
# platform-internal, the same convention the Hypergraphs list UI (Phase 4)
# hides by default.
GRAPH_ID = "__local-telemetry"

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_MAX_SLUG_TOKENS = 4


# ── Graph lifecycle ────────────────────────────────────────────────────────────

async def ensure_graph() -> None:
    """Create `__local-telemetry` if it doesn't exist yet. Idempotent and
    safe under a create race (the loser's `create_hypergraph` call fails on
    the store's own unique index; the winner's graph is what's used either
    way) — the same lazy-create-on-first-use shape as `bootstrap_admin`."""
    from hgai.core.engine import create_hypergraph, get_hypergraph
    from hgai.models.hypergraph import HypergraphCreate

    if await get_hypergraph(GRAPH_ID, space_id=None) is not None:
        return
    try:
        await create_hypergraph(
            HypergraphCreate(id=GRAPH_ID, label="Local Telemetry", tags=["system", "telemetry"]),
            created_by="system",
        )
    except Exception:
        # Lost a create race, or a transient storage error — either way, a
        # concrete node-create call right after this is what actually
        # surfaces a real problem; ensure_graph() itself must never raise.
        logger.debug("ensure_graph(): create_hypergraph did not succeed (may already exist)", exc_info=True)


# ── Slug generation (plan §3a) ─────────────────────────────────────────────────

def _feature_tokens(feature: str) -> List[str]:
    """Meaningful lowercase tokens from a `feature` string.

    REST features are `"METHOD /api/v1/hyperedges/{id}"` — the method and
    versioned-API-prefix segments and any `{param}` placeholder carry no
    information worth putting in an id, so only the path's own segments
    survive (`/api/v1/hyperedges` -> `["hyperedges"]`). A dotted feature
    (`"shql.query"`, `"ui.visualize.focus_dblclick"`) has no such prefix
    noise, so every dot-separated part becomes its own token.
    """
    text = feature
    method, sep, rest = feature.partition(" ")
    if sep and method.isupper():
        text = rest
    if "/" in text:
        segments = [s for s in text.split("/") if s and not s.startswith("{")]
        segments = [s for s in segments if s not in ("api", "v1")]
        return [t for s in segments for t in _TOKEN_RE.findall(s.lower())]
    return [t for s in text.split(".") for t in _TOKEN_RE.findall(s.lower())]


def _timestamp_suffix(iso_timestamp: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y%m%d%H%M%S")


def build_slug(record: Dict[str, Any]) -> str:
    """`<3-4-word-slug>-<yyyymmddhhmmss>` (plan §3a). Deterministic and
    collision-free by construction (the timestamp suffix), so callers never
    need a uniqueness check before inserting.
    """
    tokens: List[str] = []
    if record.get("surface"):
        tokens.append(record["surface"])
    tokens += _feature_tokens(record.get("feature") or "")
    outcome = record.get("outcome")
    if outcome and outcome != "ok":
        tokens.append(outcome)
    error = record.get("error") or {}
    if error.get("type"):
        tokens.append(error["type"])

    deduped: List[str] = []
    for t in tokens:
        t = t.lower()
        if t and (not deduped or deduped[-1] != t):
            deduped.append(t)
    deduped = deduped[:_MAX_SLUG_TOKENS]
    if not deduped:
        deduped = [record.get("kind") or "event", record.get("surface") or "x"]

    return f"{'-'.join(deduped)}-{_timestamp_suffix(record.get('timestamp') or '')}"


# ── Writing records ───────────────────────────────────────────────────────────

async def _create_with_retry(data: Any) -> None:
    """`create_hypernode`, retried once with a short disambiguating suffix
    on the id if the first attempt fails.

    The slug is second-precision (plan §3a), so two events with the same
    surface/feature/outcome/error.type in the same second — realistic at
    any real traffic volume, not just a theoretical edge case — produce the
    *same* slug and collide on the store's own uniqueness constraint. Rather
    than a pre-write existence check (defeating the plan's "collision-free
    by construction, no uniqueness check needed" point in the common case),
    this stays optimistic: one insert, and only on failure — whatever the
    cause, deliberately not inspected, since a specific storage backend's
    exception type is exactly what this module must not need to know about
    — a retry with a variant id. A second failure is a real problem and
    propagates (the `Exporter.export` contract: raise, let the caller's own
    retry/backoff apply).
    """
    from hgai.core.engine import create_hypernode

    try:
        await create_hypernode(GRAPH_ID, data, created_by="system", space_id=None)
    except Exception:
        import secrets
        suffix = secrets.token_hex(2)
        disambiguated = data.model_copy(update={"id": f"{data.id}-{suffix}", "label": f"{data.label}-{suffix}"})
        await create_hypernode(GRAPH_ID, disambiguated, created_by="system", space_id=None)


async def write_records(records: List[Dict[str, Any]]) -> None:
    """Write a batch of OTEL records as hypernodes in `__local-telemetry`.
    Raises on failure (same `Exporter.export` contract as `HTTPExporter`) so
    the caller's batching/retry logic applies uniformly across destinations.
    """
    from hgai.models.hypernode import HypernodeCreate

    await ensure_graph()
    for record in records:
        slug = build_slug(record)
        await _create_with_retry(HypernodeCreate(
            id=slug, label=slug, type="OTEL",
            description=json.dumps(record, indent=2, default=str),
            attributes=record,
            tags=["telemetry", record.get("kind") or "usage"],
            valid_from=record.get("timestamp"),
        ))


# ── Retention ──────────────────────────────────────────────────────────────────

_PRUNE_BATCH_SIZE = 500


async def prune_older_than(cutoff: datetime) -> int:
    """Delete `__local-telemetry` hypernodes with `valid_from` before
    `cutoff`. Returns the number deleted.

    Repeatedly re-queries the same server-side-filtered page (always
    `skip=0`) rather than paging through the whole collection once: each
    delete shrinks what still matches, so this converges correctly and
    without unbounded memory regardless of collection size, unlike filtering
    client-side over an arbitrary `search()` page (which could always land
    on "still fresh" rows in a large collection and prune nothing).

    `cutoff` is required and must not be `None` — that would build a filter
    with no date bound at all and delete *everything* in the graph, active
    or not. `retention_cutoff()` returning `None` means "pruning is
    disabled"; callers must check that themselves rather than pass it
    straight through (`_retention_loop` does this correctly — this assert
    is a guard against a future caller getting it wrong, not a real path).
    """
    assert cutoff is not None, "prune_older_than() requires an explicit cutoff; None would delete everything"

    from hgai.core.engine import delete_hypernode
    from hgai.db.storage import get_storage
    from hgai_module_storage.filters import HypernodeSearchFilters

    filters = HypernodeSearchFilters(hypergraph_ids=[GRAPH_ID], status="active", valid_from_before=cutoff)
    deleted = 0
    while True:
        batch = await get_storage().hypernodes.search(filters, skip=0, limit=_PRUNE_BATCH_SIZE)
        if not batch:
            return deleted
        progressed = False
        for doc in batch:
            if await delete_hypernode(GRAPH_ID, doc["id"], space_id=None):
                deleted += 1
                progressed = True
        if not progressed:
            # Every doc in this still-matching batch failed to delete (should
            # not happen — this runs with full storage access, not through
            # REST auth) — bail out rather than spin forever re-querying the
            # same undeletable rows.
            logger.warning(
                f"Telemetry retention sweep: {len(batch)} matching hypernode(s) in "
                f"{GRAPH_ID!r} could not be deleted; stopping this pass."
            )
            return deleted


def retention_cutoff(retention_days: int) -> Optional[datetime]:
    """None means "pruning disabled" (plan §3a: `0` keeps everything)."""
    if retention_days <= 0:
        return None
    return datetime.now(timezone.utc) - timedelta(days=retention_days)


# ── Background sweep task ───────────────────────────────────────────────────────
#
# Same lifespan-managed-background-task shape as hgai_module_mesh/scheduler.py
# (start_scheduler/stop_scheduler wired into hgai/main.py's lifespan) and the
# same grace-period-GC idea as hgai/core/media.py::sweep_orphaned_media. Runs
# whenever telemetry is enabled and retention is not disabled, independent of
# whether local storage is actually the active export destination right now —
# a no-op sweep against a not-yet-created `__local-telemetry` is harmless and
# cheap (a handful of database round-trips once an hour), and it means
# switching HGAI_TELEMETRY_LOCAL_ENABLED on later doesn't also require
# restarting to pick up retention.

_RETENTION_INTERVAL_SECONDS = 3600
_retention_task: Optional[asyncio.Task] = None


async def _retention_loop(retention_days: int) -> None:
    logger.info(f"Telemetry retention sweep started (retention: {retention_days} day(s))")
    while True:
        await asyncio.sleep(_RETENTION_INTERVAL_SECONDS)
        try:
            cutoff = retention_cutoff(retention_days)
            if cutoff is not None:
                deleted = await prune_older_than(cutoff)
                if deleted:
                    logger.info(f"Telemetry retention sweep: pruned {deleted} hypernode(s) from {GRAPH_ID!r}")
        except Exception:
            logger.warning("Telemetry retention sweep iteration failed", exc_info=True)


def start_retention_scheduler(settings: Any) -> None:
    """No-op unless telemetry is enabled and retention is not disabled
    (`HGAI_TELEMETRY_LOCAL_RETENTION_DAYS=0` keeps everything, an explicit
    operator choice — see `retention_cutoff`)."""
    global _retention_task
    if not settings.telemetry_enabled or settings.telemetry_local_retention_days <= 0:
        return
    _retention_task = asyncio.create_task(_retention_loop(settings.telemetry_local_retention_days))
    logger.info("Telemetry retention background task created")


def stop_retention_scheduler() -> None:
    global _retention_task
    if _retention_task and not _retention_task.done():
        _retention_task.cancel()
    _retention_task = None
