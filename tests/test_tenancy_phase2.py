"""Multi-tenancy Phase 2: the tenant boundary in the auth chokepoint.

Real mongod (shared fixture). Two tenants, Alpha and Bravo, each with graphs and a
space, plus a system-level graph. What is verified is who may reach what.
"""

import pytest
from fastapi import HTTPException

from hgai.api import deps
from hgai.core import auth, engine, space_engine, tenant_engine
from hgai.core.auth import (
    PermissionDeniedError,
    TenantBoundaryError,
    authenticate_token,
    can_access_graph,
    can_administer_tenant,
    can_perform,
    check_graph_permission,
    check_space_role,
    create_access_token,
    filter_accessible_graphs,
)
from hgai.models.account import AccountInDB, AccountPermissions
from hgai.models.hypergraph import HypergraphCreate
from hgai.models.space import SpaceCreate
from hgai.models.tenant import TenantCreate, TenantUpdate
from tests.test_tenancy_phase1 import db  # noqa: F401  (fixture)

ALL_OPS = ["read", "write", "delete", "admin", "query", "export", "import"]


def acct(name, roles=("user",), tenant="Alpha", graphs=("*",), ops=("read", "query"), **kw):
    return AccountInDB(
        username=name, roles=list(roles), tenant_id=tenant, password_hash="", status="active",
        permissions=AccountPermissions(graphs=list(graphs), operations=list(ops)), **kw,
    )


ROOT = acct("root", roles=("admin",), tenant=None, graphs=("*",), ops=ALL_OPS)
ALICE = acct("alice")                                   # Alpha user, wildcard graphs
ALPHA_ADMIN = acct("aadmin", roles=("tenant_admin",))
BOB = acct("bob", tenant="Bravo")


def set_tenancy(monkeypatch, enabled: bool):
    """Flip HGAI_MULTITENANCY_ENABLED for every caller (routers bind the helper by name)."""
    real = auth.get_settings()
    patched = real.model_copy(update={"multitenancy_enabled": enabled})
    monkeypatch.setattr(auth, "get_settings", lambda: patched)


@pytest.fixture
def tenancy_on(monkeypatch):
    set_tenancy(monkeypatch, True)


@pytest.fixture
async def world(db, tenancy_on):  # noqa: F811
    """Alpha and Bravo each with an unowned graph and a space graph; one system graph."""
    await tenant_engine.ensure_default_tenant()
    for t in ("Alpha", "Bravo"):
        await tenant_engine.create_tenant(TenantCreate(id=t, label=t), "root")
    await db["accounts"].insert_many([
        {"username": a.username, "roles": list(a.roles), "password_hash": "", "status": "active",
         "tenant_id": a.tenant_id, **({"system_role": "system_admin"} if a.system_role else {}),
         "permissions": {"graphs": ["*"], "operations": ["read", "query"]}}
        for a in (ROOT, ALICE, ALPHA_ADMIN, BOB)
    ])
    await engine.create_hypergraph(HypergraphCreate(id="a-g", label="a"), "alice")
    await engine.create_hypergraph(HypergraphCreate(id="b-g", label="b"), "bob")
    await space_engine.create_space(SpaceCreate(id="a-s", label="as"), "alice")
    await space_engine.create_space(SpaceCreate(id="b-s", label="bs"), "bob")
    await engine.create_hypergraph(HypergraphCreate(id="a-sg", label="x", space_id="a-s"), "alice")
    await engine.create_hypergraph(HypergraphCreate(id="b-sg", label="x", space_id="b-s"), "bob")
    await engine.create_hypergraph(HypergraphCreate(id="sys-g", label="sys"), "system")
    return db


# ── Stamping at creation ──────────────────────────────────────────────────────

async def test_new_records_are_stamped_with_creators_tenant(world):
    g = {d["id"]: d async for d in world["hypergraphs"].find({})}
    s = {d["id"]: d async for d in world["spaces"].find({})}
    assert g["a-g"]["tenant_id"] == "Alpha" and g["b-g"]["tenant_id"] == "Bravo"
    assert g["a-sg"]["tenant_id"] == "Alpha" and g["b-sg"]["tenant_id"] == "Bravo"
    assert s["a-s"]["tenant_id"] == "Alpha" and s["b-s"]["tenant_id"] == "Bravo"
    assert g["sys-g"]["tenant_id"] is None  # created by the internal system actor


async def test_tenant_account_cannot_choose_another_tenant(world):
    await engine.create_hypergraph(HypergraphCreate(id="sneaky", label="x", tenant_id="Bravo"), "alice")
    assert (await world["hypergraphs"].find_one({"id": "sneaky"}))["tenant_id"] == "Alpha"


async def test_system_admin_can_name_a_tenant(world):
    await engine.create_hypergraph(HypergraphCreate(id="for-b", label="x", tenant_id="Bravo"), "root")
    await engine.create_hypergraph(HypergraphCreate(id="dflt", label="x"), "root")
    assert (await world["hypergraphs"].find_one({"id": "for-b"}))["tenant_id"] == "Bravo"
    assert (await world["hypergraphs"].find_one({"id": "dflt"}))["tenant_id"] == "default"


# ── The boundary ──────────────────────────────────────────────────────────────

async def test_wildcard_does_not_cross_tenants(world):
    assert await can_access_graph(ALICE, "a-g", unowned=True)
    assert not await can_access_graph(ALICE, "b-g", unowned=True)
    assert not await can_access_graph(ALICE, "sys-g", unowned=True)  # system-level graph


async def test_space_membership_does_not_cross_tenants(world):
    await space_engine.add_member("b-s", "alice", "owner")  # cross-tenant membership, however it got there
    assert not await can_access_graph(ALICE, "b-sg", space_id="b-s")
    with pytest.raises(TenantBoundaryError):
        await check_space_role(ALICE, "b-s", "viewer")


async def test_cross_tenant_raises_boundary_error_in_tenant_raises_permission_error(world):
    with pytest.raises(TenantBoundaryError):
        await check_graph_permission(ALICE, "b-g", "read", unowned=True)
    with pytest.raises(PermissionDeniedError) as e:
        await check_graph_permission(ALICE, "a-g", "write", unowned=True)  # own tenant, lacks write
    assert not isinstance(e.value, TenantBoundaryError)
    await check_graph_permission(ALICE, "a-g", "read", unowned=True)


async def test_can_perform_respects_boundary(world):
    assert not await can_perform(ALICE, "read", graph_id="b-g", unowned=True)
    assert await can_perform(ALICE, "read", graph_id="a-g", unowned=True)


async def test_tenant_admin_has_full_rights_in_own_tenant_only(world):
    assert await can_access_graph(ALPHA_ADMIN, "a-sg", space_id="a-s")  # not a member of the space
    await check_graph_permission(ALPHA_ADMIN, "a-g", "delete", unowned=True)
    await check_space_role(ALPHA_ADMIN, "a-s", "owner")
    with pytest.raises(TenantBoundaryError):
        await check_graph_permission(ALPHA_ADMIN, "b-g", "read", unowned=True)
    with pytest.raises(TenantBoundaryError):
        await check_space_role(ALPHA_ADMIN, "b-s", "viewer")


async def test_system_admin_reaches_every_tenant(world):
    for gid, sid in (("a-g", None), ("b-g", None), ("b-sg", "b-s"), ("sys-g", None)):
        await check_graph_permission(ROOT, gid, "delete", space_id=sid, unowned=sid is None)
    await check_space_role(ROOT, "a-s", "owner")
    await check_space_role(ROOT, "b-s", "owner")


async def test_filter_accessible_graphs(world):
    _, graphs = await engine.list_hypergraphs(include_system=True, limit=100)
    ids = lambda accs: sorted(g.id for g in accs)  # noqa: E731
    assert ids(await filter_accessible_graphs(ALICE, graphs)) == ["a-g", "a-sg"]  # alice owns space a-s
    assert ids(await filter_accessible_graphs(ALPHA_ADMIN, graphs)) == ["a-g", "a-sg"]  # without being a member
    assert ids(await filter_accessible_graphs(acct("carol"), graphs)) == ["a-g"]  # Alpha, not in a-s
    assert ids(await filter_accessible_graphs(BOB, graphs)) == ["b-g", "b-sg"]
    assert ids(await filter_accessible_graphs(ROOT, graphs)) == sorted(g.id for g in graphs)


async def test_rest_dependency_maps_cross_tenant_to_404(world):
    dep = deps.require_graph_access("read")
    with pytest.raises(HTTPException) as e:
        await dep(graph_id="b-g", space_id=None, account=ALICE)
    assert e.value.status_code == 404
    with pytest.raises(HTTPException) as e:
        await deps.require_space_role()(space_id="b-s", account=ALICE)
    assert e.value.status_code == 404
    with pytest.raises(HTTPException) as e:
        await dep(graph_id="a-g", space_id=None, account=acct("nope", graphs=()))  # in tenant, no grant
    assert e.value.status_code == 403


async def test_missing_graph_is_left_to_normal_checks(world):
    assert await auth._tenant_allows_graph(ALICE, "does-not-exist", None, True)


# ── Flag off: behavior unchanged ─────────────────────────────────────────────

async def test_flag_off_applies_no_boundary(world, monkeypatch):
    set_tenancy(monkeypatch, False)
    assert await can_access_graph(ALICE, "b-g", unowned=True)  # as before: permissions.graphs only
    assert not await can_access_graph(ALPHA_ADMIN, "a-sg", space_id="a-s")  # tenant_admin powers need the flag


# ── Tenant status and role gates ─────────────────────────────────────────────

async def test_suspended_tenant_locks_out_its_accounts_only(world):
    tok_a, _ = create_access_token("alice", ["user"])
    tok_b, _ = create_access_token("bob", ["user"])
    tok_r, _ = create_access_token("root", ["admin"])
    assert (await authenticate_token(tok_a)).username == "alice"
    await tenant_engine.update_tenant("Alpha", TenantUpdate(status="suspended"), "root")
    assert await authenticate_token(tok_a) is None
    assert (await authenticate_token(tok_b)).username == "bob"
    assert (await authenticate_token(tok_r)).username == "root"  # system admin unaffected


async def test_account_in_missing_tenant_is_rejected(world):
    await world["accounts"].insert_one(
        {"username": "ghost", "roles": ["user"], "password_hash": "", "status": "active", "tenant_id": "Gone"})
    tok, _ = create_access_token("ghost", ["user"])
    assert await authenticate_token(tok) is None


async def test_suspension_ignored_when_flag_off(world, monkeypatch):
    await tenant_engine.update_tenant("Alpha", TenantUpdate(status="suspended"), "root")
    set_tenancy(monkeypatch, False)
    tok, _ = create_access_token("alice", ["user"])
    assert (await authenticate_token(tok)).username == "alice"


async def test_role_gates(world):
    assert await auth.require_system_admin(ROOT) is ROOT
    with pytest.raises(HTTPException):
        await auth.require_system_admin(ALPHA_ADMIN)
    assert await auth.require_tenant_admin(ALPHA_ADMIN) is ALPHA_ADMIN
    assert await auth.require_tenant_admin(ROOT) is ROOT
    with pytest.raises(HTTPException):
        await auth.require_tenant_admin(ALICE)
    assert auth.require_admin is auth.require_system_admin  # legacy name
    with pytest.raises(PermissionDeniedError):
        auth.require_admin_role(ALPHA_ADMIN, "mesh")


async def test_can_administer_tenant(world):
    assert can_administer_tenant(ROOT, "Bravo")
    assert can_administer_tenant(ALPHA_ADMIN, "Alpha")
    assert not can_administer_tenant(ALPHA_ADMIN, "Bravo")
    assert not can_administer_tenant(ALICE, "Alpha")


# ── Account creation ─────────────────────────────────────────────────────────

async def test_create_account_assigns_and_validates_tenant(world):
    from hgai.api.routers.accounts import create_account
    from hgai.models.account import AccountCreate

    made = await create_account(AccountCreate(username="c1", password="secret1", tenant_id="Bravo"), admin=ROOT)
    assert made.tenant_id == "Bravo"
    dflt = await create_account(AccountCreate(username="c2", password="secret1"), admin=ROOT)
    assert dflt.tenant_id == "default"
    sysacct = await create_account(AccountCreate(username="c3", password="secret1", roles=["admin"]), admin=ROOT)
    assert sysacct.tenant_id is None and sysacct.system_role == "system_admin"
    with pytest.raises(HTTPException) as e:
        await create_account(AccountCreate(username="c4", password="secret1", tenant_id="Nope"), admin=ROOT)
    assert e.value.status_code == 400
