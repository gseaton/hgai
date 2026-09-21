"""Per-caller authorization: shared helpers, SHQL execution, the MCP tools and the MCP endpoint.

Storage is faked (no MongoDB): space membership, graph documents and accounts are
in-memory stand-ins patched in where the code looks them up, so what is verified is
the authorization logic itself — the same rules REST enforces via `require_graph_access`.
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi import HTTPException

from hgai.api.deps import require_graph_access, require_space_role
from hgai.core import auth
from hgai.core.auth import (
    PermissionDeniedError,
    authenticate_token,
    can_access_graph,
    check_graph_permission,
    check_space_role,
    create_access_token,
    filter_accessible_graphs,
)
from hgai.models.account import AccountInDB, AccountPermissions
from hgai.models.space import SpaceRole
from hgai_module_shql import engine as shql_engine
from hgai_module_shql.parser import SHQLPermissionError


def make_account(name="alice", roles=("user",), graphs=(), ops=("read", "query"), status="active"):
    return AccountInDB(
        username=name, email=None, roles=list(roles), password_hash="", status=status,
        permissions=AccountPermissions(graphs=list(graphs), operations=list(ops)),
    )


ADMIN = make_account("root", roles=("admin",))
NOBODY = make_account("nobody")                                   # authenticated, no graph permissions
READER = make_account("reader", graphs=["g1"], ops=["read", "query"])
WRITER = make_account("writer", graphs=["g1"], ops=["read", "query", "write", "delete"])
WILDCARD = make_account("wild", graphs=["*"], ops=["read", "query"])

# space id -> {username: role}; graph id -> space id (as get_space_for_graph would say)
MEMBERS = {"s1": {"viewer1": "viewer", "member1": "member", "admin1": "admin", "wild": None}}
GRAPH_SPACE = {"g1": None, "sg": "s1", "shared-id": "s1"}


@pytest.fixture(autouse=True)
def fake_spaces():
    async def get_member_role(space_id, username):
        return MEMBERS.get(space_id, {}).get(username)

    async def get_space_for_graph(graph_id):
        return GRAPH_SPACE.get(graph_id)

    with patch("hgai.core.space_engine.get_member_role", get_member_role), \
         patch("hgai.core.space_engine.get_space_for_graph", get_space_for_graph):
        yield


async def denied(coro):
    with pytest.raises(PermissionDeniedError) as e:
        await coro
    return str(e.value)


# ─── Shared helpers ───────────────────────────────────────────────────────────

class TestCheckGraphPermission:
    async def test_admin_may_do_anything(self):
        await check_graph_permission(ADMIN, "anything", "delete", unowned=True)

    async def test_listed_graph_with_operation(self):
        await check_graph_permission(READER, "g1", "read", unowned=True)

    async def test_unlisted_graph_denied(self):
        assert "Access to graph 'g2'" in await denied(check_graph_permission(READER, "g2", "read", unowned=True))

    async def test_missing_operation_denied(self):
        assert "Operation 'write'" in await denied(check_graph_permission(READER, "g1", "write", unowned=True))

    async def test_wildcard_covers_unowned_graphs(self):
        await check_graph_permission(WILDCARD, "whatever", "read", unowned=True)

    async def test_wildcard_does_not_open_a_space(self):
        # "space membership is the sole gate" — a permissions.graphs wildcard is not enough
        await denied(check_graph_permission(WILDCARD, "sg", "read", space_id="s1"))

    async def test_space_role_supplies_operations(self):
        viewer = make_account("viewer1", ops=[])
        await check_graph_permission(viewer, "sg", "read", space_id="s1")
        assert "Operation 'write'" in await denied(check_graph_permission(viewer, "sg", "write", space_id="s1"))
        member = make_account("member1", ops=[])
        await check_graph_permission(member, "sg", "write", space_id="s1")

    async def test_non_member_denied_in_space(self):
        await denied(check_graph_permission(make_account("stranger", graphs=["*"]), "sg", "read", space_id="s1"))

    async def test_unowned_flag_ignores_a_same_id_space_graph(self):
        # "shared-id" also exists inside space s1; asserting it is the *unowned* graph must not
        # let s1's members in, nor lock out someone holding it in permissions.graphs.
        member = make_account("member1", graphs=[], ops=["read"])
        await denied(check_graph_permission(member, "shared-id", "read", unowned=True))
        holder = make_account("holder", graphs=["shared-id"], ops=["read"])
        await check_graph_permission(holder, "shared-id", "read", unowned=True)

    async def test_id_only_lookup_used_when_not_told(self):
        assert await can_access_graph(make_account("member1"), "sg") is True      # resolved via the space
        assert await can_access_graph(make_account("stranger", graphs=["*"]), "sg") is False


class TestCheckSpaceRole:
    async def test_admin_passes(self):
        await check_space_role(ADMIN, "s1", "owner")

    @pytest.mark.parametrize("user,minimum,ok", [
        ("viewer1", "viewer", True), ("viewer1", "member", False),
        ("member1", "member", True), ("member1", "admin", False),
        ("admin1", "admin", True), ("admin1", "owner", False),
    ])
    async def test_rank(self, user, minimum, ok):
        coro = check_space_role(make_account(user), "s1", minimum)
        if ok:
            await coro
        else:
            await denied(coro)

    async def test_non_member_denied(self):
        assert "Not a member" in await denied(check_space_role(make_account("stranger"), "s1", "viewer"))


class TestFilterAccessibleGraphs:
    async def test_filters_like_can_access_graph(self):
        graphs = [
            SimpleNamespace(id="g1", space_id=None),
            SimpleNamespace(id="g2", space_id=None),
            SimpleNamespace(id="sg", space_id="s1"),
            SimpleNamespace(id="sg2", space_id="s2"),
        ]
        assert [g.id for g in await filter_accessible_graphs(make_account("m", graphs=["g1"]), graphs)] == ["g1"]
        assert [g.id for g in await filter_accessible_graphs(make_account("member1"), graphs)] == ["sg"]
        # wildcard reaches unowned graphs only, never another tenant's space
        assert [g.id for g in await filter_accessible_graphs(WILDCARD, graphs)] == ["g1", "g2"]
        assert len(await filter_accessible_graphs(ADMIN, graphs)) == 4


class TestRestDependenciesShareTheRule:
    async def test_graph_dependency_maps_denial_to_403(self):
        dep = require_graph_access("write")
        with pytest.raises(HTTPException) as e:
            await dep(graph_id="g1", space_id=None, account=READER)
        assert e.value.status_code == 403 and "Operation 'write'" in e.value.detail
        assert await dep(graph_id="g1", space_id=None, account=WRITER) is WRITER

    async def test_space_dependency_maps_denial_to_403(self):
        dep = require_space_role(SpaceRole.admin)
        with pytest.raises(HTTPException) as e:
            await dep(space_id="s1", account=make_account("member1"))
        assert e.value.status_code == 403
        assert await dep(space_id="s1", account=make_account("admin1")) is not None


class TestAuthenticateToken:
    async def test_api_key_is_admin(self):
        with patch.object(auth, "_resolve_api_key", lambda t: t == "k"):
            acct = await authenticate_token("k")
        assert acct.username == "api-key" and "admin" in acct.roles

    async def test_valid_jwt_for_active_account(self):
        token, _ = create_access_token("alice", ["user"])
        with patch.object(auth, "get_account_by_username", AsyncMock(return_value=make_account("alice"))):
            assert (await authenticate_token(token)).username == "alice"

    async def test_inactive_unknown_and_garbage_are_rejected(self):
        token, _ = create_access_token("alice", ["user"])
        with patch.object(auth, "get_account_by_username", AsyncMock(return_value=make_account("alice", status="archived"))):
            assert await authenticate_token(token) is None
        with patch.object(auth, "get_account_by_username", AsyncMock(return_value=None)):
            assert await authenticate_token(token) is None
        assert await authenticate_token("not-a-token") is None
        assert await authenticate_token("") is None
        assert await authenticate_token(None) is None


# ─── SHQL ─────────────────────────────────────────────────────────────────────

class FakeStore:
    """Graph documents keyed (space_id, id), logical composition members, and meshes."""

    def __init__(self, graphs=(), meshes=()):
        self.docs = {(d.space_id, d.id): d for d in graphs}
        self.mesh_ids = set(meshes)
        outer = self

        class Hypergraphs:
            async def get(self, gid, space_id=None):
                return outer.docs.get((space_id, gid))

            async def find_composition_member(self, member_id):
                return next((d for d in outer.docs.values() if d.id == member_id), None)

        class Meshes:
            async def get(self, mid):
                return {"id": mid} if mid in outer.mesh_ids else None

        self.hypergraphs, self.meshes = Hypergraphs(), Meshes()


def graph(gid, space_id=None, type_="instantiated", composition=()):
    return SimpleNamespace(id=gid, space_id=space_id, type=type_, composition=list(composition))


def query(frm):
    return {"from": frm}


@pytest.fixture
def store():
    s = FakeStore(
        graphs=[
            graph("g1"), graph("g2"), graph("sg", "s1"),
            graph("logical", type_="logical", composition=["g1", "g2"]),
        ],
        meshes=["mesh1"],
    )
    with patch.object(shql_engine, "get_storage", return_value=s):
        yield s


class TestSHQLAuthorization:
    async def test_admin_skips_everything(self, store):
        await shql_engine._authorize_query(query("mesh.srv.g"), ADMIN)

    async def test_permitted_graph(self, store):
        await shql_engine._authorize_query(query("g1"), READER)

    async def test_unpermitted_graph(self, store):
        with pytest.raises(SHQLPermissionError, match="Access to graph 'g2'"):
            await shql_engine._authorize_query(query("g2"), READER)

    async def test_unpermitted_graph_is_denied_even_if_it_does_not_exist(self, store):
        with pytest.raises(SHQLPermissionError):
            await shql_engine._authorize_query(query("ghost"), READER)      # no existence oracle

    async def test_query_operation_required(self, store):
        read_only = make_account("ro", graphs=["g1"], ops=["read"])
        with pytest.raises(SHQLPermissionError, match="Operation 'query'"):
            await shql_engine._authorize_query(query("g1"), read_only)

    async def test_every_from_graph_is_checked(self, store):
        with pytest.raises(SHQLPermissionError):
            await shql_engine._authorize_query(query(["g1", "g2"]), READER)
        await shql_engine._authorize_query(query(["g1", "g2"]), make_account("both", graphs=["g1", "g2"]))

    async def test_space_scoped_ref_needs_membership(self, store):
        await shql_engine._authorize_query(query("s1/sg"), make_account("viewer1", ops=[]))
        with pytest.raises(SHQLPermissionError):
            await shql_engine._authorize_query(query("s1/sg"), WILDCARD)     # wildcard is not membership

    async def test_logical_graph_needs_its_members_too(self, store):
        only_logical = make_account("lg", graphs=["logical"])
        with pytest.raises(SHQLPermissionError, match="Access to graph 'g1'"):
            await shql_engine._authorize_query(query("logical"), only_logical)
        await shql_engine._authorize_query(query("logical"), make_account("lg", graphs=["logical", "g1", "g2"]))

    async def test_mesh_references_are_admin_only(self, store):
        for ref in ("mesh1.srv.g1", "mesh1.srv.s1.sg"):
            with pytest.raises(SHQLPermissionError, match="admin"):
                await shql_engine._authorize_query(query(ref), WILDCARD)
        with pytest.raises(SHQLPermissionError, match="admin"):
            await shql_engine._authorize_query(query("mesh1"), WILDCARD)     # bare mesh id, wildcard graph perms

    async def test_unknown_graph_falls_through_to_not_found_once_allowed(self, store):
        await shql_engine._authorize_query(query("ghost"), WILDCARD)         # execution reports "not found"


class TestExecuteShqlChecksBeforeTheCache:
    async def test_cache_hit_is_not_served_to_an_unauthorized_caller(self, store):
        cached = AsyncMock(return_value={"alias": "result", "items": [{"secret": 1}], "meta": {}})
        with patch("hgai.core.cache.get_cached_result", cached):
            with pytest.raises(SHQLPermissionError):
                await shql_engine.execute_shql("shql:\n  from: g2\n  where: []\n", account=READER)
            cached.assert_not_awaited()
            result = await shql_engine.execute_shql("shql:\n  from: g2\n  where: []\n", account=ADMIN)
        assert result.items == [{"secret": 1}]

    async def test_account_is_required(self):
        with pytest.raises(TypeError):
            await shql_engine.execute_shql("shql:\n  from: g1\n")


class TestSHQLRoutes:
    async def test_shql_route_maps_denial_to_403(self):
        from hgai_module_shql.api_router import SHQLRequest, execute_shql_query
        with patch("hgai_module_shql.engine.execute_shql", AsyncMock(side_effect=SHQLPermissionError("nope"))):
            with pytest.raises(HTTPException) as e:
                await execute_shql_query(SHQLRequest(shql="shql:\n  from: g2\n"), READER)
        assert e.value.status_code == 403

    async def test_parameterized_query_route_maps_denial_to_403(self):
        from hgai.api.routers import parameterized_queries as pq
        query_doc = SimpleNamespace(id="q1")
        with patch.object(pq, "get_parameterized_query", AsyncMock(return_value=query_doc)), \
             patch.object(pq, "execute_parameterized_query", AsyncMock(side_effect=SHQLPermissionError("nope"))):
            with pytest.raises(HTTPException) as e:
                await pq.execute_parameterized_query_route(
                    "q1", pq.ExecuteParameterizedQueryRequest(values={}), READER)
        assert e.value.status_code == 403


class TestMeshFederationIsAdminOnly:
    async def test_federated_query_refused_for_non_admin(self):
        from hgai_module_mesh.engine import execute_dot_refs, federated_shql
        with pytest.raises(SHQLPermissionError):
            await federated_shql("m", "shql:\n  from: g\n", account=WILDCARD)
        with pytest.raises(SHQLPermissionError):
            await execute_dot_refs(["m.s.g"], "shql:\n  from: m.s.g\n", account=WILDCARD)


# ─── MCP tools ────────────────────────────────────────────────────────────────

from hgai_module_mcp import server as mcp_server  # noqa: E402  (after the fixtures it patches)
from hgai_module_mcp.server import mcp, reset_caller, set_caller  # noqa: E402

GRAPH_ARGS = {"graph_id": "g1"}
# tool -> (arguments, operation the caller needs on g1)
GRAPH_TOOLS = {
    "hgai_hypergraph_get": (GRAPH_ARGS, "read"),
    "hgai_hypergraph_stats": (GRAPH_ARGS, "read"),
    "hgai_hypernode_list": (GRAPH_ARGS, "read"),
    "hgai_hypernode_get": ({**GRAPH_ARGS, "node_id": "n"}, "read"),
    "hgai_hypernode_create": ({**GRAPH_ARGS, "id": "n", "label": "N"}, "write"),
    "hgai_hypernode_update": ({**GRAPH_ARGS, "node_id": "n", "label": "N2"}, "write"),
    "hgai_hypernode_delete": ({**GRAPH_ARGS, "node_id": "n"}, "delete"),
    "hgai_hyperedge_list": (GRAPH_ARGS, "read"),
    "hgai_hyperedge_get": ({**GRAPH_ARGS, "edge_id": "e"}, "read"),
    "hgai_hyperedge_create": ({**GRAPH_ARGS, "relation": "r", "members_json": '[{"node_id":"a"},{"node_id":"b"}]'}, "write"),
    "hgai_hyperedge_delete": ({**GRAPH_ARGS, "edge_id": "e"}, "delete"),
    "hgai_infer_expand_edge": ({**GRAPH_ARGS, "edge_id": "e"}, "read"),
    "hgai_infer_check_transitive": ({**GRAPH_ARGS, "relation": "r", "start_id": "a", "end_id": "b"}, "read"),
}
ADMIN_TOOLS = {
    "hgai_mesh_list": {},
    "hgai_mesh_get": {"mesh_id": "m"},
    "hgai_mesh_ping": {"mesh_id": "m"},
    "hgai_mesh_sync": {"mesh_id": "m"},
    "hgai_mesh_query": {"mesh_id": "m", "query_yaml": "shql:\n  from: g1\n"},
}
SPACE_TOOLS = {   # tool -> (arguments, minimum space role)
    "hgai_space_get": ({"space_id": "s1"}, "viewer"),
    "hgai_space_list_graphs": ({"space_id": "s1"}, "viewer"),
    "hgai_space_add_member": ({"space_id": "s1", "username": "u"}, "admin"),
}
# Open to any authenticated account, exactly as their REST counterparts are; each still
# runs as the caller (audit stamps, membership filtering) or has its own check.
CALLER_SCOPED_TOOLS = {
    "hgai_hypergraph_list", "hgai_hypergraph_create", "hgai_query_execute", "hgai_query_validate",
    "hgai_space_list", "hgai_space_create",
    "hgai_media_upload", "hgai_media_download", "hgai_media_delete",
}


async def call(tool, args, caller):
    token = set_caller(caller)
    try:
        out = await mcp.call_tool(tool, args)
    finally:
        reset_caller(token)
    content = out[0] if isinstance(out, tuple) else out
    return content[0].text


def is_denied(text):
    try:
        return json.loads(text).get("type") == "PermissionDenied"
    except (ValueError, AttributeError):
        return False


async def test_every_tool_is_classified():
    tools = {t.name for t in await mcp.list_tools()}
    classified = set(GRAPH_TOOLS) | set(ADMIN_TOOLS) | set(SPACE_TOOLS) | CALLER_SCOPED_TOOLS
    assert tools == classified, f"unclassified: {tools - classified}; stale: {classified - tools}"


class TestMcpGraphTools:
    @pytest.fixture(autouse=True)
    def engine_stubs(self):
        stubs = {name: AsyncMock(return_value=None) for name in (
            "get_hypergraph", "get_hypergraph_stats", "list_hypernodes", "get_hypernode", "create_hypernode",
            "update_hypernode", "delete_hypernode", "list_hyperedges", "get_hyperedge", "create_hyperedge",
            "delete_hyperedge")}
        stubs["list_hypernodes"].return_value = (0, [])
        stubs["list_hyperedges"].return_value = (0, [])
        with patch.multiple(mcp_server.engine, **stubs), \
             patch("hgai.core.inference.check_transitive", AsyncMock(return_value=True)):
            self.engine = stubs
            yield

    @pytest.mark.parametrize("tool", sorted(GRAPH_TOOLS))
    async def test_account_without_the_graph_is_denied(self, tool):
        args, _ = GRAPH_TOOLS[tool]
        text = await call(tool, args, NOBODY)
        assert is_denied(text), text
        assert all(not stub.await_count for stub in self.engine.values()), "engine ran despite the denial"

    @pytest.mark.parametrize("tool", sorted(GRAPH_TOOLS))
    async def test_only_the_needed_operation_is_required(self, tool):
        args, op = GRAPH_TOOLS[tool]
        wrong_op = {"read": make_account("x", graphs=["g1"], ops=["write", "delete"]),
                    "write": make_account("x", graphs=["g1"], ops=["read", "query", "delete"]),
                    "delete": make_account("x", graphs=["g1"], ops=["read", "query", "write"])}[op]
        assert is_denied(await call(tool, args, wrong_op)), f"{tool} should need '{op}'"
        assert not is_denied(await call(tool, args, make_account("x", graphs=["g1"], ops=[op])))

    @pytest.mark.parametrize("tool", sorted(GRAPH_TOOLS))
    async def test_admin_passes_the_guard(self, tool):
        assert not is_denied(await call(tool, GRAPH_TOOLS[tool][0], ADMIN))

    async def test_another_graph_is_denied_even_with_the_operation(self):
        assert is_denied(await call("hgai_hypernode_list", {"graph_id": "g2"}, READER))

    async def test_writes_are_attributed_to_the_caller(self):
        self.engine["create_hypernode"].return_value = SimpleNamespace(model_dump=lambda: {})
        await call("hgai_hypernode_create", {"graph_id": "g1", "id": "n", "label": "N"}, WRITER)
        assert self.engine["create_hypernode"].await_args.kwargs["created_by"] == "writer"

    async def test_no_caller_means_no_access(self):
        out = await mcp.call_tool("hgai_hypernode_list", {"graph_id": "g1"})   # no set_caller
        assert is_denied((out[0] if isinstance(out, tuple) else out)[0].text)
        assert not self.engine["list_hypernodes"].await_count


class TestMcpAdminAndSpaceTools:
    @pytest.mark.parametrize("tool", sorted(ADMIN_TOOLS))
    async def test_mesh_tools_are_admin_only(self, tool):
        assert is_denied(await call(tool, ADMIN_TOOLS[tool], WILDCARD))

    @pytest.mark.parametrize("tool", sorted(SPACE_TOOLS))
    async def test_space_tools_need_a_space_role(self, tool):
        args, minimum = SPACE_TOOLS[tool]
        assert is_denied(await call(tool, args, make_account("stranger")))
        ranks = ["viewer", "member", "admin"]
        below = ranks[ranks.index(minimum) - 1] if minimum != "viewer" else None
        if below:
            below_user = {"viewer": "viewer1", "member": "member1"}[below]
            assert is_denied(await call(tool, args, make_account(below_user)))

    async def test_space_list_shows_only_the_callers_spaces(self):
        listed = AsyncMock(return_value=(0, []))
        with patch("hgai.core.space_engine.list_spaces", listed):
            await call("hgai_space_list", {}, make_account("member1"))
            assert listed.await_args.kwargs["username"] == "member1"
            await call("hgai_space_list", {}, ADMIN)
            assert listed.await_args.kwargs["username"] is None


class TestMcpQueryAndList:
    async def test_query_execute_denied_for_an_unpermitted_graph(self):
        with patch.object(shql_engine, "get_storage", return_value=FakeStore(graphs=[graph("g2")])):
            text = await call("hgai_query_execute", {"query_yaml": "shql:\n  from: g2\n  where: []\n"}, READER)
        assert is_denied(text), text

    async def test_query_execute_runs_as_the_caller(self):
        seen = {}

        async def fake_execute(q, use_cache=True, *, account):
            seen["account"] = account
            return SimpleNamespace(to_dict=lambda: {"count": 0, "items": []})

        with patch.object(mcp_server, "execute_shql", fake_execute):
            await call("hgai_query_execute", {"query_yaml": "shql:\n  from: g1\n"}, READER)
        assert seen["account"].username == "reader"

    async def test_hypergraph_list_is_filtered_to_what_the_caller_may_see(self):
        graphs = [
            SimpleNamespace(id="g1", label="g1", type="instantiated", status="active", node_count=0, edge_count=0, space_id=None),
            SimpleNamespace(id="g2", label="g2", type="instantiated", status="active", node_count=0, edge_count=0, space_id=None),
            SimpleNamespace(id="sg", label="sg", type="instantiated", status="active", node_count=0, edge_count=0, space_id="s1"),
        ]
        with patch.object(mcp_server.engine, "list_hypergraphs", AsyncMock(return_value=(3, graphs))):
            listed = json.loads(await call("hgai_hypergraph_list", {}, READER))
            assert [g["id"] for g in listed["graphs"]] == ["g1"] and listed["total"] == 1
            assert [g["id"] for g in json.loads(await call("hgai_hypergraph_list", {}, ADMIN))["graphs"]] == ["g1", "g2", "sg"]


# ─── The MCP endpoint end to end ──────────────────────────────────────────────

async def rpc(client, token, tool, arguments):
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return await client.post("/", headers=headers, json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": arguments}})


def rpc_text(response):
    for line in response.text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:])["result"]["content"][0]["text"]
    return json.loads(response.text)["result"]["content"][0]["text"]


async def test_mcp_endpoint_authenticates_and_scopes_every_call():
    """Through the real ASGI app: credentials -> account -> tool.

    One test on purpose: the MCP session manager may be started only once per process.
    """
    from hgai_module_mcp.module import MCPModule

    accounts = {"alice": make_account("alice", roles=("readonly",)), "root": ADMIN,
                "gone": make_account("gone", status="archived")}

    async def lookup(username):
        return accounts.get(username)

    module = MCPModule()
    app = module.get_app()
    with patch.object(auth, "get_account_by_username", lookup):
        async with module.lifespan():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8357/") as client:
                # no credential / a bad one / a disabled account's otherwise-valid token -> 401
                assert (await rpc(client, None, "hgai_mesh_list", {})).status_code == 401
                assert (await rpc(client, "garbage", "hgai_mesh_list", {})).status_code == 401
                gone, _ = create_access_token("gone", ["user"])
                assert (await rpc(client, gone, "hgai_mesh_list", {})).status_code == 401

                # the tool sees the caller: a readonly account is refused an admin-only tool
                alice, _ = create_access_token("alice", ["readonly"])
                response = await rpc(client, alice, "hgai_mesh_list", {})
                assert response.status_code == 200 and is_denied(rpc_text(response))

                # ... and identities never bleed between concurrent calls
                tokens = {"alice": alice, "root": create_access_token("root", ["admin"])[0]}
                order = ["alice", "root"] * 6
                with patch("hgai.db.storage.get_storage", side_effect=RuntimeError("storage not needed here")):
                    responses = await asyncio.gather(*[rpc(client, tokens[who], "hgai_mesh_list", {}) for who in order])
                for who, response in zip(order, responses):
                    assert is_denied(rpc_text(response)) == (who == "alice"), who
