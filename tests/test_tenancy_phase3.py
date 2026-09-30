"""Multi-tenancy Phase 3: tenant API, tenant-scoped accounts/spaces/graphs, and
tenant isolation for notes, media and saved queries.

Real mongod; the routes are called directly with account objects. Reuses the
two-tenant `world` of the Phase 2 tests (Alpha: alice, aadmin; Bravo: bob).
"""

import io

import pytest
from fastapi import HTTPException

from hgai.api.routers import accounts as accounts_r
from hgai.api.routers import hypergraphs as graphs_r
from hgai.api.routers import notes as notes_r
from hgai.api.routers import parameterized_queries as pq_r
from hgai.api.routers import spaces as spaces_r
from hgai.api.routers import tenants as tenants_r
from hgai.core import auth, tenant_engine
from hgai.core.auth import TenantBoundaryError
from hgai.core.media import check_media_tenant
from hgai.db.storage import get_storage
from hgai.models.account import AccountCreate, AccountUpdate
from hgai.models.note import NoteCreate, ShareNoteRequest
from hgai.models.parameterized_query import ParameterizedQueryCreate
from hgai.models.space import AddMemberRequest
from hgai.models.tenant import TenantCreate, TenantUpdate
from hgai_module_storage.filters import MediaFilters
from tests.test_tenancy_phase1 import db  # noqa: F401  (fixture)
from tests.test_tenancy_phase2 import ALICE, ALPHA_ADMIN, BOB, ROOT, acct, set_tenancy, tenancy_on, world  # noqa: F401


async def status_of(coro):
    with pytest.raises(HTTPException) as e:
        await coro
    return e.value.status_code


# ── Tenants API ───────────────────────────────────────────────────────────────

async def test_tenant_crud_system_admin(world):
    made = await tenants_r.create_tenant(TenantCreate(id="Charlie", label="C"), admin=ROOT)
    assert made.id == "Charlie"
    assert await status_of(tenants_r.create_tenant(TenantCreate(id="Charlie", label="C"), admin=ROOT)) == 409
    got = await tenants_r.get_tenant("Charlie", account=ROOT)
    assert got.label == "C"
    upd = await tenants_r.update_tenant("Charlie", TenantUpdate(label="Chuck"), admin=ROOT)
    assert upd.label == "Chuck"
    await tenants_r.delete_tenant("Charlie", admin=ROOT)
    assert await status_of(tenants_r.get_tenant("Charlie", account=ROOT)) == 404


async def test_tenant_visibility(world):
    page = await tenants_r.list_tenants(status_filter=None, skip=0, limit=50, account=ROOT)
    assert {t["id"] for t in page.items} >= {"Alpha", "Bravo", "default"}
    mine = await tenants_r.list_tenants(status_filter=None, skip=0, limit=50, account=ALPHA_ADMIN)
    assert [t["id"] for t in mine.items] == ["Alpha"]
    assert (await tenants_r.get_tenant("Alpha", account=ALICE)).id == "Alpha"      # own tenant
    assert await status_of(tenants_r.get_tenant("Bravo", account=ALICE)) == 404     # other tenant


async def test_tenant_route_guards(world):
    # The routes' dependencies (route functions are called directly above).
    assert await status_of(auth.require_system_admin(ALPHA_ADMIN)) == 403      # create/update/delete
    assert await status_of(auth.require_tenant_admin(ALICE)) == 403             # list


async def test_delete_tenant_rules(world):
    assert await status_of(tenants_r.delete_tenant("Alpha", admin=ROOT)) == 409  # has accounts, spaces, graphs
    assert await status_of(tenants_r.delete_tenant("default", admin=ROOT)) == 400
    assert await status_of(tenants_r.delete_tenant("nope", admin=ROOT)) == 404
    assert await status_of(tenants_r.update_tenant("default", TenantUpdate(status="suspended"), admin=ROOT)) == 400


# ── Accounts ─────────────────────────────────────────────────────────────────

async def test_tenant_admin_lists_only_own_tenants_accounts(world):
    page = await accounts_r.list_accounts(status=None, tenant_id=None, skip=0, limit=50, actor=ALPHA_ADMIN)
    names = {a["username"] for a in page.items}
    assert names == {"alice", "aadmin"}  # not bob, not root
    everyone = await accounts_r.list_accounts(status=None, tenant_id=None, skip=0, limit=50, actor=ROOT)
    assert {"alice", "bob", "root"} <= {a["username"] for a in everyone.items}
    bravo = await accounts_r.list_accounts(status=None, tenant_id="Bravo", skip=0, limit=50, actor=ROOT)
    assert {a["username"] for a in bravo.items} == {"bob"}


async def test_tenant_admin_creates_only_in_own_tenant(world):
    made = await accounts_r.create_account(AccountCreate(username="newbie", password="secret1"), admin=ALPHA_ADMIN)
    assert made.tenant_id == "Alpha"
    assert await status_of(accounts_r.create_account(
        AccountCreate(username="x1", password="secret1", tenant_id="Bravo"), admin=ALPHA_ADMIN)) == 403
    assert await status_of(accounts_r.create_account(
        AccountCreate(username="x2", password="secret1", roles=["admin"]), admin=ALPHA_ADMIN)) == 403
    ok = await accounts_r.create_account(
        AccountCreate(username="t2", password="secret1", roles=["tenant_admin"]), admin=ALPHA_ADMIN)
    assert ok.tenant_id == "Alpha"


async def test_tenant_admin_cannot_reach_other_tenants_or_system_accounts(world):
    for target in ("bob", "root"):
        assert await status_of(accounts_r.get_account(target, actor=ALPHA_ADMIN)) == 404
        assert await status_of(accounts_r.update_account(target, AccountUpdate(description="x"), admin=ALPHA_ADMIN)) == 404
        assert await status_of(accounts_r.delete_account(target, admin=ALPHA_ADMIN)) == 404
    assert (await accounts_r.get_account("alice", actor=ALPHA_ADMIN)).username == "alice"


async def test_tenant_admin_cannot_escalate_via_update(world):
    assert await status_of(accounts_r.update_account(
        "alice", AccountUpdate(system_role="system_admin"), admin=ALPHA_ADMIN)) == 403
    assert await status_of(accounts_r.update_account(
        "alice", AccountUpdate(roles=["admin"]), admin=ALPHA_ADMIN)) == 403
    assert await status_of(accounts_r.update_account(
        "alice", AccountUpdate(tenant_id="Bravo"), admin=ALPHA_ADMIN)) == 403
    done = await accounts_r.update_account("alice", AccountUpdate(description="hi"), admin=ALPHA_ADMIN)
    assert done.description == "hi"


async def test_moving_an_account_drops_its_space_memberships(world):
    await spaces_r.space_engine.add_member("a-s", "alice", "member")
    await accounts_r.update_account("alice", AccountUpdate(tenant_id="Bravo"), admin=ROOT)
    assert await spaces_r.space_engine.get_member_role("a-s", "alice") is None
    assert await status_of(accounts_r.update_account("alice", AccountUpdate(tenant_id="Nope"), admin=ROOT)) == 400


async def test_account_space_assignment_is_tenant_scoped(world):
    body = spaces_r.UpdateMemberRoleRequest(role="member")
    # tenant admin: cannot use another tenant's space
    assert await status_of(accounts_r.assign_account_to_space("alice", "b-s", body, actor=ALPHA_ADMIN)) == 404
    await accounts_r.assign_account_to_space("alice", "a-s", body, actor=ALPHA_ADMIN)
    # system admin: still cannot put a Bravo account in an Alpha space
    assert await status_of(accounts_r.assign_account_to_space("bob", "a-s", body, actor=ROOT)) == 400


# ── Spaces and graphs ───────────────────────────────────────────────────────

async def test_space_listing_is_tenant_scoped(world):
    async def ids(account, tenant_id=None):
        page = await spaces_r.list_spaces(skip=0, limit=50, tenant_id=tenant_id, account=account)
        return {s["id"] for s in page.items}

    assert await ids(ALICE) == {"a-s"}
    assert await ids(BOB) == {"b-s"}
    await spaces_r.space_engine.create_space(spaces_r.SpaceCreate(id="a-s2", label="x"), "aadmin")
    assert await ids(ALPHA_ADMIN) == {"a-s", "a-s2"}           # all of the tenant's spaces
    assert {"a-s", "b-s"} <= await ids(ROOT)
    assert await ids(ROOT, tenant_id="Bravo") == {"b-s"}
    assert await ids(ALICE, tenant_id="Bravo") == {"a-s"}      # tenant_id param ignored for non-system accounts


async def test_space_membership_route_rejects_other_tenants_accounts(world):
    assert await status_of(spaces_r.add_member("a-s", AddMemberRequest(username="bob", role="member"), account=ALICE)) == 400
    ok = await spaces_r.add_member("a-s", AddMemberRequest(username="aadmin", role="member"), account=ALICE)
    assert ok.id == "a-s"


async def test_graph_listing_filters_in_storage_and_pages_correctly(world):
    async def ids(account, tenant_id=None, include_system=False):
        page = await graphs_r.list_graphs(
            status="active", tags=None, space_id=None, search=None, skip=0, limit=50, sort=None,
            include_system=include_system, tenant_id=tenant_id, account=account)
        return page.total, {g["id"] for g in page.items}

    total, got = await ids(ALICE)
    assert got == {"a-g", "a-sg"} and total == 2
    assert (await ids(BOB))[1] == {"b-g", "b-sg"}
    assert (await ids(ALPHA_ADMIN))[1] == {"a-g", "a-sg"}
    assert (await ids(ROOT, tenant_id="Bravo"))[1] == {"b-g", "b-sg"}
    assert "sys-g" in (await ids(ROOT, include_system=False))[1]  # 'sys-g' has no '__' prefix
    assert "sys-g" not in (await ids(ALICE))[1]


# ── Notes ────────────────────────────────────────────────────────────────────

async def test_notes_are_tenant_isolated(world):
    note = await notes_r.create_note_route(NoteCreate(label="plan", scope="public"), account=ALICE)
    assert note["tenant_id"] == "Alpha"
    assert (await notes_r.get_note_route(note["id"], account=acct("carol")))["id"] == note["id"]   # public inside Alpha
    assert await status_of(notes_r.get_note_route(note["id"], account=BOB)) == 404                 # public, but not to Bravo
    page = await notes_r.list_notes(tags=None, search=None, scope=None, owner=None, skip=0, limit=50, sort=None, account=BOB)
    assert page.total == 0
    assert (await notes_r.get_note_route(note["id"], account=ROOT))["id"] == note["id"]


async def test_note_sharing_stays_inside_the_tenant(world):
    note = await notes_r.create_note_route(NoteCreate(label="plan"), account=ALICE)
    assert await status_of(notes_r.share_note_route(note["id"], ShareNoteRequest(username="bob"), account=ALICE)) == 400
    shared = await notes_r.share_note_route(note["id"], ShareNoteRequest(username="aadmin"), account=ALICE)
    assert [g["username"] for g in shared["acl"]] == ["aadmin"]


# ── Media ────────────────────────────────────────────────────────────────────

class _Stream:
    def __init__(self, data):
        self._b = io.BytesIO(data)

    async def read(self, n=-1):
        return self._b.read(n)


async def _put(username, tenant, data=b"same bytes"):
    return await get_storage().media.put(
        f"m-{username}", _Stream(data), content_type="text/plain", filename="f.txt",
        uploaded_by=username, tenant_id=tenant)


async def test_media_is_tenant_stamped_and_dedup_is_per_tenant(world):
    a = await _put("alice", "Alpha")
    b = await _put("bob", "Bravo")
    assert a.id != b.id and a.tenant_id == "Alpha" and b.tenant_id == "Bravo"  # identical bytes, two records
    again = await _put("alice2", "Alpha")
    assert again.id == a.id                                                     # dedup inside a tenant still works
    alpha = await get_storage().media.list(MediaFilters(tenant_id="Alpha"), skip=0, limit=50)
    assert [m.id for m in alpha[1]] == [a.id]


async def test_media_boundary(world):
    a = await _put("alice", "Alpha")
    await check_media_tenant(ALICE, a.id)
    await check_media_tenant(ROOT, a.id)
    with pytest.raises(TenantBoundaryError):
        await check_media_tenant(BOB, a.id)
    with pytest.raises(TenantBoundaryError):
        await check_media_tenant(ALICE, "some-server/abc")  # mesh-proxied media bypasses tenancy
    await check_media_tenant(ALICE, "missing")              # unknown: the route's own 404 follows
    await check_media_tenant(ROOT, "some-server/abc")


# ── Saved queries ────────────────────────────────────────────────────────────

async def test_parameterized_queries_are_tenant_isolated(world):
    q = await pq_r.create_parameterized_query_route(
        ParameterizedQueryCreate(name="n", label="L", shql="from: a-g\nmatch: (n)\nreturn: n"), account=ALICE)
    assert q.tenant_id == "Alpha"
    assert (await pq_r.get_parameterized_query_route(q.id, account=ALPHA_ADMIN)).id == q.id
    assert await status_of(pq_r.get_parameterized_query_route(q.id, account=BOB)) == 404
    assert await status_of(pq_r.delete_parameterized_query_route(q.id, account=BOB)) == 404
    mine = await pq_r.list_parameterized_queries_route(tags=None, search=None, skip=0, limit=50, sort=None, account=BOB)
    assert mine.total == 0
    allq = await pq_r.list_parameterized_queries_route(tags=None, search=None, skip=0, limit=50, sort=None, account=ROOT)
    assert allq.total == 1


# ── Flag off ─────────────────────────────────────────────────────────────────

async def test_flag_off_keeps_legacy_admin_routes(world, monkeypatch):
    set_tenancy(monkeypatch, False)
    assert await status_of(auth.require_tenant_admin(ALPHA_ADMIN)) == 403  # tenant admin powers need the flag
    page = await accounts_r.list_accounts(status=None, tenant_id=None, skip=0, limit=50, actor=ROOT)
    assert {"alice", "bob"} <= {a["username"] for a in page.items}
    assert auth.tenant_scope(ALICE) is None
