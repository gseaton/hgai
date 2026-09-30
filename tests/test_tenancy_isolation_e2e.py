"""Multi-tenancy Phase 6: end-to-end isolation through the real ASGI app.

Phases 2 to 5 test the pieces by calling functions directly. This suite goes
through HTTP (real routing, real dependencies, real status codes), with real tokens
and a real mongod, and generates its checks from the app's own route table so a
new route cannot silently skip the tenant boundary.

World: Alpha (alice user, aadmin tenant admin) and Bravo (bob user), plus a system
admin. Bravo owns an unowned graph with a node and an edge, a space with a graph,
a note, a media file and a saved query.
"""

import re

import httpx
import pytest

from hgai.core import engine, notes, parameterized_queries, space_engine
from hgai.core.auth import create_access_token
from hgai.db.storage import get_storage
from hgai.models.hyperedge import HyperedgeCreate
from hgai.models.hypergraph import HypergraphCreate
from hgai.models.hypernode import HypernodeCreate
from hgai.models.note import NoteCreate
from hgai.models.parameterized_query import ParameterizedQueryCreate
from hgai.models.space import SpaceCreate
from tests.test_tenancy_phase1 import db  # noqa: F401  (fixture)
from tests.test_tenancy_phase2 import tenancy_on, world  # noqa: F401
from tests.test_tenancy_phase3 import _put
from tests.test_tenancy_phase4 import _dep_names, _routes

_APP = None


def app():
    global _APP
    if _APP is None:
        from hgai.main import create_app
        _APP = create_app()
    return _APP


def token(username, roles):
    return create_access_token(username, roles)[0]


TOKENS = {
    "alice": lambda: token("alice", ["user"]),
    "aadmin": lambda: token("aadmin", ["tenant_admin"]),
    "bob": lambda: token("bob", ["user"]),
    "root": lambda: token("root", ["admin"]),
}


@pytest.fixture
async def e2e(world):  # noqa: F811
    """Bravo's resources, plus an HTTP client that can act as any of the four accounts."""
    await engine.create_hypernode("b-g", HypernodeCreate(id="bn1", label="n", type="T"), "bob")
    await engine.create_hypernode("b-g", HypernodeCreate(id="bn2", label="n2", type="T"), "bob")
    await engine.create_hyperedge("b-g", HyperedgeCreate(
        id="be1", relation="r", members=[{"node_id": "bn1"}, {"node_id": "bn2"}]), "bob")
    note = await notes.create_note(NoteCreate(label="bravo note", scope="public"), "bob")
    media = await _put("bob", "Bravo", data=b"bravo bytes")
    pq = await parameterized_queries.create_parameterized_query(
        ParameterizedQueryCreate(name="q", label="Q", shql="shql:\n  from: b-g\n  where: []\n"), "bob")
    ids = {"note": note.id, "media": media.id, "pq": pq.id}

    transport = httpx.ASGITransport(app=app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async def call(who, method, path, **kw):
            headers = {"Authorization": f"Bearer {TOKENS[who]()}"}
            return await client.request(method, f"/api/v1{path}", headers=headers, **kw)
        yield call, ids


# ── Every graph- and space-addressed route, generated from the route table ────

_PARAMS = {
    "{graph_id}": "b-g", "{space_id}": "b-s", "{node_id:path}": "bn1", "{edge_id:path}": "be1",
    "{username}": "bob", "{media_path}": "x",
}


def _bravo_url(path):
    url = path[len("/api/v1"):]
    space_graph = "{space_id}" in url
    for key, value in _PARAMS.items():
        if key == "{graph_id}" and space_graph:
            value = "b-sg"            # inside a space, the graph is the space's graph
        url = url.replace(key, value)
    return url


def _graph_space_routes():
    out = []
    for path, r in _routes():
        if "{graph_id" in path or "{space_id" in path:
            for method in sorted(r.methods - {"HEAD", "OPTIONS"}):
                out.append((method, path, r))
    return out


def test_the_route_table_is_large_enough_to_mean_something():
    assert len(_graph_space_routes()) >= 45


@pytest.mark.parametrize("who", ["alice", "aadmin"])
async def test_every_graph_and_space_route_is_not_found_across_tenants(e2e, who):
    call, _ = e2e
    failures = []
    for method, path, route in _graph_space_routes():
        url = _bravo_url(path)
        names = _dep_names(route.dependant)
        admin_only = any("require_system_admin" in n or "require_tenant_admin" in n for n in names)
        resp = await call(who, method, url, json={"role": "member", "username": "bob"} if method in ("POST", "PUT", "PATCH") else None)
        expected = {404}
        if admin_only and who == "alice":
            expected = {403}          # a plain user is refused before tenancy is even asked
        if resp.status_code not in expected:
            failures.append(f"{who} {method} {url} -> {resp.status_code} (wanted {sorted(expected)})")
    assert failures == []


async def test_control_the_owning_tenant_reaches_the_same_routes(e2e):
    call, _ = e2e
    for url in ("/graphs/b-g", "/graphs/b-g/stats", "/graphs/b-g/nodes", "/graphs/b-g/nodes/bn1",
                "/graphs/b-g/edges/be1", "/spaces/b-s", "/spaces/b-s/members", "/spaces/b-s/graphs/b-sg"):
        assert (await call("bob", "GET", url)).status_code == 200, url
    assert (await call("root", "GET", "/graphs/b-g/nodes/bn1")).status_code == 200   # system admin


# ── Resources addressed by their own id ──────────────────────────────────────

async def test_notes_media_and_queries_are_not_found_across_tenants(e2e):
    call, ids = e2e
    n, m, q = ids["note"], ids["media"], ids["pq"]
    attempts = [
        ("GET", f"/notes/{n}", None), ("PUT", f"/notes/{n}", {"label": "x"}), ("DELETE", f"/notes/{n}", None),
        ("GET", f"/notes/{n}/share", None), ("PUT", f"/notes/{n}/scope", {"scope": "private"}),
        ("POST", f"/notes/{n}/share", {"username": "alice"}),
        ("GET", f"/media/{m}", None), ("PUT", f"/media/{m}", {"label": "x"}), ("DELETE", f"/media/{m}", None),
        ("GET", f"/parameterized-queries/{q}", None), ("PUT", f"/parameterized-queries/{q}", {"label": "x"}),
        ("DELETE", f"/parameterized-queries/{q}", None),
        ("POST", f"/parameterized-queries/{q}/execute", {"values": {}}),
    ]
    for who in ("alice", "aadmin"):
        for method, url, body in attempts:
            resp = await call(who, method, url, json=body)
            assert resp.status_code == 404, f"{who} {method} {url} -> {resp.status_code}"
    for method, url, body in attempts[:1] + attempts[6:7] + attempts[9:10]:
        assert (await call("bob", method, url, json=body)).status_code == 200, url   # controls


async def test_tenant_and_account_routes(e2e):
    call, _ = e2e
    assert (await call("alice", "GET", "/tenants/bravo")).status_code == 404
    assert (await call("aadmin", "GET", "/tenants/bravo")).status_code == 404
    assert (await call("alice", "GET", "/tenants/Alpha")).status_code == 200
    for method in ("PUT", "DELETE"):
        assert (await call("aadmin", method, "/tenants/Alpha", json={"label": "x"})).status_code == 403
    assert (await call("aadmin", "POST", "/tenants", json={"id": "x", "label": "x"})).status_code == 403
    assert (await call("alice", "GET", "/accounts")).status_code == 403
    for who in ("aadmin",):
        for method in ("GET", "PUT", "DELETE"):
            assert (await call(who, method, "/accounts/bob", json={"description": "x"} if method == "PUT" else None)
                    ).status_code == 404, method
        assert (await call(who, "GET", "/accounts/root")).status_code == 404       # system account
    created = await call("aadmin", "POST", "/accounts",
                         json={"username": "x1", "password": "secret1", "tenant_id": "Bravo"})
    assert created.status_code == 403
    sneaky = await call("aadmin", "POST", "/accounts", json={"username": "x2", "password": "secret1", "roles": ["admin"]})
    assert sneaky.status_code == 403


# ── Every list endpoint ──────────────────────────────────────────────────────

def _ids(resp, key="id"):
    assert resp.status_code == 200, resp.text
    body = resp.json()
    return {i[key] for i in body["items"]}


async def test_list_endpoints_return_only_the_callers_tenant(e2e):
    call, ids = e2e
    # what Bravo owns, as bob sees it
    assert "b-g" in _ids(await call("bob", "GET", "/graphs"))
    assert ids["note"] in _ids(await call("bob", "GET", "/notes"))
    assert ids["media"] in _ids(await call("bob", "GET", "/media"))
    assert ids["pq"] in _ids(await call("bob", "GET", "/parameterized-queries"))
    # Alpha never sees it
    for who in ("alice", "aadmin"):
        graphs = _ids(await call(who, "GET", "/graphs?limit=500"))
        assert graphs and graphs.isdisjoint({"b-g", "b-sg", "sys-g"})
        assert _ids(await call(who, "GET", "/notes")).isdisjoint({ids["note"]})
        assert _ids(await call(who, "GET", "/media")).isdisjoint({ids["media"]})
        assert _ids(await call(who, "GET", "/parameterized-queries")).isdisjoint({ids["pq"]})
        assert "b-s" not in _ids(await call(who, "GET", "/spaces"))
    assert "bravo" not in _ids(await call("aadmin", "GET", "/tenants"))
    usernames = _ids(await call("aadmin", "GET", "/accounts"), key="username")
    assert usernames == {"alice", "aadmin"}


async def test_list_totals_and_paging_stay_inside_the_tenant(e2e):
    call, _ = e2e
    body = (await call("alice", "GET", "/graphs?limit=1&skip=0")).json()
    assert body["total"] == 2 and len(body["items"]) == 1        # not inflated by other tenants' graphs
    body = (await call("alice", "GET", "/graphs?limit=1&skip=1")).json()
    assert len(body["items"]) == 1 and body["items"][0]["id"] in {"a-g", "a-sg"}


async def test_system_admin_sees_everything_and_can_scope_to_a_tenant(e2e):
    call, ids = e2e
    everything = _ids(await call("root", "GET", "/graphs?limit=500"))
    assert {"a-g", "b-g", "a-sg", "b-sg"} <= everything
    bravo = _ids(await call("root", "GET", "/graphs?limit=500&tenant_id=Bravo"))
    assert bravo == {"b-g", "b-sg"}
    assert _ids(await call("root", "GET", "/spaces?tenant_id=Bravo")) == {"b-s"}
    assert _ids(await call("root", "GET", "/accounts?tenant_id=Bravo"), key="username") == {"bob"}
    assert ids["note"] in _ids(await call("root", "GET", "/notes"))
    # acting in a tenant: a system admin can create a graph for it
    made = await call("root", "POST", "/graphs", json={"id": "for-bravo", "label": "x", "tenant_id": "Bravo"})
    assert made.status_code == 201 and made.json()["tenant_id"] == "Bravo"
    assert "for-bravo" in _ids(await call("bob", "GET", "/graphs?limit=500"))
    assert "for-bravo" not in _ids(await call("alice", "GET", "/graphs?limit=500"))


# ── Writes land in the right tenant ──────────────────────────────────────────

async def test_created_records_belong_to_the_creators_tenant(e2e):
    call, _ = e2e
    g = await call("alice", "POST", "/graphs", json={"id": "alice-new", "label": "x", "tenant_id": "Bravo"})
    assert g.status_code == 201 and g.json()["tenant_id"] == "Alpha"      # asking for another tenant is ignored
    s = await call("alice", "POST", "/spaces", json={"id": "alice-space", "label": "x"})
    assert s.status_code == 201 and s.json()["tenant_id"] == "Alpha"
    n = await call("alice", "POST", "/notes", json={"label": "mine"})
    assert n.json()["tenant_id"] == "Alpha"
    assert (await call("bob", "GET", f"/notes/{n.json()['id']}")).status_code == 404
    escaped = await call("alice", "POST", "/graphs", json={"id": "escape", "label": "x", "space_id": "b-s"})
    assert escaped.status_code == 201 and escaped.json()["space_id"] is None   # cannot be placed in Bravo's space


async def test_a_logical_graph_cannot_reach_across(e2e):
    call, _ = e2e
    r = await call("alice", "POST", "/graphs", json={"id": "lg", "label": "x", "type": "logical", "composition": ["b-g"]})
    assert r.status_code == 400


async def test_shql_over_http_is_tenant_scoped(e2e):
    call, _ = e2e
    q = "shql:\n  from: b-g\n  where: []\n"
    assert (await call("bob", "POST", "/shql/query", json={"shql": q})).status_code == 200
    assert (await call("alice", "POST", "/shql/query", json={"shql": q})).status_code == 403
    assert (await call("aadmin", "POST", "/shql/query", json={"shql": q})).status_code == 403
    both = "shql:\n  from: [a-g, b-g]\n  where: []\n"
    assert (await call("alice", "POST", "/shql/query", json={"shql": both})).status_code == 403
    assert (await call("alice", "POST", "/shql/query", json={"shql": "shql:\n  from: a-g\n  where: []\n"})).status_code == 200


# ── Tenant status and the flag ───────────────────────────────────────────────

async def test_a_suspended_tenant_gets_401_over_http(e2e):
    call, _ = e2e
    assert (await call("alice", "GET", "/graphs")).status_code == 200
    assert (await call("root", "PUT", "/tenants/Alpha", json={"status": "suspended"})).status_code == 200
    assert (await call("alice", "GET", "/graphs")).status_code == 401
    assert (await call("aadmin", "GET", "/accounts")).status_code == 401
    assert (await call("bob", "GET", "/graphs")).status_code == 200            # other tenants unaffected
    assert (await call("root", "GET", "/graphs")).status_code == 200
    assert (await call("root", "PUT", "/tenants/Alpha", json={"status": "active"})).status_code == 200
    assert (await call("alice", "GET", "/graphs")).status_code == 200


async def test_with_the_flag_off_nothing_changes_for_ordinary_routes(e2e, monkeypatch):
    from tests.test_tenancy_phase2 import set_tenancy
    call, ids = e2e
    set_tenancy(monkeypatch, False)
    assert (await call("alice", "GET", "/auth/me")).json()["multitenancy_enabled"] is False
    assert (await call("aadmin", "GET", "/accounts")).status_code == 403       # tenant admin powers need the flag
    assert (await call("root", "GET", "/accounts")).status_code == 200
    # and the wildcard account really does reach it (the boundary is what stops it when the flag is on)
    assert (await call("alice", "GET", "/graphs/b-g")).status_code == 200


async def test_ids_are_unique_server_wide_so_a_clash_is_a_409_not_a_shared_graph(e2e):
    call, _ = e2e
    # Documented trade-off: nodes and edges are keyed by graph id, so ids cannot repeat across tenants.
    clash = await call("bob", "POST", "/graphs", json={"id": "a-g", "label": "x"})
    assert clash.status_code == 409
    space_clash = await call("bob", "POST", "/spaces", json={"id": "a-s", "label": "x"})
    assert space_clash.status_code == 409
    # and Alpha's graph is untouched
    assert (await call("alice", "GET", "/graphs/a-g")).json()["tenant_id"] == "Alpha"
