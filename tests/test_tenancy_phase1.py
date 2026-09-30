"""Multi-tenancy Phase 1: tenant model, tenant store, account/resource fields, startup migration.

Runs against a real mongod (same fixture as the storage tests). Enforcement is a
later phase, so nothing here checks access, only what is stored and stamped.
"""

import pytest
from pydantic import ValidationError

from hgai.core import tenant_engine
from hgai.core.tenant_engine import TenancyError, effective_tenant_id, validate_account_tenancy
from hgai.models.account import AccountInDB, Role, SystemRole
from hgai.models.tenant import DEFAULT_TENANT_ID, TenantCreate, TenantUpdate


def _acct(name="a", roles=("user",), **kw):
    return AccountInDB(username=name, roles=list(roles), password_hash="", **kw)


# ── Models ────────────────────────────────────────────────────────────────────

def test_legacy_admin_reads_as_system_admin():
    a = _acct("root", roles=("admin",))
    assert a.system_role == SystemRole.system_admin
    assert "admin" in a.roles  # legacy role kept


def test_ordinary_account_has_no_system_role_or_tenant():
    a = _acct()
    assert a.system_role is None and a.tenant_id is None


def test_tenant_admin_role_exists():
    assert Role.tenant_admin.value == "tenant_admin"


@pytest.mark.parametrize("bad", ["__system", "a.b", "has space", "-lead", "a/b", ""])
def test_tenant_id_rejected(bad):
    with pytest.raises(ValidationError):
        TenantCreate(id=bad, label="x")


@pytest.mark.parametrize("ok", ["Alpha", "alpha-1", "a_b", "9lives"])
def test_tenant_id_accepted(ok):
    assert TenantCreate(id=ok, label="x").id == ok


def test_effective_tenant_id():
    assert effective_tenant_id(_acct("root", roles=("admin",))) is None
    assert effective_tenant_id(_acct(tenant_id="Alpha")) == "Alpha"
    assert effective_tenant_id(_acct()) == DEFAULT_TENANT_ID  # pre-migration account


# ── Storage and migration (real mongod) ──────────────────────────────────────

@pytest.fixture
async def db(mongod):  # noqa: F811
    from hgai.db import storage
    import hgai_module_storage_mongodb  # noqa: F401

    await storage.init_storage("mongodb", mongo_uri=mongod, mongo_db="hgai_tenancy_test")
    from hgai_module_storage_mongodb.connection import get_db
    d = get_db()
    try:
        yield d
    finally:
        await d.client.drop_database("hgai_tenancy_test")
        await storage.close_storage()


async def test_tenant_store_crud(db):
    t = await tenant_engine.create_tenant(TenantCreate(id="Alpha", label="Alpha Corp"), "root")
    assert t.status == "active" and t.version == 1
    assert (await tenant_engine.get_tenant("Alpha")).label == "Alpha Corp"
    u = await tenant_engine.update_tenant("Alpha", TenantUpdate(status="suspended", label="A"), "root")
    assert u.status == "suspended" and u.label == "A" and u.version == 2
    total, rows = await tenant_engine.list_tenants(status="suspended")
    assert total == 1 and rows[0].id == "Alpha"
    assert await tenant_engine.get_tenant("nope") is None


async def test_tenant_id_unique(db):
    await tenant_engine.create_tenant(TenantCreate(id="Alpha", label="x"), "root")
    with pytest.raises(Exception):
        await tenant_engine.create_tenant(TenantCreate(id="Alpha", label="y"), "root")


async def test_validate_account_tenancy(db):
    await tenant_engine.create_tenant(TenantCreate(id="Alpha", label="x"), "root")
    await tenant_engine.create_tenant(TenantCreate(id="Dead", label="x", status="suspended"), "root")
    await validate_account_tenancy(None, "Alpha", ["user"])
    await validate_account_tenancy("system_admin", None, ["admin"])
    for tid, roles in ((None, ["user"]), (None, ["tenant_admin"]), ("Nope", ["user"]), ("Dead", ["user"])):
        with pytest.raises(TenancyError):
            await validate_account_tenancy(None, tid, roles)


async def _seed_legacy(db):
    """Records as they existed before multi-tenancy: none carry tenant_id."""
    await db["accounts"].insert_many([
        {"username": "root", "roles": ["admin"], "password_hash": ""},
        {"username": "alice", "roles": ["user"], "password_hash": ""},
    ])
    await db["spaces"].insert_one({"id": "s1", "label": "S1", "members": []})
    await db["hypergraphs"].insert_many([
        {"id": "g-unowned", "label": "g", "space_id": None},
        {"id": "g-in-space", "label": "g", "space_id": "s1"},
        {"id": "__local-telemetry", "label": "t", "space_id": None},
    ])
    await db["notes"].insert_many([
        {"id": "n1", "owner_username": "alice"},
        {"id": "n2", "owner_username": "root"},
    ])
    await db["parameterized_queries"].insert_one({"id": "q1", "created_by": "alice"})


async def test_migration_stamps_legacy_records(db):
    await _seed_legacy(db)
    counts = await tenant_engine.run_tenancy_migration()

    assert (await tenant_engine.get_tenant(DEFAULT_TENANT_ID)) is not None
    root = await db["accounts"].find_one({"username": "root"})
    alice = await db["accounts"].find_one({"username": "alice"})
    assert root["system_role"] == "system_admin" and "tenant_id" not in root
    assert alice["tenant_id"] == DEFAULT_TENANT_ID and "system_role" not in alice

    assert (await db["spaces"].find_one({"id": "s1"}))["tenant_id"] == DEFAULT_TENANT_ID
    g = {d["id"]: d async for d in db["hypergraphs"].find({})}
    assert g["g-unowned"]["tenant_id"] == DEFAULT_TENANT_ID
    assert g["g-in-space"]["tenant_id"] == DEFAULT_TENANT_ID
    assert g["__local-telemetry"]["tenant_id"] is None  # system-level graph

    n = {d["id"]: d for d in await db["notes"].find({}).to_list(10)}
    assert n["n1"]["tenant_id"] == DEFAULT_TENANT_ID
    assert n["n2"]["tenant_id"] is None  # owned by a system account
    assert (await db["parameterized_queries"].find_one({"id": "q1"}))["tenant_id"] == DEFAULT_TENANT_ID
    assert counts["accounts"] == 1 and counts["accounts_system_admin"] == 1 and counts["hypergraphs"] == 3


async def test_migration_is_idempotent(db):
    await _seed_legacy(db)
    await tenant_engine.run_tenancy_migration()
    second = await tenant_engine.run_tenancy_migration()
    assert not any(second.values())
    assert (await tenant_engine.list_tenants())[0] == 1  # default tenant not duplicated


async def test_migration_keeps_existing_stamps(db):
    await tenant_engine.create_tenant(TenantCreate(id="Alpha", label="x"), "root")
    await db["spaces"].insert_one({"id": "sa", "label": "SA", "members": [], "tenant_id": "Alpha"})
    await db["hypergraphs"].insert_one({"id": "ga", "label": "g", "space_id": "sa"})
    await db["accounts"].insert_one({"username": "bob", "roles": ["user"], "password_hash": "", "tenant_id": "Alpha"})
    await tenant_engine.run_tenancy_migration()
    assert (await db["spaces"].find_one({"id": "sa"}))["tenant_id"] == "Alpha"
    assert (await db["hypergraphs"].find_one({"id": "ga"}))["tenant_id"] == "Alpha"  # from its space
    assert (await db["accounts"].find_one({"username": "bob"}))["tenant_id"] == "Alpha"


async def test_tenant_indexes_exist(db):
    assert "id_unique" in await _names(db, "tenants")
    for c in ("accounts", "spaces", "notes", "parameterized_queries", "media"):
        assert "tenant_id" in await _names(db, c)
    assert "tenant_id_id" in await _names(db, "hypergraphs")


async def _names(db, coll):
    return {i["name"] async for i in db[coll].list_indexes()}
