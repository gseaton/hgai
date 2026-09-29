"""REST instrumentation (plan §4's REST row): one ASGI middleware records a
usage event for every request, without touching any route handler.

A pure ASGI middleware class (not Starlette's `BaseHTTPMiddleware`, which
buffers the whole response body to let a handler read/replace it — overhead
and a streaming-response footgun this doesn't need) wrapping `send` just to
observe the status code that went out.
"""

import time
from typing import Any, Dict, Optional

from hgai.config import get_settings
from hgai.models.account import AccountInDB

from . import engine
from .events import account_field, build_event
from .routing import route_template

# Static assets, API docs, and the MCP sub-app (its own protocol, and its own
# Phase 3 tool-level instrumentation — see the plan's §4 MCP row) aren't
# "features" in the product-usage sense this middleware exists to measure.
_SKIP_PREFIXES = ("/ui", "/mcp", "/api/docs", "/api/redoc", "/api/openapi.json")


class TelemetryMiddleware:
    def __init__(self, app):
        self._app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"].startswith(_SKIP_PREFIXES):
            await self._app(scope, receive, send)
            return

        status_code = 500  # overwritten by wrapped_send; stays 500 only if the app raised past us
        start = time.perf_counter()
        # Stashed on the ASGI scope (plan §7) so a FastAPI exception handler
        # — which runs deeper in the stack, with no timer of its own — can
        # report a real `duration_ms` on the paired `kind: "error"` event
        # instead of 0. See hgai/main.py's exception handlers.
        scope.setdefault("state", {})["telemetry_start"] = start

        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                nonlocal status_code
                status_code = message["status"]
            await send(message)

        try:
            await self._app(scope, receive, wrapped_send)
        finally:
            self._emit(scope, status_code, (time.perf_counter() - start) * 1000)

    def _emit(self, scope: Dict[str, Any], status_code: int, duration_ms: float) -> None:
        # Never let instrumentation itself become the reason a request fails
        # (plan §2) — this runs in the request's own `finally`, so it must
        # not raise.
        try:
            settings = get_settings()
            account: Optional[AccountInDB] = (scope.get("state") or {}).get("account")
            outcome = "ok" if status_code < 400 else ("denied" if status_code in (401, 403) else "error")
            template = route_template(scope)
            engine.emit(build_event(
                kind="usage",
                surface="rest",
                feature=f"{scope['method']} {template}",
                duration_ms=duration_ms,
                outcome=outcome,
                account=account_field(account, settings),
                attributes={"http.route": template, "http.status_code": status_code},
            ))
        except Exception:
            pass
