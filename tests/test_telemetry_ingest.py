"""Tests for POST /api/v1/telemetry/ingest (Phase 4 of
docs/architect/telemetry-20260929061557.md §4 — the Web UI and hgsh rows).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch

import hgai_module_telemetry.engine as engine
from hgai_module_telemetry.api_router import router
from hgai.core.auth import get_current_account
from hgai.models.account import AccountInDB


def build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    async def fake_account():
        return AccountInDB(username="alice", email=None, roles=["user"], password_hash="")

    app.dependency_overrides[get_current_account] = fake_account
    return app


@pytest.fixture
def captured_events():
    events = []
    with patch.object(engine, "emit", side_effect=events.append):
        yield events


@pytest.fixture
def client():
    with TestClient(build_test_app()) as c:
        yield c


def test_ingest_enqueues_a_usage_event_with_the_verified_account(client, captured_events):
    r = client.post("/api/v1/telemetry/ingest", json={
        "surface": "web-ui", "feature": "ui.visualize.render", "duration_ms": 12.0,
    })
    assert r.status_code == 202
    assert r.json() == {"accepted": True}
    (event,) = captured_events
    assert event["kind"] == "usage"
    assert event["surface"] == "web-ui" and event["feature"] == "ui.visualize.render"
    assert event["account"]["roles"] == ["user"]  # the server's own verified account, not client-claimed


def test_ingest_accepts_the_shell_surface_and_hyphenated_features(client, captured_events):
    r = client.post("/api/v1/telemetry/ingest", json={"surface": "shell", "feature": "shell.import-rdf"})
    assert r.status_code == 202
    assert captured_events[0]["surface"] == "shell" and captured_events[0]["feature"] == "shell.import-rdf"


@pytest.mark.parametrize("body, field", [
    ({"surface": "some-other-service", "feature": "ui.x.y"}, "surface"),
    ({"surface": "web-ui", "feature": "not-a-known-shape"}, "feature"),
    ({"surface": "web-ui", "feature": "ui.x.y", "outcome": "whatever"}, "outcome"),
])
def test_ingest_rejects_values_outside_the_known_shape(client, body, field):
    r = client.post("/api/v1/telemetry/ingest", json=body)
    assert r.status_code == 422
    assert field in r.text


def test_ingest_strips_attributes_beyond_the_allowlisted_shape(client, captured_events):
    huge_value = "x" * 1000
    r = client.post("/api/v1/telemetry/ingest", json={
        "surface": "web-ui", "feature": "ui.notes.save",
        "attributes": {**{f"k{i}": i for i in range(20)}, "big": huge_value},
    })
    assert r.status_code == 202
    attrs = captured_events[0]["attributes"]
    assert len(attrs) <= 8  # _MAX_ATTRIBUTES
    if "big" in attrs:
        assert len(attrs["big"]) <= 100  # _MAX_ATTRIBUTE_STR_LEN


def test_ingest_rejects_a_free_text_query_content_style_payload(client):
    # The hard privacy rule (plan §5.2): a client can't smuggle arbitrary
    # content through the one field shaped like free text.
    r = client.post("/api/v1/telemetry/ingest", json={
        "surface": "web-ui", "feature": "select * from where node.label = 'secret customer name'",
    })
    assert r.status_code == 422


def test_ingest_always_returns_202_even_if_emit_is_broken(client):
    with patch.object(engine, "emit", side_effect=RuntimeError("telemetry is on fire")):
        r = client.post("/api/v1/telemetry/ingest", json={"surface": "web-ui", "feature": "ui.query.run"})
    assert r.status_code == 202


def test_ingest_requires_authentication():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")  # no dependency override this time
    with TestClient(app) as c:
        r = c.post("/api/v1/telemetry/ingest", json={"surface": "web-ui", "feature": "ui.query.run"})
    assert r.status_code == 401
