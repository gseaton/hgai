"""MCP tool instrumentation (plan §4's MCP row of
docs/architect/telemetry-20260929061557.md): one decorator, stacked under
`@mcp.tool()`, so each of the 30 tool definitions in server.py changes by
one line, not thirty call sites.

Lives in hgai_module_mcp (not hgai_module_telemetry) and lazily imports the
telemetry module's generic building blocks, the same direction and shape as
hgai_module_shql/engine.py's own telemetry hooks (Phase 2) — a surface
module knows about telemetry, telemetry never knows about a surface.
"""

import functools
import json
import logging
import time
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def _classify(raw_result: Any) -> Tuple[str, Optional[Dict[str, Any]]]:
    """(outcome, parsed_error_envelope | None) read from a tool's own return
    value — never reimplemented here.

    Every tool in this module catches its own errors and returns a JSON
    string; on failure that string has a `"type"` key (`_denied()`'s
    `{"error", "type": "PermissionDenied"}`, and the same shape every
    tool's own `except` blocks build for their own failure types —
    `"ParseError"`, `"SHQLError"`, `"ExecutionError"`, ...). A non-JSON or
    keyless-JSON return is a normal success value.
    """
    if not isinstance(raw_result, str):
        return "ok", None
    try:
        parsed = json.loads(raw_result)
    except (TypeError, ValueError):
        return "ok", None
    if not isinstance(parsed, dict) or "type" not in parsed:
        return "ok", None
    outcome = "denied" if parsed["type"] == "PermissionDenied" else "error"
    return outcome, parsed


def track_tool(fn: Callable) -> Callable:
    """Stack under `@mcp.tool()`. Never changes `fn`'s return value or
    raised exception — telemetry observes, it doesn't intercept (the same
    rule Phase 2 applies to the SHQL and REST hooks)."""
    tool_name = fn.__name__
    feature = f"mcp.{tool_name}"

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            result = await fn(*args, **kwargs)
        except Exception as exc:
            _report(feature, tool_name, (time.perf_counter() - start) * 1000, "error", exc=exc)
            raise
        outcome, envelope = _classify(result)
        _report(feature, tool_name, (time.perf_counter() - start) * 1000, outcome, envelope=envelope)
        return result

    return wrapper


def _account_field(settings) -> Optional[Dict[str, Any]]:
    """The caller MCP's own `_AuthMiddleware` (module.py) already resolved
    and published — a missing caller there is a 401 before any tool runs,
    so `_caller()` succeeding is the normal case; still guarded, since a
    telemetry helper must never be the reason a tool call fails."""
    try:
        from .server import _caller
        from hgai_module_telemetry.events import account_field
        return account_field(_caller(), settings)
    except Exception:
        return None


def _report(
    feature: str, tool_name: str, duration_ms: float, outcome: str,
    *, exc: Optional[Exception] = None, envelope: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        from hgai.config import get_settings
        from hgai_module_telemetry import engine
        from hgai_module_telemetry.errors import build_error_event, build_error_event_from_message
        from hgai_module_telemetry.events import build_event
    except ImportError:
        return
    try:
        settings = get_settings()
        account = _account_field(settings)
        attributes = {"hgai.mcp.tool": tool_name}
        emit_kwargs = dict(surface="mcp", feature=feature, duration_ms=duration_ms, outcome=outcome, account=account)
        engine.emit(build_event(kind="usage", attributes=attributes, **emit_kwargs))

        if exc is not None:
            engine.emit(build_error_event(exc, surface_context="mcp.tool", **emit_kwargs))
        elif envelope is not None:
            engine.emit(build_error_event_from_message(
                str(envelope.get("type", "Unknown")), str(envelope.get("error", "")),
                surface_context="mcp.tool", **emit_kwargs,
            ))
    except Exception:
        logger.debug("MCP telemetry failed", exc_info=True)
