"""Tests for execute_shql's telemetry wrapper (Phase 2 of
docs/architect/telemetry-20260929061557.md §4/§7).

Reuses the same fake storage as tests/test_shql_aggregate_pushdown.py so the
telemetry wrapper is exercised against real `execute_shql` behavior, not a
mock of it — the point is to prove the wrapper is *transparent* (identical
return value / raised exception) as well as correct about what it reports.
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from hgai.models.account import AccountInDB
import hgai_module_telemetry.engine as engine
from hgai_module_shql import engine as shql_engine
from hgai_module_shql.parser import SHQLError, SHQLPermissionError
from tests.storage_fixtures import mongod, stores  # noqa: F401  (fixtures used by name)

ADMIN = AccountInDB(username="root", email=None, roles=["admin"], password_hash="", status="active")
READER = AccountInDB(
    username="reader", email=None, roles=["user"], password_hash="",
    permissions={"graphs": [], "operations": ["read", "query"]},
)


@pytest.fixture
def storage(stores):  # noqa: F811
    nodes, edges = stores

    class Hypergraphs:
        async def get(self, gid, space_id=None):
            return SimpleNamespace(id=gid, space_id=None, type="instantiated", composition=[]) \
                if gid == "g" else None

    class Meshes:
        async def get(self, mid):
            return None

    s = SimpleNamespace(hypernodes=nodes, hyperedges=edges, hypergraphs=Hypergraphs(), meshes=Meshes())
    with patch.object(shql_engine, "get_storage", return_value=s):
        yield s


@pytest.fixture
def captured_events():
    events = []
    with patch.object(engine, "emit", side_effect=events.append):
        yield events


def only(events, kind):
    matches = [e for e in events if e["kind"] == kind]
    assert len(matches) == 1, f"expected exactly one {kind!r} event, got {[e['kind'] for e in events]}"
    return matches[0]


async def test_a_successful_query_emits_one_usage_event_with_shql_attributes(storage, captured_events):
    q = "shql:\n  from: g\n  where:\n    - node: {bind: '?n', type: person}\n  select: ['?n.id']\n"
    result = await shql_engine.execute_shql(q, use_cache=False, account=ADMIN)
    assert result.items  # the wrapper didn't swallow or alter the real result

    usage = only(captured_events, "usage")
    assert usage["surface"] == "shql" and usage["feature"] == "shql.query"
    assert usage["outcome"] == "ok"
    assert usage["account"]["roles"] == ["admin"]
    attrs = usage["attributes"]
    assert attrs["hgai.shql.pattern_kinds"] == ["node"]
    assert attrs["hgai.shql.aggregate_requested"] is False
    assert attrs["hgai.shql.infer"] is False
    assert attrs["hgai.shql.cached"] is False
    assert usage["duration_ms"] >= 0


async def test_an_aggregate_query_reports_pushdown_flags(storage, captured_events):
    q = ("shql:\n  from: g\n  where:\n    - node: '?n'\n  select: ['?n.type']\n"
         "  aggregate: {count: true, group_by: n.type}\n")
    await shql_engine.execute_shql(q, use_cache=False, account=ADMIN)
    attrs = only(captured_events, "usage")["attributes"]
    assert attrs["hgai.shql.aggregate_requested"] is True
    assert attrs["hgai.shql.aggregate_pushdown"] is True  # this session's earlier pushdown work, visible for free


async def test_a_missing_hypergraph_raises_normally_and_emits_one_shql_error_event(storage, captured_events):
    q = "shql:\n  from: does-not-exist\n  where:\n    - node: '?n'\n"
    with pytest.raises(SHQLError):
        await shql_engine.execute_shql(q, use_cache=False, account=ADMIN)

    err = only(captured_events, "error")
    assert err["surface"] == "shql" and err["outcome"] == "error"
    assert err["error"]["type"] == "SHQLError"
    assert err["error"]["surface_context"] == "shql.execute"
    assert "does-not-exist" not in str(err)  # templatized, same redaction rule as every other surface


async def test_a_permission_denial_maps_to_denied_outcome(storage, captured_events):
    q = "shql:\n  from: g\n  where:\n    - node: '?n'\n"
    with pytest.raises(SHQLPermissionError):
        await shql_engine.execute_shql(q, use_cache=False, account=READER)
    assert only(captured_events, "error")["outcome"] == "denied"


async def test_telemetry_never_changes_what_the_caller_sees_even_if_it_breaks(storage, captured_events):
    q = "shql:\n  from: g\n  where:\n    - node: '?n'\n  select: ['?n.id']\n"
    with patch.object(engine, "emit", side_effect=RuntimeError("telemetry bug")):
        result = await shql_engine.execute_shql(q, use_cache=False, account=ADMIN)
    assert result.items  # real result still comes back despite the broken emit()


async def test_telemetry_never_changes_the_raised_exception_even_if_it_breaks(storage):
    q = "shql:\n  from: does-not-exist\n  where:\n    - node: '?n'\n"
    with patch.object(engine, "emit", side_effect=RuntimeError("telemetry bug")):
        with pytest.raises(SHQLError):  # not RuntimeError — the real exception, not telemetry's
            await shql_engine.execute_shql(q, use_cache=False, account=ADMIN)
