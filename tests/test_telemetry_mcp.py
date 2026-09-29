"""Tests for hgai_module_mcp.telemetry (Phase 3 of
docs/architect/telemetry-20260929061557.md §4's MCP row): the `track_tool`
decorator stacked under every `@mcp.tool()`.
"""

import json

import pytest
from unittest.mock import patch

import hgai_module_telemetry.engine as engine
import hgai_module_mcp.server as mcp_server
from hgai_module_mcp.telemetry import _classify, track_tool
from hgai.models.account import AccountInDB, AccountPermissions

ADMIN = AccountInDB(
    username="admin", email=None, roles=["admin"], password_hash="",
    permissions=AccountPermissions(graphs=["*"], operations=["read", "write", "delete", "admin", "query"]),
)


# ── _classify: read the tool's own return value, never reimplement it ────────

@pytest.mark.parametrize("raw, expected_outcome", [
    ({"total": 3, "graphs": []}, "ok"),          # not a str at all (already parsed) -> ok
    ("not json at all", "ok"),
    ("42", "ok"),                                  # valid JSON, not a dict
    (json.dumps({"total": 3}), "ok"),               # dict, no "type" key
])
def test_classify_treats_non_error_shapes_as_ok(raw, expected_outcome):
    outcome, envelope = _classify(raw)
    assert outcome == expected_outcome and envelope is None


def test_classify_reads_permission_denied_as_denied():
    raw = json.dumps({"error": "Access to graph 'x' not permitted", "type": "PermissionDenied"})
    outcome, envelope = _classify(raw)
    assert outcome == "denied" and envelope["type"] == "PermissionDenied"


@pytest.mark.parametrize("type_", ["SHQLError", "ExecutionError", "ParseError", "NotFoundError"])
def test_classify_reads_any_other_typed_envelope_as_error(type_):
    raw = json.dumps({"error": "something went wrong", "type": type_})
    outcome, envelope = _classify(raw)
    assert outcome == "error" and envelope["type"] == type_


# ── track_tool: unit behavior against a fake tool ─────────────────────────────

@pytest.fixture
def captured_events():
    events = []
    with patch.object(engine, "emit", side_effect=events.append):
        yield events


@pytest.fixture(autouse=True)
def caller():
    token = mcp_server.set_caller(ADMIN)
    yield
    mcp_server.reset_caller(token)


def usage_events(events):
    return [e for e in events if e["kind"] == "usage"]


def error_events(events):
    return [e for e in events if e["kind"] == "error"]


async def test_a_successful_tool_call_emits_one_usage_event_and_no_error(captured_events):
    @track_tool
    async def hgai_fake_tool() -> str:
        return json.dumps({"ok": True})

    result = await hgai_fake_tool()
    assert result == json.dumps({"ok": True})  # unchanged return value
    assert len(usage_events(captured_events)) == 1
    assert error_events(captured_events) == []
    usage = usage_events(captured_events)[0]
    assert usage["surface"] == "mcp" and usage["feature"] == "mcp.hgai_fake_tool"
    assert usage["outcome"] == "ok"
    assert usage["attributes"]["hgai.mcp.tool"] == "hgai_fake_tool"
    assert usage["account"]["roles"] == ["admin"]


async def test_a_permission_denied_envelope_emits_a_denied_usage_and_error_event(captured_events):
    @track_tool
    async def hgai_fake_tool() -> str:
        return json.dumps({"error": "Access to graph 'secret-project' not permitted", "type": "PermissionDenied"})

    await hgai_fake_tool()
    assert usage_events(captured_events)[0]["outcome"] == "denied"
    err = error_events(captured_events)[0]
    assert err["outcome"] == "denied"
    assert err["error"]["type"] == "PermissionDenied"
    assert err["error"]["surface_context"] == "mcp.tool"
    assert "secret-project" not in str(err)  # templatized like every other surface
    assert err["error"]["stack_frames"] == []  # no live exception to extract frames from


async def test_a_business_error_envelope_emits_an_error_outcome_and_event(captured_events):
    @track_tool
    async def hgai_fake_tool() -> str:
        return json.dumps({"error": "boom", "type": "ExecutionError"})

    await hgai_fake_tool()
    assert usage_events(captured_events)[0]["outcome"] == "error"
    assert error_events(captured_events)[0]["error"]["type"] == "ExecutionError"


async def test_an_uncaught_exception_still_propagates_and_reports_a_real_stack_frame(captured_events):
    @track_tool
    async def hgai_fake_tool() -> str:
        raise RuntimeError("truly unexpected")

    with pytest.raises(RuntimeError, match="truly unexpected"):
        await hgai_fake_tool()
    assert usage_events(captured_events)[0]["outcome"] == "error"
    err = error_events(captured_events)[0]
    assert err["error"]["type"] == "RuntimeError"
    assert err["error"]["stack_frames"]  # a real traceback this time, unlike the envelope cases


async def test_two_different_tools_returning_the_same_generic_error_fingerprint_differently(captured_events):
    @track_tool
    async def hgai_tool_a() -> str:
        return json.dumps({"error": "not found", "type": "NotFoundError"})

    @track_tool
    async def hgai_tool_b() -> str:
        return json.dumps({"error": "not found", "type": "NotFoundError"})

    await hgai_tool_a()
    await hgai_tool_b()
    fps = {e["error"]["fingerprint"] for e in error_events(captured_events)}
    assert len(fps) == 2  # different tool -> different fingerprint, despite an identical message


def test_track_tool_preserves_the_wrapped_functions_metadata():
    @track_tool
    async def hgai_fake_tool(x: int) -> str:
        """docstring"""
        return "{}"

    assert hgai_fake_tool.__name__ == "hgai_fake_tool"
    assert hgai_fake_tool.__doc__ == "docstring"
    assert hgai_fake_tool.__wrapped__ is not None


async def test_telemetry_never_breaks_a_tool_call_even_when_broken(captured_events):
    @track_tool
    async def hgai_fake_tool() -> str:
        return json.dumps({"ok": True})

    with patch.object(engine, "emit", side_effect=RuntimeError("telemetry is on fire")):
        result = await hgai_fake_tool()
    assert result == json.dumps({"ok": True})


# ── Every real MCP tool is wrapped ────────────────────────────────────────────

async def test_every_registered_mcp_tool_is_wrapped_with_track_tool():
    tools = await mcp_server.mcp.list_tools()
    assert len(tools) == 30
    unwrapped = [
        t.name for t in tools
        if not hasattr(mcp_server.mcp._tool_manager._tools[t.name].fn, "__wrapped__")
    ]
    assert unwrapped == []


async def test_track_tool_does_not_change_a_real_tools_input_schema():
    tools = await mcp_server.mcp.list_tools()
    schema = next(t for t in tools if t.name == "hgai_hypernode_create").inputSchema
    assert schema["required"] == ["graph_id", "id", "label"]
    assert "graph_id" in schema["properties"]


async def test_a_real_denied_tool_call_produces_the_expected_telemetry(captured_events):
    reader = AccountInDB(
        username="reader", email=None, roles=["user"], password_hash="",
        permissions=AccountPermissions(graphs=[], operations=["read"]),
    )
    token = mcp_server.set_caller(reader)
    try:
        result = await mcp_server.hgai_hypergraph_get(graph_id="secret-graph")
    finally:
        mcp_server.reset_caller(token)
    assert json.loads(result)["type"] == "PermissionDenied"
    usage = usage_events(captured_events)[0]
    assert usage["feature"] == "mcp.hgai_hypergraph_get" and usage["outcome"] == "denied"
    assert usage["account"]["roles"] == ["user"]
    assert "secret-graph" not in str(error_events(captured_events)[0])
