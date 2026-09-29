"""The OTEL-shaped event record (plan §3) — one dict per usage or error, the
shape every surface's emitter builds and every destination consumes.

Only the fields Phase 1 (REST instrumentation) needs are populated here;
later phases (SHQL, MCP, Web UI, shell) build the same shape from their own
call sites and pass it through the same `emit()`.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from hgai.config import Settings
from hgai.models.account import AccountInDB

from .identity import hash_id

VALID_KINDS = ("usage", "error")
VALID_OUTCOMES = ("ok", "error", "denied")


def account_field(account: Optional[AccountInDB], settings: Settings) -> Optional[Dict[str, Any]]:
    """The event's `account` field — None for an unauthenticated request.

    Never the username itself unless `telemetry_include_account_ids` opts in
    (plan §5.3); role and `is_agent` travel in the clear either way.
    """
    if account is None:
        return None
    identifier = account.username if settings.telemetry_include_account_ids else hash_id(account.username, settings)
    return {
        "id_hash": identifier,
        "roles": [str(r) for r in account.roles],
        "is_agent": "agent" in [str(r) for r in account.roles],
    }


def build_event(
    *,
    kind: str,
    surface: str,
    feature: str,
    duration_ms: float,
    outcome: str,
    account: Optional[Dict[str, Any]] = None,
    attributes: Optional[Dict[str, Any]] = None,
    error: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """One event record matching docs/architect/telemetry-*.md §3.

    `account` is the already-built dict from `account_field` (or None), not
    an `AccountInDB` — callers that already have one on hand pass it through
    rather than every emitter re-deriving it.
    """
    assert kind in VALID_KINDS, f"invalid event kind: {kind!r}"
    assert outcome in VALID_OUTCOMES, f"invalid event outcome: {outcome!r}"
    return {
        "kind": kind,
        "surface": surface,
        "feature": feature,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "duration_ms": round(duration_ms, 3),
        "outcome": outcome,
        "account": account,
        "attributes": attributes or {},
        "error": error,
    }
