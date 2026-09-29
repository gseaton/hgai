"""Tests for hgai_module_telemetry.errors and the REST exception handlers
(Phase 2 of docs/architect/telemetry-20260929061557.md §7)."""

import re

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.testclient import TestClient
from starlette.responses import PlainTextResponse
from unittest.mock import patch

import hgai_module_telemetry.engine as engine
from hgai_module_telemetry import rest_errors
from hgai_module_telemetry.errors import build_error_event, fingerprint, stack_frames, templatize_message
from hgai_module_telemetry.middleware import TelemetryMiddleware


# ── templatize_message ────────────────────────────────────────────────────────

@pytest.mark.parametrize("message, expected", [
    ("Hypergraph not found: 'my-secret-project'", "Hypergraph not found: '…'"),
    ('Hypergraph not found: "my-secret-project"', "Hypergraph not found: '…'"),
    ("no quoted data here", "no quoted data here"),
    ("two 'values' in 'one' message", "two '…' in '…' message"),
])
def test_templatize_message_redacts_quoted_segments(message, expected):
    assert templatize_message(message) == expected


def test_templatize_message_same_shape_different_data_fingerprints_identically():
    a = templatize_message("Hypergraph not found: 'customer-a-graph'")
    b = templatize_message("Hypergraph not found: 'customer-b-graph'")
    assert a == b


# ── stack_frames ──────────────────────────────────────────────────────────────

def _raise_from_here():
    raise ValueError("boom")


def test_stack_frames_are_repo_relative_with_no_source_text():
    try:
        _raise_from_here()
    except ValueError as e:
        frames = stack_frames(e.__traceback__)
    assert frames  # at least this file's frame
    last = frames[-1]
    assert set(last) == {"file", "line", "function"}
    assert last["function"] == "_raise_from_here"
    assert not last["file"].startswith("/")  # relative, not absolute
    assert "tests/test_telemetry_errors.py" in last["file"] or last["file"].endswith("test_telemetry_errors.py")


def test_stack_frames_excludes_stdlib_and_site_packages_frames():
    try:
        int("not a number")
    except ValueError as e:
        frames = stack_frames(e.__traceback__)
    # Only this file's frame should survive — int()'s own internal frame (if any) is stdlib.
    assert all("test_telemetry_errors.py" in f["file"] for f in frames)


def test_stack_frames_handles_no_traceback():
    assert stack_frames(None) == []


# ── fingerprint / build_error_event ───────────────────────────────────────────

def test_fingerprint_is_deterministic_for_the_same_inputs():
    assert fingerprint("ValueError", "f.py:1:g", "boom") == fingerprint("ValueError", "f.py:1:g", "boom")


def test_fingerprint_differs_when_any_input_differs():
    base = fingerprint("ValueError", "f.py:1:g", "boom")
    assert fingerprint("TypeError", "f.py:1:g", "boom") != base
    assert fingerprint("ValueError", "f.py:2:g", "boom") != base
    assert fingerprint("ValueError", "f.py:1:g", "bang") != base


def test_build_error_event_shape_and_redaction():
    try:
        raise ValueError("bad id: 'secret-123'")
    except ValueError as e:
        event = build_error_event(
            e, surface="shql", surface_context="shql.execute", feature="shql.query",
            duration_ms=5.0, outcome="error", account=None, http_status=None,
        )
    assert event["kind"] == "error"
    assert event["error"]["type"] == "ValueError"
    assert event["error"]["message_template"] == "bad id: '…'"
    assert "secret-123" not in str(event)
    assert event["error"]["surface_context"] == "shql.execute"
    assert re.fullmatch(r"[0-9a-f]{64}", event["error"]["fingerprint"])
    assert event["error"]["stack_frames"]


def test_build_error_event_two_occurrences_of_the_same_bug_share_a_fingerprint():
    def make(id_):
        try:
            raise ValueError(f"not found: {id_!r}")
        except ValueError as e:
            return build_error_event(e, surface="rest", surface_context="x", feature="f",
                                     duration_ms=1, outcome="error", account=None)
    a = make("customer-one")
    b = make("customer-two")
    assert a["error"]["fingerprint"] == b["error"]["fingerprint"]
    assert "customer-one" not in str(a) and "customer-two" not in str(b)


# ── REST exception handlers (real ASGI pipeline: middleware + handlers) ──────

def build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(TelemetryMiddleware)

    @app.exception_handler(HTTPException)
    async def _http_handler(request, exc):
        rest_errors.report(request, exc, exc.status_code)
        return await default_http_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def _unhandled_handler(request, exc):
        rest_errors.report(request, exc, 500)
        return PlainTextResponse("Internal Server Error", status_code=500)

    @app.get("/api/v1/graphs/{graph_id}")
    async def get_graph(graph_id: str):
        raise HTTPException(status_code=404, detail=f"Hypergraph {graph_id!r} not found")

    @app.get("/api/v1/forbidden")
    async def forbidden():
        raise HTTPException(status_code=403, detail="nope")

    @app.get("/api/v1/anon")
    async def anon():
        raise HTTPException(status_code=401, detail="no token")

    @app.get("/api/v1/boom")
    async def boom():
        raise RuntimeError("totally unexpected")

    return app


@pytest.fixture
def captured_events():
    events = []
    with patch.object(engine, "emit", side_effect=events.append):
        yield events


def error_events(events):
    return [e for e in events if e["kind"] == "error"]


def test_404_produces_an_error_event_and_the_response_is_unchanged(captured_events):
    with TestClient(build_test_app(), raise_server_exceptions=False) as client:
        r = client.get("/api/v1/graphs/eden")
    assert r.status_code == 404 and r.json() == {"detail": "Hypergraph 'eden' not found"}
    errs = error_events(captured_events)
    assert len(errs) == 1
    e = errs[0]
    assert e["error"]["type"] == "HTTPException"
    assert e["error"]["http_status"] == 404
    assert e["error"]["surface_context"] == "rest.exception_handler"
    assert "eden" not in str(e)  # redacted, same as the rule for every other surface
    assert e["feature"] == "GET /api/v1/graphs/{graph_id}"
    assert e["duration_ms"] > 0  # taken from the middleware's stashed start, not left at 0


def test_403_maps_to_denied_outcome(captured_events):
    with TestClient(build_test_app(), raise_server_exceptions=False) as client:
        client.get("/api/v1/forbidden")
    assert error_events(captured_events)[0]["outcome"] == "denied"


def test_401_is_not_reported_as_an_error_event(captured_events):
    with TestClient(build_test_app(), raise_server_exceptions=False) as client:
        client.get("/api/v1/anon")
    assert error_events(captured_events) == []
    # ...but the ordinary usage event (from the middleware) still fires.
    assert any(e["kind"] == "usage" and e["outcome"] == "denied" for e in captured_events)


def test_uncaught_exception_returns_the_unmodified_default_500_response(captured_events):
    with TestClient(build_test_app(), raise_server_exceptions=False) as client:
        r = client.get("/api/v1/boom")
    assert r.status_code == 500 and r.text == "Internal Server Error"
    e = error_events(captured_events)[0]
    assert e["error"]["type"] == "RuntimeError"
    assert e["error"]["http_status"] == 500
    assert e["error"]["message_template"] == "totally unexpected"


def test_error_reporting_never_raises_even_when_broken(captured_events):
    with patch.object(engine, "emit", side_effect=RuntimeError("telemetry is on fire")):
        with TestClient(build_test_app(), raise_server_exceptions=False) as client:
            r = client.get("/api/v1/graphs/eden")
    assert r.status_code == 404  # the real response must still get through


def test_report_is_a_noop_with_telemetry_disabled(captured_events):
    # engine.emit() itself already no-ops when telemetry is off (Phase 1); this
    # just confirms rest_errors.report() doesn't bypass it or crash either way.
    with patch.object(engine, "_queue", None):
        with TestClient(build_test_app(), raise_server_exceptions=False) as client:
            client.get("/api/v1/graphs/eden")
