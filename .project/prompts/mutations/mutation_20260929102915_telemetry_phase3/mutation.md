# Mutation Log

## Created
- **hgai_module_mcp/telemetry.py** — `track_tool` decorator (stacked under `@mcp.tool()`), `_classify` (reads a tool's own JSON-envelope return value for ok/denied/error, per the plan's "reads their return value, doesn't reimplement authorization" instruction), `_report`/`_account_field` (lazy-import `hgai_module_telemetry`, broadly caught, mirroring `hgai_module_shql/engine.py`'s Phase 2 hooks). Lives in `hgai_module_mcp` (not `hgai_module_telemetry`), matching the established direction: a surface module knows about telemetry, telemetry never knows about a surface.
- **tests/test_telemetry_mcp.py** — 19 tests: `_classify` unit tests, `track_tool` behavior against fake tools (success/denied-envelope/error-envelope/uncaught-exception, metadata preservation, never-breaks-the-call), a fingerprint-differs-by-tool test, and integration tests against the real `hgai_module_mcp.server` module (every one of the 30 registered tools is wrapped, a real tool's MCP input schema is unaffected, and a real denied call produces the expected events).

## Modified
- **hgai_module_telemetry/errors.py** — Added `build_error_event_from_message(exc_type, message, ...)`, `build_error_event`'s counterpart for a failure already caught and turned into a `{"error", "type"}` string (no live exception, so no traceback) — used by MCP's synthetic error events.
- **hgai_module_mcp/server.py** — `from .telemetry import track_tool`; stacked `@track_tool` under all 30 `@mcp.tool()` definitions (one line each).
