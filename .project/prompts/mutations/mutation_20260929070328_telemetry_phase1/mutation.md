# Mutation Log

## Created
- **hgai_module_telemetry/__init__.py** — Module docstring/summary; exports `TelemetryModule`.
- **hgai_module_telemetry/module.py** — `TelemetryModule` descriptor (name/version/description/get_router), matching the Mesh/SHQL/AgentChat module convention.
- **hgai_module_telemetry/identity.py** — `hash_id(value, settings)`: HMAC-SHA256 keyed by `settings.secret_key`, used to hash account/graph/space ids by default.
- **hgai_module_telemetry/events.py** — `build_event(...)` (the OTEL-shaped record, plan §3) and `account_field(account, settings)` (hashed by default, opt-in clear via `HGAI_TELEMETRY_INCLUDE_ACCOUNT_IDS`).
- **hgai_module_telemetry/envelope.py** — `build_envelope(records, settings)`: the `hgai-envelope` wire format (resource + scope + records).
- **hgai_module_telemetry/exporters.py** — `Exporter` ABC, `NullExporter`, `HTTPExporter` (posts the envelope, bearer auth, HTTPS-required unless `HGAI_TELEMETRY_ALLOW_INSECURE`), `select_exporter(settings)`, shared `get_http_client`/`close_http_client`.
- **hgai_module_telemetry/engine.py** — `emit()` (fire-and-forget, bounded queue, oldest-drop, sampling for usage events only), `start_scheduler`/`stop_scheduler` (background export task, mirrors `hgai_module_mesh/scheduler.py`), batching by size/flush-interval, capped-retry-then-drop export, `status()` for the admin endpoint.
- **hgai_module_telemetry/middleware.py** — `TelemetryMiddleware`, a pure ASGI middleware recording one usage event per REST request (route-template reconstruction from `scope["path_params"]`, outcome from status code, account read from `scope["state"]["account"]`); never raises.
- **hgai_module_telemetry/api_router.py** — `GET /api/v1/telemetry/status` (admin-only).
- **tests/test_telemetry.py** — 30 tests: identity hashing, event/envelope shape, exporter unit tests (mocked HTTP client), engine tests (disabled-means-silent, never-blocks, batching, backoff-then-drop, sampling, status redaction), and REST middleware integration tests against a real ASGI request cycle.
- **docs/architect/telemetry-20260929061557.md** — (from the prior turn's plan; unchanged this turn.)

## Modified
- **hgai/config.py** — Added the Phase 1 `HGAI_TELEMETRY_*` settings (enabled, endpoint, protocol, api_key, batch_size, flush_interval, queue_max_size, include_graph_ids, include_account_ids, allow_insecure, sample_rate, environment), plus `telemetry_local_enabled`/`telemetry_local_retention_days` reserved for Phase 3a.
- **hgai/core/auth.py** — `get_current_account` now takes `request: Request` and stashes the authenticated account onto `request.state.account` (backed by `scope["state"]`), so the outer ASGI middleware can read it after the fact without re-authenticating. No behavior change for existing callers.
- **hgai/main.py** — Wires the telemetry background task into the lifespan (start/stop, alongside the mesh scheduler; closes the shared telemetry HTTP client on shutdown) and mounts `TelemetryMiddleware` and the telemetry router conditionally (`try/except BaseException`, non-fatal), matching the Mesh/SHQL/MCP/AgentChat pattern.
- **.env.example**, **README.md**, **docs/help/notes/admin/configuration.md** — Documented the new `HGAI_TELEMETRY_*` settings, following the precedent set for the earlier SHQL/aggregation settings.
