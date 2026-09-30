"""Telemetry REST API router: the admin-only status endpoint (Phase 1) and
the client-driven ingest endpoint (Phase 4, plan §4's Web UI / hgsh rows).
"""

import re
from typing import Any, Dict, Union

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field, field_validator

from hgai.api.deps import get_current_active_account
from hgai.config import get_settings
from hgai.core.auth import require_system_admin
from hgai.models.account import AccountInDB

from . import engine
from .events import account_field, build_event

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("/status")
async def telemetry_status(_: AccountInDB = Depends(require_system_admin)) -> Dict[str, Any]:
    """Whether telemetry is enabled, where it's going (host only — never the
    full URL, which may embed a bearer token), queue depth, drop/export
    counts, and the last export's outcome. Admin-only, so "is this thing
    sending data, and to where" is answerable without reading source or
    config files — without also being a way for a non-admin to probe
    deployment configuration."""
    return engine.status()


# ─── Ingest (client-driven usage events: Web UI, hgsh shell) ──────────────────
#
# Neither client runs in this process, so neither can call engine.emit()
# directly (the Web UI is the browser; hgsh is a separate CLI process talking
# over the same REST API — see shell/hgai_shell.py). Both post here instead,
# authenticated the same as any other route, and the server enqueues with the
# *verified* account from this request's own auth — never whatever the
# client claims — then returns immediately (plan §4: "the browser gets a 202
# immediately").
#
# `feature` is meant to stay a small, known set of action ids (the whole
# point of the field, plan §3), not client-supplied free text, so it's
# restricted to the same two dotted-token shape server-side features already
# use. `attributes` is restricted to a few primitive-valued keys so a client
# bug (or a malicious client) can't smuggle arbitrary data — note text, query
# content, anything else the plan's §5 hard privacy rule forbids — into
# telemetry through this one open door.

_ALLOWED_SURFACES = {"web-ui", "shell"}
_ALLOWED_OUTCOMES = {"ok", "error", "denied"}
_FEATURE_RE = re.compile(r"^[a-z][a-z0-9_-]*(\.[a-z0-9_-]+)+$")  # e.g. "ui.query.run", "shell.import-rdf"
_MAX_ATTRIBUTES = 8
_MAX_ATTRIBUTE_KEY_LEN = 40
_MAX_ATTRIBUTE_STR_LEN = 100

AttributeValue = Union[str, int, float, bool, None]


class IngestRequest(BaseModel):
    surface: str
    feature: str = Field(..., max_length=100)
    duration_ms: float = Field(default=0.0, ge=0)
    outcome: str = "ok"
    attributes: Dict[str, AttributeValue] = Field(default_factory=dict)

    @field_validator("surface")
    @classmethod
    def _valid_surface(cls, v: str) -> str:
        if v not in _ALLOWED_SURFACES:
            raise ValueError(f"surface must be one of {sorted(_ALLOWED_SURFACES)}")
        return v

    @field_validator("outcome")
    @classmethod
    def _valid_outcome(cls, v: str) -> str:
        if v not in _ALLOWED_OUTCOMES:
            raise ValueError(f"outcome must be one of {sorted(_ALLOWED_OUTCOMES)}")
        return v

    @field_validator("feature")
    @classmethod
    def _valid_feature(cls, v: str) -> str:
        if not _FEATURE_RE.match(v):
            raise ValueError("feature must look like 'ui.<screen>.<action>' or 'shell.<command>'")
        return v


def _sanitize_attributes(attributes: Dict[str, AttributeValue]) -> Dict[str, AttributeValue]:
    clean: Dict[str, AttributeValue] = {}
    for key, value in list(attributes.items())[:_MAX_ATTRIBUTES]:
        key = str(key)[:_MAX_ATTRIBUTE_KEY_LEN]
        if isinstance(value, str):
            value = value[:_MAX_ATTRIBUTE_STR_LEN]
        clean[key] = value
    return clean


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest(
    body: IngestRequest, account: AccountInDB = Depends(get_current_active_account),
) -> Dict[str, bool]:
    """Enqueue one client-reported usage event. Always 202 — a telemetry
    submission failing must never look like the client's real action (the
    render, the export, the shell command it's reporting on) failed; the
    only way this responds with an error is if `body` itself doesn't parse
    (FastAPI's own 422), which happens before any client code sees a result
    to react to."""
    try:
        settings = get_settings()
        engine.emit(build_event(
            kind="usage",
            surface=body.surface,
            feature=body.feature,
            duration_ms=body.duration_ms,
            outcome=body.outcome,
            account=account_field(account, settings),
            attributes=_sanitize_attributes(body.attributes),
        ))
    except Exception:
        pass
    return {"accepted": True}
