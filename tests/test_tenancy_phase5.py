"""Multi-tenancy Phase 5: what clients see (GET /auth/me), the shell's tenant commands,
telemetry's tenant field, and the UI script's tenancy hooks.

The browser UI itself was exercised by hand against a live server; here the pieces
that can be checked without a browser are.
"""

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hgai.api.routers import auth as auth_r
from hgai.core import auth
from hgai.models.tenant import SYSTEM_TENANT_ID
from hgai_module_telemetry.events import account_field, build_event
from shell.hgai_shell import HgaiClient, HgaiShell
from tests.test_tenancy_phase1 import db  # noqa: F401  (fixture)
from tests.test_tenancy_phase2 import ALICE, ALPHA_ADMIN, ROOT, acct, set_tenancy, tenancy_on, world  # noqa: F401
from tests.test_telemetry import make_settings

ROOT_DIR = Path(__file__).resolve().parent.parent


# ── GET /auth/me ──────────────────────────────────────────────────────────────

async def test_me_reports_tenancy_for_a_tenant_account(world):
    me = await auth_r.get_me(account=ALICE)
    assert me.multitenancy_enabled is True
    assert me.tenant_id == "Alpha" and me.tenant_label == "Alpha"
    assert me.system_role is None


async def test_me_for_a_system_admin_has_no_tenant(world):
    me = await auth_r.get_me(account=ROOT)
    assert me.multitenancy_enabled is True
    assert me.system_role == "system_admin" and me.tenant_label is None


async def test_me_with_tenancy_off_hides_tenant_info(world, monkeypatch):
    set_tenancy(monkeypatch, False)
    me = await auth_r.get_me(account=ALICE)
    assert me.multitenancy_enabled is False and me.tenant_label is None


# ── Telemetry ─────────────────────────────────────────────────────────────────

def test_telemetry_tenant_is_hashed_by_default():
    s = make_settings()
    field = account_field(acct("alice", tenant="Alpha"), s)
    assert field["tenant"] not in ("Alpha", None) and len(field["tenant"]) == 64
    assert field["tenant"] == account_field(acct("bob", tenant="Alpha"), s)["tenant"]   # same tenant, same value
    assert field["tenant"] != account_field(acct("bob", tenant="Bravo"), s)["tenant"]


def test_telemetry_tenant_in_the_clear_when_account_ids_are():
    s = make_settings(telemetry_include_account_ids=True)
    assert account_field(acct("alice", tenant="Alpha"), s)["tenant"] == "Alpha"


def test_telemetry_system_actor_has_the_system_tenant():
    s = make_settings()
    assert account_field(ROOT, s)["tenant"] == SYSTEM_TENANT_ID
    e = build_event(kind="usage", surface="rest", feature="f", duration_ms=1, outcome="ok")
    assert e["tenant"] == SYSTEM_TENANT_ID and e["actor"] == "__system"
    e2 = build_event(kind="usage", surface="rest", feature="f", duration_ms=1, outcome="ok",
                     account=account_field(acct("alice", tenant="Alpha"), s))
    assert e2["tenant"] == e2["account"]["tenant"]


# ── Shell ─────────────────────────────────────────────────────────────────────

@pytest.fixture
def shell():
    sh = HgaiShell()
    sh.client = MagicMock(spec=HgaiClient)
    sh.client.me.return_value = {"system_role": "system_admin"}
    sh.username = "root"
    sh.server_url = "http://x"
    return sh


def test_use_tenant_sets_and_clears_scope(shell):
    shell.client.get_tenant.return_value = {"id": "alpha"}
    shell.active_graph = "g"
    shell.cmd_use(["tenant", "alpha"])
    assert shell.tenant_scope == "alpha" and shell.active_graph is None
    assert "<alpha>" in shell._prompt_str()
    shell.cmd_use(["tenant", "all"])
    assert shell.tenant_scope is None and "<alpha>" not in shell._prompt_str()


def test_use_tenant_unknown_leaves_scope_alone(shell):
    shell.client.get_tenant.side_effect = KeyError("nope")
    shell.cmd_use(["tenant", "ghost"])
    assert shell.tenant_scope is None


def test_ls_passes_the_tenant_scope(shell):
    shell.tenant_scope = "alpha"
    shell.client.list_graphs.return_value = {"items": [], "total": 0}
    shell.client.list_accounts.return_value = {"items": [], "total": 0}
    shell.cmd_ls(["graphs"])
    shell.cmd_ls(["accounts"])
    assert shell.client.list_graphs.call_args.kwargs["tenant_id"] == "alpha"
    assert shell.client.list_accounts.call_args.kwargs["tenant_id"] == "alpha"


def test_ls_tenants_and_get_tenant(shell):
    shell.client.list_tenants.return_value = {"items": [{"id": "alpha", "label": "A", "status": "active"}], "total": 1}
    shell.client.get_tenant.return_value = {"id": "alpha"}
    shell.cmd_ls(["tenants"])
    shell.cmd_get(["tenant", "alpha"])
    shell.client.list_tenants.assert_called_once()
    shell.client.get_tenant.assert_called_with("alpha")


def test_delete_tenant_clears_a_matching_scope(shell, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "y")
    shell.tenant_scope = "alpha"
    shell.cmd_delete(["tenant", "alpha"])
    shell.client.delete_tenant.assert_called_with("alpha")
    assert shell.tenant_scope is None


def test_use_graph_keyword_reaches_a_graph_named_tenant(shell):
    shell.client.get_graph.return_value = {"id": "tenant"}
    shell.cmd_use(["graph", "tenant"])
    assert shell.active_graph == "tenant" and shell.tenant_scope is None


def test_client_tenant_methods_hit_the_tenant_routes():
    c = HgaiClient("http://x")
    calls = []
    c._request = lambda method, path, body=None, params=None: calls.append((method, path, body, params))
    c.list_tenants(limit=5); c.get_tenant("a"); c.create_tenant({"id": "a"}); c.update_tenant("a", {}); c.delete_tenant("a")
    c.list_graphs(tenant_id="a")
    assert [(m, p) for m, p, *_ in calls[:5]] == [
        ("GET", "/tenants"), ("GET", "/tenants/a"), ("POST", "/tenants"), ("PUT", "/tenants/a"), ("DELETE", "/tenants/a")]
    assert calls[5][3]["tenant_id"] == "a"


# ── Web UI script ─────────────────────────────────────────────────────────────

def test_ui_tenancy_hooks_are_wired():
    html = (ROOT_DIR / "ui/index.html").read_text()
    js = (ROOT_DIR / "ui/js/app.js").read_text()
    api = (ROOT_DIR / "ui/js/api.js").read_text()
    for marker in ('data-screen="tenants"', 'id="screen-tenants"', 'id="tenant-scope-select"',
                   'id="modal-tenant"', 'id="account-tenant"', 'id="role-tenant_admin"'):
        assert marker in html, marker
    # Spaces and Accounts are the only admin areas a tenant admin may see.
    assert len(re.findall(r"data-tenant-admin", html)) == 7     # section label, 3 links (Spaces, Accounts, API Keys), 3 screens
    for fn in ("applyTenancyUi", "loadTenants", "openTenantModal", "populateTenantScopePicker"):
        assert f"function {fn}" in js, fn
    assert "tenants: loadTenants" in js
    for fn in ("refreshMe", "isTenantAdmin", "listTenants", "setTenantScope"):
        assert fn in api, fn
