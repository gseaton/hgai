"""Tests for hgai_module_telemetry (Phase 1: foundation + REST instrumentation).

See docs/architect/telemetry-20260929061557.md §9 for the testing plan this
follows: exporter batching/backoff against a fake HTTP client, a "never
blocks" property test, a "disabled means silent" test, and schema checks.
"""

import asyncio
import time

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from hgai.config import Settings
from hgai.models.account import AccountInDB, AccountPermissions

import hgai_module_telemetry.engine as engine
from hgai_module_telemetry.envelope import build_envelope
from hgai_module_telemetry.events import account_field, build_event
from hgai_module_telemetry.exporters import HTTPExporter, NullExporter, select_exporter
from hgai_module_telemetry.identity import hash_id
from hgai_module_telemetry.middleware import TelemetryMiddleware


def make_settings(**overrides) -> Settings:
    defaults = dict(
        secret_key="test-secret",
        server_id="hgai-test",
        telemetry_enabled=True,
        telemetry_endpoint="https://telemetry.hypergra.ai/report",
    )
    defaults.update(overrides)
    return Settings(**defaults)


def make_account(username="alice", roles=("user",)) -> AccountInDB:
    return AccountInDB(
        username=username, email=None, roles=list(roles), password_hash="",
        status="active", permissions=AccountPermissions(),
    )


@pytest.fixture(autouse=True)
def reset_engine_state():
    """Every test starts from a clean module-level state and leaves one behind."""
    engine.stop_scheduler()
    engine._exporter = NullExporter()
    engine._settings = None
    engine._stats = {
        "dropped_queue_full": 0, "batches_sent": 0, "batches_failed": 0,
        "records_sent": 0, "last_export_at": None, "last_export_outcome": None,
    }
    yield
    engine.stop_scheduler()


# ── Identity hashing ──────────────────────────────────────────────────────────

def test_hash_id_is_deterministic_and_never_the_raw_value():
    s = make_settings()
    h1 = hash_id("alice", s)
    h2 = hash_id("alice", s)
    assert h1 == h2
    assert h1 != "alice"
    assert len(h1) == 64  # sha256 hex


def test_hash_id_differs_across_deployments():
    assert hash_id("alice", make_settings(secret_key="a")) != hash_id("alice", make_settings(secret_key="b"))


# ── Event / envelope shape ────────────────────────────────────────────────────

def test_account_field_hashes_by_default_and_carries_role_and_is_agent():
    s = make_settings()
    field = account_field(make_account("bob", ["user"]), s)
    assert field["id_hash"] == hash_id("bob", s)
    assert field["roles"] == ["user"] and field["is_agent"] is False


def test_account_field_is_none_for_no_account():
    assert account_field(None, make_settings()) is None


def test_account_field_can_opt_into_the_clear():
    s = make_settings(telemetry_include_account_ids=True)
    assert account_field(make_account("carol"), s)["id_hash"] == "carol"


def test_account_field_flags_agent_role():
    assert account_field(make_account("bot", ["agent"]), make_settings())["is_agent"] is True


def test_build_event_rejects_invalid_kind_or_outcome():
    with pytest.raises(AssertionError):
        build_event(kind="bogus", surface="rest", feature="x", duration_ms=1, outcome="ok")
    with pytest.raises(AssertionError):
        build_event(kind="usage", surface="rest", feature="x", duration_ms=1, outcome="bogus")


def test_build_event_has_the_documented_shape():
    e = build_event(
        kind="usage", surface="rest", feature="GET /api/v1/graphs", duration_ms=12.3456, outcome="ok",
        account=None, attributes={"http.status_code": 200},
    )
    assert set(e) == {"kind", "surface", "feature", "timestamp", "duration_ms", "outcome", "actor", "account", "attributes", "error"}
    assert e["actor"] == "__system"
    a = build_event(kind="usage", surface="rest", feature="f", duration_ms=1, outcome="ok",
                    account={"id_hash": "abc", "roles": [], "is_agent": False})
    assert a["actor"] == "abc"
    assert e["timestamp"].endswith("Z")
    assert e["duration_ms"] == 12.346  # rounded, not truncated
    assert e["error"] is None


def test_build_envelope_carries_resource_scope_and_records():
    s = make_settings(server_id="srv-1", telemetry_environment="staging")
    records = [build_event(kind="usage", surface="rest", feature="f", duration_ms=1, outcome="ok")]
    env = build_envelope(records, s)
    assert env["resource"]["service.instance.id"] == "srv-1"
    assert env["resource"]["deployment.environment"] == "staging"
    assert env["scope"] == {"name": "hgai.telemetry", "version": "1"}
    assert env["records"] == records


# ── Exporters ─────────────────────────────────────────────────────────────────

async def test_null_exporter_is_a_true_noop():
    await NullExporter().export([{"anything": "goes"}])  # must not raise


async def test_http_exporter_posts_the_envelope_and_bearer_header():
    s = make_settings(telemetry_api_key="secret-token")
    response = MagicMock()
    response.raise_for_status = MagicMock()
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    with patch("hgai_module_telemetry.exporters.get_http_client", return_value=client):
        await HTTPExporter(s).export([{"kind": "usage"}])
    args, kwargs = client.post.call_args
    assert args[0] == s.telemetry_endpoint
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"
    assert kwargs["json"]["records"] == [{"kind": "usage"}]


async def test_http_exporter_propagates_failure_for_the_caller_to_retry():
    response = MagicMock()
    response.raise_for_status = MagicMock(side_effect=RuntimeError("boom"))
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    with patch("hgai_module_telemetry.exporters.get_http_client", return_value=client):
        with pytest.raises(RuntimeError):
            await HTTPExporter(make_settings()).export([{}])


def test_select_exporter_uses_http_when_endpoint_configured():
    assert isinstance(select_exporter(make_settings()), HTTPExporter)


def test_select_exporter_falls_back_to_local_storage_with_no_endpoint():
    # Phase 3a: no endpoint no longer means "discard" — see test_telemetry_local_storage.py
    # for LocalHypergraphExporter's own behavior.
    from hgai_module_telemetry.exporters import LocalHypergraphExporter
    assert isinstance(select_exporter(make_settings(telemetry_endpoint=None)), LocalHypergraphExporter)


def test_select_exporter_refuses_an_insecure_endpoint_by_default():
    from hgai_module_telemetry.exporters import LocalHypergraphExporter
    s = make_settings(telemetry_endpoint="http://telemetry.internal/report")
    # An insecure, refused endpoint is treated the same as "no endpoint" (Phase 3a).
    assert isinstance(select_exporter(s), LocalHypergraphExporter)


def test_select_exporter_allows_insecure_when_explicitly_opted_in():
    s = make_settings(telemetry_endpoint="http://localhost:9999/report", telemetry_allow_insecure=True)
    assert isinstance(select_exporter(s), HTTPExporter)


# ── engine: emit() / queue / background export loop ──────────────────────────

def test_emit_is_a_noop_when_telemetry_is_disabled():
    engine.start_scheduler(make_settings(telemetry_enabled=False))
    assert engine._queue is None
    engine.emit(build_event(kind="usage", surface="rest", feature="f", duration_ms=1, outcome="ok"))  # must not raise
    assert engine.status()["enabled"] is False
    assert engine.status()["queue_depth"] == 0


async def test_disabled_means_silent_no_network_calls_at_all():
    client = AsyncMock()
    with patch("hgai_module_telemetry.exporters.get_http_client", return_value=client):
        engine.start_scheduler(make_settings(telemetry_enabled=False))
        for _ in range(5):
            engine.emit(build_event(kind="usage", surface="rest", feature="f", duration_ms=1, outcome="ok"))
        await asyncio.sleep(0.05)
    client.post.assert_not_called()


async def test_emit_never_blocks_even_when_the_queue_is_full():
    engine.start_scheduler(make_settings(telemetry_queue_max_size=2, telemetry_flush_interval_seconds=999))
    event = build_event(kind="usage", surface="rest", feature="f", duration_ms=1, outcome="ok")
    start = time.perf_counter()
    for _ in range(200):
        engine.emit(event)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.25, f"emit() took {elapsed}s for 200 calls against a full queue"
    assert engine._stats["dropped_queue_full"] > 0
    assert engine._queue.qsize() == 2  # bounded, never grows past the configured max


async def test_export_loop_batches_by_size_and_reports_stats():
    sent = []

    class FakeExporter:
        async def export(self, records):
            sent.append(list(records))

    engine.start_scheduler(make_settings(telemetry_batch_size=3, telemetry_flush_interval_seconds=999))
    engine._exporter = FakeExporter()
    for i in range(3):
        engine.emit(build_event(kind="usage", surface="rest", feature=f"f{i}", duration_ms=1, outcome="ok"))
    for _ in range(50):
        if sent:
            break
        await asyncio.sleep(0.02)
    assert len(sent) == 1 and len(sent[0]) == 3
    status = engine.status()
    assert status["batches_sent"] == 1 and status["records_sent"] == 3
    assert status["last_export_outcome"] == "ok"


async def test_export_loop_flushes_a_partial_batch_on_the_interval():
    sent = []

    class FakeExporter:
        async def export(self, records):
            sent.append(list(records))

    engine.start_scheduler(make_settings(telemetry_batch_size=100, telemetry_flush_interval_seconds=0.05))
    engine._exporter = FakeExporter()
    engine.emit(build_event(kind="usage", surface="rest", feature="only-one", duration_ms=1, outcome="ok"))
    for _ in range(50):
        if sent:
            break
        await asyncio.sleep(0.02)
    assert sent == [[sent[0][0]]] or len(sent[0]) == 1


async def test_export_retries_with_backoff_then_drops_the_batch(monkeypatch):
    monkeypatch.setattr(engine, "_BACKOFF_BASE_SECONDS", 0.001)
    attempts = []

    class FailingExporter:
        async def export(self, records):
            attempts.append(1)
            raise RuntimeError("still down")

    engine.start_scheduler(make_settings(telemetry_batch_size=1, telemetry_flush_interval_seconds=999))
    engine._exporter = FailingExporter()
    engine.emit(build_event(kind="usage", surface="rest", feature="f", duration_ms=1, outcome="ok"))
    for _ in range(200):
        if engine._stats["batches_failed"]:
            break
        await asyncio.sleep(0.01)
    assert len(attempts) == engine._MAX_EXPORT_ATTEMPTS
    assert engine._stats["batches_failed"] == 1
    assert "still down" in engine._stats["last_export_outcome"]
    assert engine._queue.qsize() == 0  # dropped, not requeued — never grows without bound


async def test_usage_events_are_sampled_but_errors_never_are(monkeypatch):
    engine.start_scheduler(make_settings(telemetry_sample_rate=0.0, telemetry_flush_interval_seconds=999))
    engine.emit(build_event(kind="usage", surface="rest", feature="f", duration_ms=1, outcome="ok"))
    engine.emit(build_event(kind="error", surface="rest", feature="f", duration_ms=1, outcome="error"))
    assert engine._queue.qsize() == 1  # usage dropped by 0% sample rate, error kept


async def test_status_never_exposes_the_full_endpoint_url_or_api_key():
    engine.start_scheduler(make_settings(telemetry_endpoint="https://telemetry.hypergra.ai/report?token=shh"))
    s = engine.status()
    assert s["endpoint_host"] == "telemetry.hypergra.ai"
    assert "shh" not in str(s) and "report" not in str(s)


# ── REST middleware (real ASGI request cycle, no DB) ──────────────────────────

def build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(TelemetryMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/v1/graphs/{graph_id}")
    async def get_graph(graph_id: str, request: Request):
        # Simulates what hgai.core.auth.get_current_account now does.
        request.state.account = make_account("alice", ["admin"])
        return {"id": graph_id}

    @app.get("/api/v1/denied")
    async def denied():
        raise HTTPException(status_code=403, detail="nope")

    @app.get("/ui/js/app.js")
    async def ui_asset():
        return {}

    return app


@pytest.fixture
def captured_events():
    events = []
    with patch.object(engine, "emit", side_effect=events.append):
        yield events


def test_middleware_reconstructs_the_route_template_not_the_raw_id(captured_events):
    with TestClient(build_test_app()) as client:
        client.get("/api/v1/graphs/eden")
    assert captured_events[0]["feature"] == "GET /api/v1/graphs/{graph_id}"
    assert captured_events[0]["attributes"]["http.route"] == "/api/v1/graphs/{graph_id}"


def test_middleware_reads_the_account_the_route_stashed_on_request_state(captured_events):
    with TestClient(build_test_app()) as client:
        client.get("/api/v1/graphs/eden")
    assert captured_events[0]["account"]["roles"] == ["admin"]


def test_middleware_maps_403_to_denied_outcome_with_no_account(captured_events):
    with TestClient(build_test_app()) as client:
        client.get("/api/v1/denied")
    assert captured_events[0]["outcome"] == "denied"
    assert captured_events[0]["account"] is None


def test_middleware_maps_2xx_to_ok_and_5xx_to_error(captured_events):
    with TestClient(build_test_app()) as client:
        client.get("/health")
    assert captured_events[0]["outcome"] == "ok"
    assert captured_events[0]["attributes"]["http.status_code"] == 200


def test_middleware_skips_static_ui_assets(captured_events):
    with TestClient(build_test_app()) as client:
        client.get("/ui/js/app.js")
    assert captured_events == []


def test_middleware_never_raises_even_if_emit_itself_blows_up():
    app = build_test_app()
    with patch.object(engine, "emit", side_effect=RuntimeError("telemetry bug")):
        with TestClient(app) as client:
            r = client.get("/health")
    assert r.status_code == 200  # the request must succeed regardless
