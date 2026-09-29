"""Tests for hgai_module_telemetry.local_storage (Phase 3a of
docs/architect/telemetry-20260929061557.md §3a): the `__local-telemetry`
hypergraph, slug generation, isolation and retention.

Runs against a real throwaway MongoDB (the same `mongod` fixture the
storage-aggregation work this session already established) through the
real `hgai.db.storage` singleton and `hgai.core.engine` functions — the
actual code path telemetry writes through, not a mock of it.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import AsyncMock, patch

from hgai.db.storage import close_storage, get_storage, init_storage
from hgai.models.account import AccountInDB, AccountPermissions
from hgai_module_telemetry import local_storage
from hgai_module_telemetry.exporters import CompositeExporter, HTTPExporter, LocalHypergraphExporter, select_exporter
from tests.storage_fixtures import mongod  # noqa: F401  (fixture used by name)

UTC = timezone.utc
ADMIN = AccountInDB(username="admin", email=None, roles=["admin"], password_hash="")
READER = AccountInDB(
    username="reader", email=None, roles=["user"], password_hash="",
    permissions=AccountPermissions(graphs=[], operations=["read", "query"]),
)


def event(**overrides):
    base = {
        "kind": "usage", "surface": "rest", "feature": "GET /api/v1/graphs",
        "timestamp": datetime.now(UTC).isoformat(), "duration_ms": 1.0, "outcome": "ok",
        "account": None, "attributes": {}, "error": None,
    }
    base.update(overrides)
    return base


# ── Slug generation (pure function, no DB) ────────────────────────────────────

def test_rest_slug_strips_method_prefix_and_path_noise():
    slug = local_storage.build_slug(event(
        surface="rest", feature="POST /api/v1/hyperedges/{edge_id}", outcome="ok",
        timestamp="2026-09-29T06:15:57.123Z",
    ))
    assert slug == "rest-hyperedges-20260929061557"


def test_error_slug_includes_outcome_and_error_type_deduplicated():
    slug = local_storage.build_slug(event(
        surface="rest", feature="POST /api/v1/hyperedges", outcome="denied",
        error={"type": "PermissionDenied"}, timestamp="2026-09-29T06:15:57.123Z",
    ))
    assert slug == "rest-hyperedges-denied-permissiondenied-20260929061557"


def test_ok_outcome_is_never_a_token():
    slug = local_storage.build_slug(event(feature="GET /api/v1/graphs", outcome="ok"))
    assert "-ok-" not in slug and not slug.startswith("ok-")


def test_dotted_feature_tokens_and_adjacent_dedup_with_surface():
    slug = local_storage.build_slug(event(
        surface="shql", feature="shql.query", outcome="ok", timestamp="2026-09-29T06:16:00Z",
    ))
    assert slug == "shql-query-20260929061600"  # surface "shql" + feature "shql","query" -> dedup adjacent


def test_slug_truncates_to_four_tokens():
    slug = local_storage.build_slug(event(
        surface="ui", feature="visualize.focus.dblclick.extra.tokens", outcome="denied",
        error={"type": "SomeError"}, timestamp="2026-09-29T06:15:57Z",
    ))
    body = slug.rsplit("-", 1)[0]  # strip the timestamp suffix
    assert len(body.split("-")) == 4


def test_slug_falls_back_when_no_tokens_extractable():
    slug = local_storage.build_slug(event(surface="", feature="", outcome="ok", kind="usage"))
    assert slug.startswith("usage-x-") or slug.startswith("usage-")


def test_two_events_at_different_seconds_never_collide():
    a = local_storage.build_slug(event(timestamp="2026-09-29T06:15:57Z"))
    b = local_storage.build_slug(event(timestamp="2026-09-29T06:15:58Z"))
    assert a != b


# ── Real storage integration ──────────────────────────────────────────────────

@pytest.fixture
async def storage(mongod):  # noqa: F811
    """Real MongoDB-backed storage, initialized/closed per test — the actual
    global singleton `hgai.core.engine`'s functions read from."""
    db_name = f"hgai_telemetry_test_{id(asyncio.current_task())}"
    await init_storage("mongodb", mongo_uri=mongod, mongo_db=db_name)
    try:
        yield get_storage()
    finally:
        client = get_storage()._client if hasattr(get_storage(), "_client") else None
        await close_storage()
        if client is not None:
            await client.drop_database(db_name)
        else:
            from motor.motor_asyncio import AsyncIOMotorClient
            cli = AsyncIOMotorClient(mongod)
            await cli.drop_database(db_name)
            cli.close()


async def test_write_records_creates_the_graph_lazily(storage):
    await local_storage.write_records([event()])
    from hgai.core.engine import get_hypergraph
    graph = await get_hypergraph(local_storage.GRAPH_ID, space_id=None)
    assert graph is not None
    assert graph.label == "Local Telemetry"
    assert set(graph.tags) == {"system", "telemetry"}
    assert graph.created_by == "system"
    assert graph.space_id is None


async def test_write_records_is_idempotent_about_the_graph(storage):
    await local_storage.write_records([event()])
    await local_storage.write_records([event()])  # must not raise on the second ensure_graph()
    from hgai_module_storage.filters import HypernodeSearchFilters
    docs = await get_storage().hypernodes.search(
        HypernodeSearchFilters(hypergraph_ids=[local_storage.GRAPH_ID]), skip=0, limit=10,
    )
    assert len(docs) == 2


async def test_written_hypernode_has_the_documented_shape(storage):
    rec = event(
        kind="error", surface="shql", feature="shql.query", outcome="error",
        error={"fingerprint": "abc123", "type": "SHQLError", "message_template": "boom",
               "surface_context": "shql.execute", "http_status": None, "stack_frames": []},
        timestamp="2026-09-29T06:15:57Z",
    )
    await local_storage.write_records([rec])
    from hgai_module_storage.filters import HypernodeSearchFilters
    (doc,) = await get_storage().hypernodes.search(
        HypernodeSearchFilters(hypergraph_ids=[local_storage.GRAPH_ID]), skip=0, limit=10,
    )
    assert doc["id"] == doc["label"] == local_storage.build_slug(rec)
    assert doc["type"] == "OTEL"
    assert doc["attributes"] == rec  # structured, not stringified
    assert '"fingerprint": "abc123"' in doc["description"]  # human-readable JSON
    assert set(doc["tags"]) == {"telemetry", "error"}
    assert doc["status"] == "active"
    assert doc["valid_from"] is not None


async def test_two_identically_shaped_events_in_the_same_second_both_land(storage):
    # Same surface/feature/outcome -> the same deterministic slug (build_slug
    # is second-precision) -> the store's own uniqueness constraint would
    # reject the second insert outright without _create_with_retry's
    # disambiguation. Realistic under any real traffic, not just this test.
    ts = datetime.now(UTC).isoformat()
    await local_storage.write_records([event(timestamp=ts), event(timestamp=ts)])
    from hgai_module_storage.filters import HypernodeSearchFilters
    docs = await get_storage().hypernodes.search(
        HypernodeSearchFilters(hypergraph_ids=[local_storage.GRAPH_ID]), skip=0, limit=10,
    )
    assert len(docs) == 2
    assert len({d["id"] for d in docs}) == 2  # distinct ids despite the identical slug base


async def test_local_telemetry_is_queryable_and_aggregatable_with_shql(storage):
    await local_storage.write_records([
        event(surface="rest", feature="GET /api/v1/graphs", outcome="ok"),
        event(surface="rest", feature="GET /api/v1/graphs", outcome="ok"),
        event(kind="error", surface="shql", feature="shql.query", outcome="error",
              error={"type": "SHQLError"}),
    ])
    from hgai_module_shql.engine import execute_shql
    result = await execute_shql(
        f"shql:\n  from: {local_storage.GRAPH_ID}\n  where:\n    - node: {{bind: '?n', type: OTEL}}\n"
        "  select: ['?n.attributes.kind']\n  aggregate: {count: true, group_by: n.attributes.kind}\n",
        use_cache=False, account=ADMIN,
    )
    assert result.meta["count"] == 3
    assert result.meta["groups"] == {"usage": 2, "error": 1}
    assert result.meta["aggregate_pushdown"] is True  # exact, not candidate-capped


# ── Isolation ──────────────────────────────────────────────────────────────────

async def test_hidden_from_the_default_hypergraph_listing_but_reachable_with_include_system(storage):
    await local_storage.write_records([event()])
    from hgai.core.engine import list_hypergraphs
    _, default = await list_hypergraphs()
    _, with_system = await list_hypergraphs(include_system=True)
    assert local_storage.GRAPH_ID not in [g.id for g in default]
    assert local_storage.GRAPH_ID in [g.id for g in with_system]


async def test_excluded_from_mesh_federations_all_local_graphs(storage):
    await local_storage.write_records([event()])
    from hgai_module_mesh.engine import _local_graph_ids
    assert local_storage.GRAPH_ID not in await _local_graph_ids()


async def test_admin_only_by_the_existing_permission_model_not_a_new_one(storage):
    await local_storage.write_records([event()])
    from hgai.core.auth import PermissionDeniedError, check_graph_permission, filter_accessible_graphs
    from hgai.core.engine import get_hypergraph

    with pytest.raises(PermissionDeniedError):
        await check_graph_permission(READER, local_storage.GRAPH_ID, "read", unowned=True)
    await check_graph_permission(ADMIN, local_storage.GRAPH_ID, "read", unowned=True)  # admin: no raise

    graph = await get_hypergraph(local_storage.GRAPH_ID, space_id=None)
    assert await filter_accessible_graphs(READER, [graph]) == []
    assert await filter_accessible_graphs(ADMIN, [graph]) == [graph]


# ── Retention ──────────────────────────────────────────────────────────────────

async def test_prune_deletes_only_records_older_than_the_cutoff(storage):
    now = datetime.now(UTC)
    await local_storage.write_records([
        event(feature="old", timestamp=(now - timedelta(days=40)).isoformat()),
        event(feature="new", timestamp=now.isoformat()),
    ])
    deleted = await local_storage.prune_older_than(now - timedelta(days=30))
    assert deleted == 1
    from hgai_module_storage.filters import HypernodeSearchFilters
    remaining = await get_storage().hypernodes.search(
        HypernodeSearchFilters(hypergraph_ids=[local_storage.GRAPH_ID]), skip=0, limit=10,
    )
    assert len(remaining) == 1 and remaining[0]["attributes"]["feature"] == "new"


async def test_prune_with_a_past_cutoff_deletes_nothing(storage):
    await local_storage.write_records([event()])
    deleted = await local_storage.prune_older_than(datetime.now(UTC) - timedelta(days=365))
    assert deleted == 0


async def test_prune_older_than_none_is_refused():
    with pytest.raises(AssertionError):
        await local_storage.prune_older_than(None)


@pytest.mark.parametrize("days, expect_none", [(0, True), (-1, True), (30, False)])
def test_retention_cutoff_disabled_only_at_zero_or_below(days, expect_none):
    assert (local_storage.retention_cutoff(days) is None) == expect_none


async def test_retention_sweep_prunes_on_its_own_schedule(storage, monkeypatch):
    monkeypatch.setattr(local_storage, "_RETENTION_INTERVAL_SECONDS", 0.01)
    now = datetime.now(UTC)
    await local_storage.write_records([event(timestamp=(now - timedelta(days=40)).isoformat())])

    class Settings:
        telemetry_enabled = True
        telemetry_local_retention_days = 30

    local_storage.start_retention_scheduler(Settings())
    try:
        for _ in range(200):
            from hgai_module_storage.filters import HypernodeSearchFilters
            remaining = await get_storage().hypernodes.search(
                HypernodeSearchFilters(hypergraph_ids=[local_storage.GRAPH_ID]), skip=0, limit=10,
            )
            if not remaining:
                break
            await asyncio.sleep(0.02)
        assert remaining == []
    finally:
        local_storage.stop_retention_scheduler()


def test_retention_scheduler_is_a_noop_when_disabled_or_retention_is_zero():
    class Off:
        telemetry_enabled = False
        telemetry_local_retention_days = 30

    class ZeroRetention:
        telemetry_enabled = True
        telemetry_local_retention_days = 0

    for settings in (Off(), ZeroRetention()):
        local_storage.start_retention_scheduler(settings)
        assert local_storage._retention_task is None
    local_storage.stop_retention_scheduler()  # must not raise with nothing running


# ── Exporter selection / composition ──────────────────────────────────────────

def make_settings(**overrides):
    from hgai.config import Settings
    defaults = dict(secret_key="s", telemetry_enabled=True, telemetry_endpoint=None)
    defaults.update(overrides)
    return Settings(**defaults)


def test_select_exporter_uses_local_storage_alone_with_no_endpoint():
    assert isinstance(select_exporter(make_settings()), LocalHypergraphExporter)


def test_select_exporter_uses_http_alone_by_default_with_an_endpoint():
    exp = select_exporter(make_settings(telemetry_endpoint="https://telemetry.hypergra.ai/report"))
    assert isinstance(exp, HTTPExporter)


def test_select_exporter_uses_both_when_local_enabled_is_set_with_an_endpoint():
    exp = select_exporter(make_settings(
        telemetry_endpoint="https://telemetry.hypergra.ai/report", telemetry_local_enabled=True,
    ))
    assert isinstance(exp, CompositeExporter)
    kinds = {type(e) for e in exp._exporters}
    assert kinds == {HTTPExporter, LocalHypergraphExporter}


async def test_composite_exporter_one_destination_failing_does_not_block_the_other(storage):
    calls = []

    class FailingExporter:
        async def export(self, records):
            calls.append("failing")
            raise RuntimeError("http is down")

    composite = CompositeExporter([FailingExporter(), LocalHypergraphExporter()])
    await composite.export([event()])  # must not raise — the local write still happened
    from hgai_module_storage.filters import HypernodeSearchFilters
    docs = await get_storage().hypernodes.search(
        HypernodeSearchFilters(hypergraph_ids=[local_storage.GRAPH_ID]), skip=0, limit=10,
    )
    assert len(docs) == 1 and calls == ["failing"]


async def test_composite_exporter_raises_only_when_every_destination_fails():
    class AlwaysFails:
        async def export(self, records):
            raise RuntimeError("nope")

    composite = CompositeExporter([AlwaysFails(), AlwaysFails()])
    with pytest.raises(RuntimeError):
        await composite.export([event()])
