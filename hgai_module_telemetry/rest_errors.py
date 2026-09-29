"""REST error reporting (plan §7): called from the two FastAPI exception
handlers registered in hgai/main.py — kept out of main.py itself so the app
assembly file stays thin, matching the rest of this codebase's style.
"""

import time
from typing import Any, Dict, Optional

from starlette.requests import Request

from hgai.config import get_settings
from hgai.models.account import AccountInDB

from . import engine
from .errors import build_error_event
from .events import account_field
from .routing import request_start, route_template

# A 401 (no/invalid credentials) is routine, high-volume traffic — an
# expired token, a not-yet-logged-in browser tab — not a bug to triage. The
# plan's own worked fingerprinting example is a 404 (plan §7), which this
# does report; 401 is the one deliberate carve-out, made so genuine bugs
# aren't buried under authentication noise. The REST middleware's ordinary
# "usage" event (outcome: "denied") still records every 401.
_SKIP_HTTP_STATUS = {401}


def report(request: Request, exc: BaseException, http_status: int) -> None:
    """Emit a `kind: "error"` event for a REST-layer exception. Never
    raises — called from an exception handler, where a telemetry bug must
    never replace the real error response."""
    if http_status in _SKIP_HTTP_STATUS:
        return
    try:
        settings = get_settings()
        scope: Dict[str, Any] = request.scope
        account: Optional[AccountInDB] = (scope.get("state") or {}).get("account")
        start = request_start(scope)
        duration_ms = (time.perf_counter() - start) * 1000 if start is not None else 0.0
        outcome = "denied" if http_status == 403 else "error"
        template = route_template(scope)
        engine.emit(build_error_event(
            exc,
            surface="rest",
            surface_context="rest.exception_handler",
            feature=f"{scope.get('method')} {template}",
            duration_ms=duration_ms,
            outcome=outcome,
            account=account_field(account, settings),
            http_status=http_status,
        ))
    except Exception:
        pass
