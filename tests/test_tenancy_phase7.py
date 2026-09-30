"""Multi-tenancy Phase 7: system auditor, per-tenant quotas, tenant-scoped API keys.

Real mongod, real ASGI app, real tokens (same world as the isolation suite: Alpha has
alice and aadmin, Bravo has bob and the b-* graph/space; `root` is a system admin).
"""

from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import HTTPException

from hgai.core import auth, engine, tenant_engine
from hgai.core.auth import create_access_token
from hgai.models.account import AccountInDB, AccountPermissions, SystemRole
from hgai.models.hypernode import HypernodeCreate
from tests.test_tenancy_isolation_e2e import TOKENS, app
from tests.test_tenancy_phase1 import db  # noqa: F401  (fixture)
from tests.test_tenancy_phase2 import set_tenancy, tenancy_on, world  # noqa: F401
from hgai_module_mcp.server import mcp, reset_caller, set_caller

AUDITOR = AccountInDB(
    username="auditor", roles=["readonly"], system_role="system_auditor", password_hash="",
    status="active", permissions=AccountPermissions(graphs=["*"], operations=["read", "query", "write", "delete"]),
)


@pytest.fixture(autouse=True)
def _fresh_quota_cache():
    tenant_engine.clear_quota_cache()
    yield
    tenant_engine.clear_quota_cache()


@pytest.fixture
async def http(world):  # noqa: F811
    await world["accounts"].insert_one({
        "username": "auditor", "roles": ["readonly"], "system_role": "system_auditor", "password_hash": "",
        "status": "active", "permissions": {"graphs": ["*"], "operations": ["read", "query", "write", "delete"]},
    })
    await engine.create_hypernode("b-g", HypernodeCreate(id="bn1", label="n", type="T"), "bob")
    tokens = dict(TOKENS, auditor=lambda: create_access_token("auditor", ["readonly"])[0])

    transport = httpx.ASGITransport(app=app())
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        async def call(who, method, path, **kw):
            return await client.request(method, f"/api/v1{path}", headers={"Authorization": f"Bearer {tokens[who]()}"}, **kw)

        async def raw(bearer, method, path, **kw):
            return await client.request(method, f"/api/v1{path}", headers={"Authorization": f"Bearer {bearer}"}, **kw)
        yield call, raw


def ids(resp, key="id"):
    assert resp.status_code == 200, resp.text
    return {i[key] for i in resp.json()["items"]}


# ══ System auditor ════════════════════════════════════════════════════════════

async def test_auditor_reads_across_every_tenant(http):
    call, _ = http
    assert {"a-g", "b-g", "a-sg", "b-sg"} <= ids(await call("auditor", "GET", "/graphs?limit=500"))
    assert {"a-s", "b-s"} <= ids(await call("auditor", "GET", "/spaces"))
    assert {"alice", "bob", "root"} <= ids(await call("auditor", "GET", "/accounts"), key="username")
    assert {"Alpha", "Bravo"} <= ids(await call("auditor", "GET", "/tenants"))
    for url in ("/graphs/b-g", "/graphs/b-g/nodes/bn1", "/graphs/b-g/stats", "/spaces/b-s",
                "/spaces/b-s/graphs/b-sg", "/tenants/Bravo", "/accounts/bob", "/accounts/bob/spaces"):
        assert (await call("auditor", "GET", url)).status_code == 200, url
    assert ids(await call("auditor", "GET", "/graphs?limit=500&tenant_id=Bravo")) == {"b-g", "b-sg"}


async def test_auditor_can_query_and_export(http):
    call, _ = http
    for gid in ("a-g", "b-g"):
        q = await call("auditor", "POST", "/shql/query", json={"shql": f"shql:\n  from: {gid}\n  where: []\n"})
        assert q.status_code == 200, q.text
    assert (await call("auditor", "POST", "/graphs/b-g/export")).status_code == 200
    assert (await call("auditor", "GET", "/graphs/b-g/export")).status_code == 200


async def test_auditor_cannot_change_anything(http):
    call, _ = http
    node = {"id": "x", "label": "x", "type": "T"}
    attempts = [
        ("POST", "/graphs", {"id": "new", "label": "x"}), ("PUT", "/graphs/b-g", {"label": "x"}),
        ("DELETE", "/graphs/b-g", None), ("POST", "/graphs/b-g/nodes", node),
        ("PUT", "/graphs/b-g/nodes/bn1", {"label": "x"}), ("DELETE", "/graphs/b-g/nodes/bn1", None),
        ("POST", "/graphs/b-g/import", {}), ("POST", "/graphs/b-g/infer/project", {}),
        ("POST", "/spaces", {"id": "s", "label": "x"}), ("PUT", "/spaces/b-s", {"label": "x"}),
        ("DELETE", "/spaces/b-s", None), ("POST", "/spaces/b-s/members", {"username": "alice"}),
        ("POST", "/spaces/b-s/graphs", {"id": "g", "label": "x"}),
        ("POST", "/accounts", {"username": "n", "password": "secret1"}), ("PUT", "/accounts/bob", {"description": "x"}),
        ("DELETE", "/accounts/bob", None), ("POST", "/tenants", {"id": "t", "label": "x"}),
        ("PUT", "/tenants/Bravo", {"label": "x"}), ("DELETE", "/tenants/Bravo", None),
        ("POST", "/api-keys", {"label": "k", "tenant_id": "Alpha"}),
    ]
    for method, url, body in attempts:
        resp = await call("auditor", method, url, json=body)
        assert resp.status_code == 403, f"{method} {url} -> {resp.status_code}"
    assert (await call("root", "GET", "/graphs/b-g")).json()["label"] == "b"   # nothing changed


async def test_auditor_cannot_reach_users_own_data(http):
    call, _ = http
    for url in ("/notes", "/media", "/parameterized-queries"):
        assert (await call("auditor", "GET", url)).status_code == 403, url
    assert (await call("auditor", "POST", "/notes", json={"label": "x"})).status_code == 403


async def test_auditor_operations_ignore_the_accounts_own_permissions(http):
    # The account above even lists write and delete; a system auditor is read-only regardless.
    assert await auth.can_perform(AUDITOR, "read", graph_id="b-g", unowned=True)
    assert await auth.can_perform(AUDITOR, "query", graph_id="b-g", unowned=True)
    for op in ("write", "delete", "import", "admin"):
        assert not await auth.can_perform(AUDITOR, op, graph_id="b-g", unowned=True)
    assert await auth.can_access_graph(AUDITOR, "b-g", unowned=True)
    with pytest.raises(auth.PermissionDeniedError):
        await auth.check_graph_permission(AUDITOR, "b-g", "write", unowned=True)
    await auth.check_space_role(AUDITOR, "b-s", "viewer")
    with pytest.raises(auth.PermissionDeniedError):
        await auth.check_space_role(AUDITOR, "b-s", "member")
    with pytest.raises(auth.PermissionDeniedError):
        auth.require_admin_role(AUDITOR, "meshes")
    assert not auth.is_system_admin(AUDITOR) and auth.sees_all_tenants(AUDITOR)


async def test_auditor_over_mcp(http):
    async def call_tool(tool, args):
        token = set_caller(AUDITOR)
        try:
            out = await mcp.call_tool(tool, args)
        finally:
            reset_caller(token)
        content = out[0] if isinstance(out, tuple) else out
        return content[0].text

    import json
    assert json.loads(await call_tool("hgai_hypergraph_get", {"graph_id": "b-g"}))["id"] == "b-g"
    graphs = {g["id"] for g in json.loads(await call_tool("hgai_hypergraph_list", {}))["graphs"]}
    assert {"a-g", "b-g"} <= graphs
    for tool, args in (("hgai_hypergraph_create", {"id": "x", "label": "x"}),
                       ("hgai_space_create", {"id": "x", "label": "x"}),
                       ("hgai_hypernode_create", {"graph_id": "b-g", "id": "x", "label": "x", "type": "T"}),
                       ("hgai_hypernode_delete", {"graph_id": "b-g", "node_id": "bn1"}),
                       ("hgai_media_upload", {"content_base64": "eA==", "content_type": "text/plain"}),
                       ("hgai_mesh_list", {})):
        assert json.loads(await call_tool(tool, args)).get("type") == "PermissionDenied", tool


async def test_a_system_admin_creates_an_auditor_and_a_tenant_admin_cannot(http):
    call, _ = http
    made = await call("root", "POST", "/accounts", json={
        "username": "aud2", "password": "secret1", "roles": ["readonly"], "system_role": "system_auditor"})
    assert made.status_code == 201
    assert made.json()["system_role"] == "system_auditor" and made.json()["tenant_id"] is None
    refused = await call("aadmin", "POST", "/accounts", json={
        "username": "aud3", "password": "secret1", "system_role": "system_auditor"})
    assert refused.status_code == 403


# ══ Quotas ════════════════════════════════════════════════════════════════════

async def set_quotas(call, tenant, **quotas):
    resp = await call("root", "PUT", f"/tenants/{tenant}", json={"settings": {"quotas": quotas}})
    assert resp.status_code == 200, resp.text
    return resp


async def test_quota_settings_are_validated(http):
    call, _ = http
    for bad in ({"max_graphs": -1}, {"max_widgets": 3}, {"max_graphs": "many"}):
        r = await call("root", "PUT", "/tenants/Alpha", json={"settings": {"quotas": bad}})
        assert r.status_code == 422, bad
    ok = await set_quotas(call, "Alpha", max_graphs=5)
    assert ok.json()["settings"]["quotas"] == {"max_graphs": 5}


async def test_graph_quota(http):
    call, _ = http
    await set_quotas(call, "Alpha", max_graphs=3)            # Alpha already has a-g and a-sg
    assert (await call("alice", "POST", "/graphs", json={"id": "g3", "label": "x"})).status_code == 201
    over = await call("alice", "POST", "/graphs", json={"id": "g4", "label": "x"})
    assert over.status_code == 409 and "limit of 3 graphs" in over.json()["detail"]
    inside_space = await call("alice", "POST", "/spaces/a-s/graphs", json={"id": "g5", "label": "x"})
    assert inside_space.status_code == 409                   # graphs in spaces count too
    assert (await call("bob", "POST", "/graphs", json={"id": "b3", "label": "x"})).status_code == 201   # Bravo unlimited


async def test_space_and_account_quotas(http):
    call, _ = http
    await set_quotas(call, "Alpha", max_spaces=2, max_accounts=3)
    assert (await call("alice", "POST", "/spaces", json={"id": "s2", "label": "x"})).status_code == 201
    assert (await call("alice", "POST", "/spaces", json={"id": "s3", "label": "x"})).status_code == 409
    assert (await call("aadmin", "POST", "/accounts", json={"username": "n1", "password": "secret1"})).status_code == 201
    over = await call("aadmin", "POST", "/accounts", json={"username": "n2", "password": "secret1"})
    assert over.status_code == 409 and "accounts" in over.json()["detail"]
    # a system account is not a tenant's account
    assert (await call("root", "POST", "/accounts", json={"username": "r2", "password": "secret1", "roles": ["admin"]})
            ).status_code == 201


async def test_node_and_edge_quotas(http):
    call, _ = http
    await set_quotas(call, "Bravo", max_nodes=3, max_edges=1)         # Bravo has one node (bn1)
    node = lambda i: {"id": i, "label": i, "type": "T"}               # noqa: E731
    assert (await call("root", "POST", "/graphs/b-g/nodes", json=node("n2"))).status_code == 201
    assert (await call("root", "POST", "/graphs/b-g/nodes", json=node("n3"))).status_code == 201
    over = await call("root", "POST", "/graphs/b-g/nodes", json=node("n4"))
    assert over.status_code == 409 and "nodes" in over.json()["detail"]
    edge = lambda i: {"id": i, "relation": "r", "members": [{"node_id": "n2"}, {"node_id": "n3"}]}   # noqa: E731
    assert (await call("root", "POST", "/graphs/b-g/edges", json=edge("e1"))).status_code == 201
    assert (await call("root", "POST", "/graphs/b-g/edges", json=edge("e2"))).status_code == 409


async def test_quota_change_takes_effect_and_can_be_removed(http):
    call, _ = http
    await set_quotas(call, "Alpha", max_graphs=2)
    assert (await call("alice", "POST", "/graphs", json={"id": "q1", "label": "x"})).status_code == 409
    await set_quotas(call, "Alpha", max_graphs=10)
    assert (await call("alice", "POST", "/graphs", json={"id": "q1", "label": "x"})).status_code == 201
    await call("root", "PUT", "/tenants/Alpha", json={"settings": {}})
    assert (await call("alice", "POST", "/graphs", json={"id": "q2", "label": "x"})).status_code == 201


async def test_usage_endpoint(http):
    call, _ = http
    await set_quotas(call, "Alpha", max_graphs=9)
    body = (await call("alice", "GET", "/tenants/Alpha/usage")).json()
    assert body["usage"]["graphs"] == 2 and body["usage"]["accounts"] == 2 and body["usage"]["spaces"] == 1
    assert body["quotas"] == {"max_graphs": 9}
    assert (await call("bob", "GET", "/tenants/Alpha/usage")).status_code == 404
    assert (await call("root", "GET", "/tenants/Alpha/usage")).status_code == 200
    assert (await call("auditor", "GET", "/tenants/Alpha/usage")).status_code == 200


async def test_quotas_are_ignored_when_tenancy_is_off(http, monkeypatch):
    call, _ = http
    await set_quotas(call, "Alpha", max_graphs=1)
    set_tenancy(monkeypatch, False)
    assert (await call("root", "POST", "/graphs", json={"id": "free", "label": "x"})).status_code == 201


async def test_quota_error_is_reported_over_mcp(http):
    import json
    await set_quotas(http[0], "Alpha", max_graphs=2)
    token = set_caller(AccountInDB(username="alice", roles=["user"], tenant_id="Alpha", password_hash="",
                                   permissions=AccountPermissions(graphs=["*"], operations=["read"])))
    try:
        out = await mcp.call_tool("hgai_hypergraph_create", {"id": "mcp-over", "label": "x"})
    finally:
        reset_caller(token)
    content = out[0] if isinstance(out, tuple) else out
    assert "limit of 2 graphs" in json.loads(content[0].text)["error"]


# ══ Tenant-scoped API keys ═══════════════════════════════════════════════════

async def issue(call, who="root", **body):
    body.setdefault("label", "ci")
    resp = await call(who, "POST", "/api-keys", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_a_key_is_shown_once_and_never_listed_with_its_secret(http):
    call, _ = http
    made = await issue(call, tenant_id="Alpha", operations=["read", "query"])
    assert made["key"].startswith("hgai_") and made["key_prefix"] == made["key"][:11]
    assert "key_hash" not in made
    listed = (await call("root", "GET", "/api-keys")).json()["items"]
    assert [k["id"] for k in listed] == [made["id"]]
    assert all("key" not in k and "key_hash" not in k for k in listed)


async def test_a_key_acts_inside_its_tenant_only(http):
    call, raw = http
    key = (await issue(call, tenant_id="Alpha", operations=["read", "query", "write"]))["key"]
    assert ids(await raw(key, "GET", "/graphs?limit=500")) == {"a-g"}         # a-sg needs space membership
    assert (await raw(key, "GET", "/graphs/a-g")).status_code == 200
    assert (await raw(key, "GET", "/graphs/b-g")).status_code == 404          # other tenant
    assert (await raw(key, "POST", "/shql/query", json={"shql": "shql:\n  from: b-g\n  where: []\n"})).status_code == 403
    made = await raw(key, "POST", "/graphs", json={"id": "key-graph", "label": "x", "tenant_id": "Bravo"})
    assert made.status_code == 201 and made.json()["tenant_id"] == "Alpha"
    note = await raw(key, "POST", "/notes", json={"label": "from a key"})
    assert note.json()["tenant_id"] == "Alpha"                               # owned data follows the key's tenant
    assert (await call("bob", "GET", f"/notes/{note.json()['id']}")).status_code == 404


async def test_a_keys_operations_are_limited(http):
    call, raw = http
    read_only = (await issue(call, tenant_id="Alpha", operations=["read", "query"]))["key"]
    writer = (await issue(call, tenant_id="Alpha", operations=["read", "write"]))["key"]
    assert (await raw(read_only, "PUT", "/graphs/a-g", json={"label": "x"})).status_code == 403
    assert (await raw(writer, "PUT", "/graphs/a-g", json={"label": "x"})).status_code == 200
    assert (await raw(writer, "DELETE", "/graphs/a-g")).status_code == 403


async def test_a_key_cannot_administer(http):
    call, raw = http
    key = (await issue(call, tenant_id="Alpha", operations=["read", "query", "write", "delete"]))["key"]
    for method, url, body in (("GET", "/api-keys", None), ("POST", "/api-keys", {"label": "x"}),
                              ("GET", "/accounts", None), ("POST", "/tenants", {"id": "x", "label": "x"}),
                              ("GET", "/meshes", None)):
        assert (await raw(key, method, url, json=body)).status_code == 403, url


async def test_revoked_expired_and_unknown_keys_are_refused(http):
    call, raw = http
    live = await issue(call, tenant_id="Alpha")
    assert (await raw(live["key"], "GET", "/graphs")).status_code == 200
    assert (await call("root", "DELETE", f"/api-keys/{live['id']}")).status_code == 204
    assert (await raw(live["key"], "GET", "/graphs")).status_code == 401
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    expired = await issue(call, tenant_id="Alpha", expires_at=past)
    assert (await raw(expired["key"], "GET", "/graphs")).status_code == 401
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    fine = await issue(call, tenant_id="Alpha", expires_at=future)
    assert (await raw(fine["key"], "GET", "/graphs")).status_code == 200
    assert (await raw("hgai_not-a-real-key", "GET", "/graphs")).status_code == 401


async def test_key_use_is_recorded(http, db):
    call, raw = http
    made = await issue(call, tenant_id="Alpha")
    assert (await db["api_keys"].find_one({"id": made["id"]}))["last_used"] is None
    await raw(made["key"], "GET", "/graphs")
    assert (await db["api_keys"].find_one({"id": made["id"]}))["last_used"] is not None
    assert "key" not in (await db["api_keys"].find_one({"id": made["id"]}))     # the secret itself is never stored


async def test_suspending_the_tenant_stops_its_keys(http):
    call, raw = http
    key = (await issue(call, tenant_id="Alpha"))["key"]
    other = (await issue(call, tenant_id="Bravo"))["key"]
    await call("root", "PUT", "/tenants/Alpha", json={"status": "suspended"})
    assert (await raw(key, "GET", "/graphs")).status_code == 401
    assert (await raw(other, "GET", "/graphs")).status_code == 200


async def test_keys_need_tenancy_to_be_enforced(http, monkeypatch):
    call, raw = http
    key = (await issue(call, tenant_id="Alpha"))["key"]
    set_tenancy(monkeypatch, False)
    assert (await raw(key, "GET", "/graphs")).status_code == 401              # nothing would confine it
    assert (await call("root", "POST", "/api-keys", json={"label": "x", "tenant_id": "Alpha"})).status_code == 409


async def test_who_may_issue_which_keys(http):
    call, raw = http
    own = await issue(call, who="aadmin")                                      # tenant defaults to its own
    assert own["tenant_id"] == "Alpha"
    assert (await call("aadmin", "POST", "/api-keys", json={"label": "x", "tenant_id": "Bravo"})).status_code == 403
    assert (await call("alice", "POST", "/api-keys", json={"label": "x"})).status_code == 403
    assert (await call("root", "POST", "/api-keys", json={"label": "x"})).status_code == 400            # tenant required
    assert (await call("root", "POST", "/api-keys", json={"label": "x", "tenant_id": "Nope"})).status_code == 400
    assert (await call("root", "POST", "/api-keys", json={"label": "x", "tenant_id": "Alpha",
                                                          "operations": ["admin"]})).status_code == 422
    bravo = await issue(call, tenant_id="Bravo")
    mine = ids(await call("aadmin", "GET", "/api-keys"))
    assert own["id"] in mine and bravo["id"] not in mine
    assert (await call("aadmin", "DELETE", f"/api-keys/{bravo['id']}")).status_code == 404
    assert (await call("aadmin", "DELETE", f"/api-keys/{own['id']}")).status_code == 204
    assert bravo["id"] in ids(await call("root", "GET", "/api-keys"))


async def test_a_key_can_be_a_space_member_but_only_in_its_own_tenant(http):
    call, raw = http
    a = await issue(call, tenant_id="Alpha", operations=["read", "query"])
    b = await issue(call, tenant_id="Bravo", operations=["read", "query"])
    assert (await raw(a["key"], "GET", "/spaces/a-s/graphs/a-sg")).status_code == 403         # not a member yet
    added = await call("alice", "POST", "/spaces/a-s/members", json={"username": f"apikey:{a['id']}", "role": "viewer"})
    assert added.status_code == 201
    assert (await raw(a["key"], "GET", "/spaces/a-s/graphs/a-sg")).status_code == 200
    cross = await call("alice", "POST", "/spaces/a-s/members", json={"username": f"apikey:{b['id']}", "role": "viewer"})
    assert cross.status_code == 400


async def test_a_tenant_with_keys_cannot_be_deleted(http):
    call, _ = http
    await call("root", "POST", "/tenants", json={"id": "Temp", "label": "t"})
    key = await issue(call, tenant_id="Temp")
    blocked = await call("root", "DELETE", "/tenants/Temp")
    assert blocked.status_code == 409 and "api_keys" in blocked.json()["detail"]
    await call("root", "DELETE", f"/api-keys/{key['id']}")
    assert (await call("root", "DELETE", "/tenants/Temp")).status_code == 204


# ══ Shell and UI hooks ═══════════════════════════════════════════════════════

def _shell():
    from unittest.mock import MagicMock
    from shell.hgai_shell import HgaiClient, HgaiShell
    sh = HgaiShell()
    sh.client = MagicMock(spec=HgaiClient)
    sh.username, sh.server_url = "root", "http://x"
    return sh


def test_shell_lists_api_keys_and_usage():
    sh = _shell()
    sh.tenant_scope = "alpha"
    sh.client.list_api_keys.return_value = {"items": [{"id": "k1", "label": "ci", "tenant_id": "alpha",
                                                        "key_prefix": "hgai_abc", "operations": ["read"]}], "total": 1}
    sh.client.tenant_usage.return_value = {"usage": {"graphs": 2, "nodes": 7}, "quotas": {"max_graphs": 5}}
    sh.cmd_ls(["apikeys"])
    assert sh.client.list_api_keys.call_args.kwargs["tenant_id"] == "alpha"
    sh.cmd_ls(["usage"])                                   # falls back to the tenant scope
    sh.client.tenant_usage.assert_called_with("alpha")


def test_shell_creates_shows_the_secret_and_revokes(monkeypatch, capsys):
    sh = _shell()
    monkeypatch.setattr(sh, "_read_multiline", lambda *a, **k: "label: ci\ntenant_id: alpha\noperations: [read]")
    sh.client.create_api_key.return_value = {"id": "k1", "tenant_id": "alpha", "key": "hgai_SECRET"}
    sh.cmd_create(["apikey"])
    assert sh.client.create_api_key.call_args.args[0]["operations"] == ["read"]
    assert "hgai_SECRET" in capsys.readouterr().out
    monkeypatch.setattr("builtins.input", lambda *_: "y")
    sh.cmd_delete(["apikey", "k1"])
    sh.client.revoke_api_key.assert_called_with("k1")


def test_ui_has_system_role_and_quota_controls():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    html, js = (root / "ui/index.html").read_text(), (root / "ui/js/app.js").read_text()
    for marker in ('id="account-system-role"', 'id="tenant-quota-graphs"', 'id="tenant-quota-nodes"'):
        assert marker in html, marker
    assert "TENANT_QUOTA_KEYS" in js and "data.system_role = systemRole" in js


def test_ui_has_an_api_keys_screen():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    html, js, api = ((root / f).read_text() for f in ("ui/index.html", "ui/js/app.js", "ui/js/api.js"))
    for marker in ('data-screen="api-keys"', 'id="screen-api-keys"', 'id="modal-api-key"', 'id="api-key-secret"',
                   'id="btn-save-api-key"'):
        assert marker in html, marker
    for fn in ("loadApiKeys", "openApiKeyModal", "revokeApiKey"):
        assert f"function {fn}" in js, fn
    assert "'api-keys': loadApiKeys" in js
    for fn in ("listApiKeys", "createApiKey", "revokeApiKey", "getTenantUsage"):
        assert fn in api, fn
