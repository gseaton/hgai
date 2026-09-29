"""Shared REST-scope helpers used by both the request middleware and the
exception handlers (hgai/main.py) — kept separate so neither has to import
the other."""

from typing import Any, Dict


def route_template(scope: Dict[str, Any]) -> str:
    """Best-effort path template, e.g. `/api/v1/graphs/{graph_id}` rather
    than `/api/v1/graphs/eden` (plan §3: `feature` is always a template,
    never a raw value with data in it).

    FastAPI's router writes the matched route's resolved dynamic segments
    into `scope["path_params"]` before calling the endpoint; substituting
    each resolved value back for its `{param}` placeholder reconstructs the
    template without re-implementing route matching. Unmatched requests
    (404s) have no `path_params` and fall back to the raw path, which is
    fine — there's no route template to report for those.
    """
    path = scope.get("path", "")
    for key, value in (scope.get("path_params") or {}).items():
        if value is not None:
            path = path.replace(f"/{value}", f"/{{{key}}}", 1)
    return path


def request_start(scope: Dict[str, Any]):
    """The `time.perf_counter()` value `TelemetryMiddleware` stashed at the
    start of this request, or None if the middleware isn't installed (or
    this isn't a request it instrumented, e.g. a skipped static-asset path).
    Lets the exception handlers report a real `duration_ms` instead of 0."""
    return (scope.get("state") or {}).get("telemetry_start")
