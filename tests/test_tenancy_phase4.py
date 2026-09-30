"""Multi-tenancy Phase 4: SHQL, MCP, federation and the route inventory.

Real mongod and the two-tenant `world` of the Phase 2 tests. SHQL authorization,
the result cache, the MCP tools (which the agent-chat toolkit also calls, with the
account's own bearer token) and the REST route table are all checked for tenant
isolation.
"""

import json

import pytest
from fastapi import HTTPException

from hgai.api.routers import hypergraphs as graphs_r
from hgai.core import auth, engine
from hgai.models.hypergraph import HypergraphCreate
from hgai.models.hypernode import HypernodeCreate
from hgai_module_mcp.server import mcp, reset_caller, set_caller
from hgai_module_shql import engine as shql_engine
from hgai_module_shql.parser import SHQLPermissionError
from tests.test_tenancy_phase1 import db  # noqa: F401  (fixture)
from tests.test_tenancy_phase2 import ALICE, ALPHA_ADMIN, BOB, ROOT, acct, set_tenancy, tenancy_on, world  # noqa: F401
from tests.test_tenancy_phase3 import _put


def q(frm):
    return {"from": frm}


# ── SHQL ──────────────────────────────────────────────────────────────────────

async def test_shql_from_refs_respect_the_tenant_boundary(world):
    await shql_engine._authorize_query(q("a-g"), ALICE)
    await shql_engine._authorize_query(q("a-s/a-sg"), ALICE)                # member of a-s
    for frm in ("b-g", "b-s/b-sg", "sys-g", ["a-g", "b-g"], ["b-g", "a-g"]):
        with pytest.raises(SHQLPermissionError):
            await shql_engine._authorize_query(q(frm), ALICE)


async def test_shql_membership_and_wildcard_do_not_cross_tenants(world):
    from hgai.core import space_engine
    await space_engine.add_member("b-s", "alice", "owner")
    with pytest.raises(SHQLPermissionError):
        await shql_engine._authorize_query(q("b-s/b-sg"), ALICE)


async def test_shql_tenant_admin_and_system_admin(world):
    await shql_engine._authorize_query(q(["a-g", "a-s/a-sg"]), ALPHA_ADMIN)   # not a member of a-s
    with pytest.raises(SHQLPermissionError):
        await shql_engine._authorize_query(q("b-s/b-sg"), ALPHA_ADMIN)
    with pytest.raises(SHQLPermissionError, match="admin"):
        await shql_engine._authorize_query(q("m.srv.b-g"), ALPHA_ADMIN)        # federation: system admin only
    await shql_engine._authorize_query(q(["a-g", "b-g", "b-s/b-sg", "sys-g"]), ROOT)


async def test_shql_error_does_not_reveal_other_tenants_graphs(world):
    with pytest.raises(SHQLPermissionError) as cross:
        await shql_engine._authorize_query(q("b-g"), ALICE)
    assert "not permitted" not in str(cross.value)       # not the "exists but forbidden" wording


async def test_result_cache_is_not_served_across_tenants(world):
    await engine.create_hypernode("b-g", HypernodeCreate(id="secret", label="Bravo only", type="T"), "bob")
    text = "shql:\n  from: b-g\n  where: []\n"
    first = await shql_engine.execute_shql(text, account=BOB)
    assert first.items                                               # populates the cache
    with pytest.raises(SHQLPermissionError):
        await shql_engine.execute_shql(text, account=ALICE)           # authorized before the cache is read
    again = await shql_engine.execute_shql(text, account=ROOT)
    assert again.items


async def test_logical_graph_cannot_compose_another_tenants_graph(world):
    # A tenant account cannot create the reference...
    with pytest.raises(HTTPException) as e:
        await graphs_r.create_graph(
            HypergraphCreate(id="a-logical", label="x", type="logical", composition=["b-g"]), account=ALICE)
    assert e.value.status_code == 400
    # ...while composing its own tenant's graphs is fine.
    ok = await graphs_r.create_graph(
        HypergraphCreate(id="a-logical", label="x", type="logical", composition=["a-g"]), account=ALICE)
    assert ok.tenant_id == "Alpha"
    # A system admin can wire one up; querying it still requires every member.
    await engine.create_hypergraph(
        HypergraphCreate(id="mixed", label="x", type="logical", composition=["a-g", "b-g"], tenant_id="Alpha"), "root")
    with pytest.raises(SHQLPermissionError):
        await shql_engine._authorize_query(q("mixed"), ALICE)


async def test_composition_update_is_checked_too(world):
    from hgai.models.hypergraph import HypergraphUpdate
    with pytest.raises(HTTPException) as e:
        await graphs_r.update_graph("a-g", HypergraphUpdate(composition=["b-g"]), account=ALICE)
    assert e.value.status_code == 400


async def test_post_graphs_ignores_a_client_supplied_space_id(world):
    made = await graphs_r.create_graph(HypergraphCreate(id="sneak", label="x", space_id="b-s"), account=ALICE)
    assert made.space_id is None and made.tenant_id == "Alpha"      # not placed in Bravo's space


# ── MCP (the tools the agent-chat toolkit calls with the account's own token) ──

async def call(tool, args, caller):
    token = set_caller(caller)
    try:
        out = await mcp.call_tool(tool, args)
    finally:
        reset_caller(token)
    content = out[0] if isinstance(out, tuple) else out
    return content[0].text


def denied(text):
    try:
        return json.loads(text).get("type") == "PermissionDenied"
    except (ValueError, AttributeError):
        return False


GRAPH_TOOLS = [
    ("hgai_hypergraph_get", {}), ("hgai_hypergraph_stats", {}), ("hgai_hypernode_list", {}),
    ("hgai_hypernode_get", {"node_id": "n"}), ("hgai_hypernode_create", {"id": "n", "label": "n", "type": "T"}),
    ("hgai_hypernode_update", {"node_id": "n", "label": "x"}), ("hgai_hypernode_delete", {"node_id": "n"}),
    ("hgai_hyperedge_list", {}), ("hgai_hyperedge_get", {"edge_id": "e"}),
    ("hgai_hyperedge_delete", {"edge_id": "e"}),
]


@pytest.mark.parametrize("tool,extra", GRAPH_TOOLS)
async def test_mcp_graph_tools_deny_other_tenants(world, tool, extra):
    wide = acct("wide", ops=["read", "write", "delete", "query"])   # wildcard graphs, broad ops, Alpha
    assert denied(await call(tool, {"graph_id": "b-g", **extra}, wide))
    assert denied(await call(tool, {"graph_id": "sys-g", **extra}, wide))


async def test_mcp_own_tenant_still_works(world):
    text = await call("hgai_hypergraph_get", {"graph_id": "a-g"}, ALICE)
    assert json.loads(text)["id"] == "a-g"


async def test_mcp_list_tools_are_tenant_filtered(world):
    graphs = json.loads(await call("hgai_hypergraph_list", {}, ALICE))["graphs"]
    assert {g["id"] for g in graphs} == {"a-g", "a-sg"}
    spaces = json.loads(await call("hgai_space_list", {}, ALICE))["spaces"]
    assert {s["id"] for s in spaces} == {"a-s"}
    everyone = json.loads(await call("hgai_space_list", {}, ROOT))["spaces"]
    assert {"a-s", "b-s"} <= {s["id"] for s in everyone}


async def test_mcp_space_tools_deny_other_tenants(world):
    assert denied(await call("hgai_space_get", {"space_id": "b-s"}, ALICE))
    assert denied(await call("hgai_space_list_graphs", {"space_id": "b-s"}, ALICE))
    assert denied(await call("hgai_space_add_member", {"space_id": "b-s", "username": "alice"}, ALICE))
    out = json.loads(await call("hgai_space_add_member", {"space_id": "a-s", "username": "bob"}, ALICE))
    assert "different tenant" in out["error"]


async def test_mcp_created_records_belong_to_the_callers_tenant(world, db):
    await call("hgai_hypergraph_create", {"id": "mcp-g", "label": "x"}, ALICE)
    await call("hgai_space_create", {"id": "mcp-s", "label": "x"}, BOB)
    assert (await db["hypergraphs"].find_one({"id": "mcp-g"}))["tenant_id"] == "Alpha"
    assert (await db["spaces"].find_one({"id": "mcp-s"}))["tenant_id"] == "Bravo"


async def test_mcp_mesh_tools_are_system_admin_only(world):
    for tool in ("hgai_mesh_list",):
        assert denied(await call(tool, {}, ALPHA_ADMIN))
    assert not denied(await call("hgai_mesh_list", {}, ROOT))


async def test_mcp_media_is_tenant_scoped(world):
    m = await _put("alice", "Alpha")
    assert denied(await call("hgai_media_download", {"media_id": m.id}, BOB))
    assert denied(await call("hgai_media_delete", {"media_id": m.id}, BOB))
    assert not denied(await call("hgai_media_download", {"media_id": m.id}, ALICE))
    assert denied(await call("hgai_media_download", {"media_id": "srv/abc"}, ALICE))   # mesh-proxied


# ── Route inventory ──────────────────────────────────────────────────────────

def _routes():
    from hgai.main import create_app
    app = create_app()
    out = []
    for x in app.routes:
        if type(x).__name__ == "_IncludedRouter":
            prefix = getattr(x.include_context, "prefix", "")
            out += [(prefix + r.path, r) for r in x.original_router.routes if hasattr(r, "dependant")]
        elif hasattr(x, "dependant"):
            out.append((x.path, x))
    return out


def _dep_names(dependant, acc=None):
    acc = [] if acc is None else acc
    for sub in dependant.dependencies:
        acc.append(getattr(sub.call, "__qualname__", str(sub.call)))
        _dep_names(sub, acc)
    return acc


AUTH_MARKERS = ("get_current", "require_", "authenticate")
GUARD_MARKERS = ("require_graph_access", "require_space_role", "require_system_admin", "require_tenant_admin")
PUBLIC = {"/api/v1/auth/token", "/health", "/api/v1/server/info", "/"}


def test_every_route_authenticates_except_the_public_ones():
    routes = _routes()
    assert len(routes) > 100  # the inventory really walked the included routers
    open_routes = {
        path for path, r in routes
        if not any(m in n for n in _dep_names(r.dependant) for m in AUTH_MARKERS)
    }
    assert open_routes == PUBLIC


def test_every_graph_or_space_addressed_route_has_an_access_guard():
    unguarded = [
        (sorted(r.methods)[0], path) for path, r in routes_with_ids()
        if not any(m in n for n in _dep_names(r.dependant) for m in GUARD_MARKERS)
    ]
    assert unguarded == []


def routes_with_ids():
    return [(p, r) for p, r in _routes() if "{graph_id" in p or "{space_id" in p]


async def test_control_the_mcp_denials_come_from_the_tenant_boundary(world, monkeypatch):
    set_tenancy(monkeypatch, False)
    wide = acct("wide", ops=["read", "write", "delete", "query"])
    assert not denied(await call("hgai_hypergraph_get", {"graph_id": "b-g"}, wide))  # flag off: wildcard reaches it
