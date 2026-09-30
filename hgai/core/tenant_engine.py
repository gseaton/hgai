"""Tenant engine: tenant CRUD, the default-tenant bootstrap, and tenancy helpers.

Enforcement (the tenant boundary in auth) is a later phase; this module holds the
tenant lifecycle and the pure rules about how an account relates to a tenant.
See docs/architecture/hypergraph-ai-multi-tenancy-*.md.
"""

import logging
from typing import Dict, List, Optional, Tuple

from hgai.db.storage import get_storage
from hgai.models.account import AccountInDB, SystemRole
from hgai.models.common import now_utc
from hgai.models.tenant import (
    DEFAULT_TENANT_ID,
    SYSTEM_GRAPH_IDS,
    TenantCreate,
    TenantInDB,
    TenantStatus,
    TenantUpdate,
)
from hgai_module_storage.filters import TenantFilters, TenantPatch

logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    """A tenant would exceed one of its quotas. REST maps this to 409."""


class TenancyError(ValueError):
    """An account/tenant assignment that breaks a tenancy invariant."""


def is_system_account(account: AccountInDB) -> bool:
    """Any system role (admin or auditor): above tenants, so no tenant of its own."""
    return account.system_role is not None


def effective_tenant_id(account: AccountInDB) -> Optional[str]:
    """The tenant an account acts in: None for system accounts, else its tenant.

    An account stored before multi-tenancy has no tenant and reads as the default one.
    """
    if is_system_account(account):
        return None
    return account.tenant_id or DEFAULT_TENANT_ID


async def tenant_for_new_record(created_by: str, requested: Optional[str] = None) -> Optional[str]:
    """The tenant a newly created space or unowned graph belongs to.

    A tenant account always creates in its own tenant, whatever it asks for. A
    system admin may name a tenant (`requested`), else the default tenant. The
    internal `system` actor (e.g. telemetry's own graph) creates system-level
    records, tenant None, unless it names one.
    """
    if created_by == "system":
        return requested
    from hgai.core.api_keys import tenant_of_key_username
    if (key := await tenant_of_key_username(created_by)) is not None:
        return key[1]   # a key always creates in its own tenant
    raw = await get_storage().accounts.get_by_username(created_by)
    if raw is None:  # e.g. the API-key account, which has no stored row
        return requested or DEFAULT_TENANT_ID
    account = AccountInDB(**raw)
    if is_system_account(account):
        return requested or DEFAULT_TENANT_ID
    return effective_tenant_id(account)


async def tenant_of_owner(username: str) -> Optional[str]:
    """The tenant for data owned by `username` (notes, media, saved queries, chats).

    A tenant account's data is its tenant's; a system account's data is system level (None).
    """
    from hgai.core.api_keys import tenant_of_key_username
    if (key := await tenant_of_key_username(username)) is not None:
        return key[1]
    raw = await get_storage().accounts.get_by_username(username)
    if raw is None:  # e.g. the configured API-key account, which has no stored row
        return None
    account = AccountInDB(**raw)
    return effective_tenant_id(account)


async def check_member_tenant(space_tenant_id: Optional[str], username: str) -> None:
    """Raise TenancyError if `username` is an account of a different tenant than the space.

    System accounts may be members anywhere (they already reach everything).
    Unknown usernames pass: nothing exists to isolate.
    """
    from hgai.core.api_keys import tenant_of_key_username
    if (key := await tenant_of_key_username(username)) is not None:
        if key[0] and key[1] != space_tenant_id:
            raise TenancyError(f"API key '{username}' belongs to a different tenant than the space")
        return
    raw = await get_storage().accounts.get_by_username(username)
    if raw is None:
        return
    account = AccountInDB(**raw)
    if is_system_account(account):
        return
    if effective_tenant_id(account) != space_tenant_id:
        raise TenancyError(f"Account '{username}' belongs to a different tenant than the space")


async def delete_tenant(tenant_id: str) -> Dict[str, int]:
    """Delete an empty tenant. Returns {} on success, else the remaining reference counts.

    The default tenant cannot be deleted.
    """
    if tenant_id == DEFAULT_TENANT_ID:
        raise TenancyError("The default tenant cannot be deleted")
    refs = await get_storage().tenants.count_references(tenant_id)
    remaining = {k: v for k, v in refs.items() if v}
    if remaining:
        return remaining
    await get_storage().tenants.delete(tenant_id)
    return {}


async def validate_account_tenancy(system_role: Optional[str], tenant_id: Optional[str], roles: List[str]) -> None:
    """Raise TenancyError unless (system_role, tenant_id, roles) is a valid assignment.

    A tenant account must name an existing, active tenant; a tenant_admin needs a
    tenant; a system account may have none.
    """
    if system_role:
        return
    if "tenant_admin" in roles and not tenant_id:
        raise TenancyError("A tenant_admin must be assigned to a tenant")
    if not tenant_id:
        raise TenancyError("A non-system account must be assigned to a tenant")
    tenant = await get_storage().tenants.get(tenant_id)
    if tenant is None:
        raise TenancyError(f"Tenant '{tenant_id}' does not exist")
    if tenant.status != TenantStatus.active.value:
        raise TenancyError(f"Tenant '{tenant_id}' is not active")


async def tenant_usage(tenant_id: str) -> Dict[str, Dict[str, Optional[int]]]:
    """Usage against quotas, for the tenant: {"usage": {...}, "quotas": {...}}."""
    tenant = await get_storage().tenants.get(tenant_id)
    quotas = ((tenant.settings if tenant else {}) or {}).get("quotas") or {}
    return {"usage": await get_storage().tenants.usage(tenant_id), "quotas": quotas}


# Creating a node or edge checks its quota, which would cost two lookups per item (a bulk
# import creates thousands). The tenant's limits and a graph's tenant are therefore cached
# for a few seconds: a changed quota takes effect within _QUOTA_TTL seconds.
_QUOTA_TTL = 5.0
_quota_cache: Dict[str, Any] = {}


def clear_quota_cache() -> None:
    _quota_cache.clear()


async def _cached(key, loader):
    import time
    now = time.monotonic()
    hit = _quota_cache.get(key)
    if hit and hit[0] > now:
        return hit[1]
    value = await loader()
    _quota_cache[key] = (now + _QUOTA_TTL, value)
    return value


async def _limits(tenant_id: str) -> Dict[str, Any]:
    async def load():
        tenant = await get_storage().tenants.get(tenant_id)
        return ((tenant.settings if tenant else None) or {}).get("quotas") or {}
    return await _cached(("limits", tenant_id), load)


async def enforce_quota(tenant_id: Optional[str], resource: str, adding: int = 1) -> None:
    """Raise QuotaExceededError if adding `adding` of `resource` would pass the tenant's limit.

    No-op unless tenancy is enforced, the record belongs to a tenant, and that tenant has a
    limit for the resource (so an unlimited tenant pays for no counting at all).
    """
    from hgai.core.auth import multitenancy_on

    if tenant_id is None or not multitenancy_on():
        return
    limit = (await _limits(tenant_id)).get(f"max_{resource}")
    if limit is None:
        return
    used = (await get_storage().tenants.usage(tenant_id, only=[resource]))[resource]
    if used + adding > limit:
        raise QuotaExceededError(
            f"Tenant '{tenant_id}' has reached its limit of {limit} {resource} (currently {used})"
        )


async def enforce_quota_for_graph(graph_id: str, space_id: Optional[str], resource: str) -> None:
    """Quota check for something created inside a graph (nodes, edges): the graph's tenant pays."""
    from hgai.core.auth import multitenancy_on

    if not multitenancy_on():
        return

    async def load():
        graph = await get_storage().hypergraphs.get(graph_id, space_id)
        return graph.tenant_id if graph is not None else None
    await enforce_quota(await _cached(("graph", graph_id, space_id), load), resource)


async def create_tenant(data: TenantCreate, created_by: str) -> TenantInDB:
    now = now_utc()
    doc = data.model_dump()
    doc.update(system_created=now, system_updated=now, created_by=created_by, version=1)
    return await get_storage().tenants.create(doc)


async def get_tenant(tenant_id: str) -> Optional[TenantInDB]:
    return await get_storage().tenants.get(tenant_id)


async def list_tenants(status: Optional[str] = None, skip: int = 0, limit: int = 50) -> Tuple[int, List[TenantInDB]]:
    return await get_storage().tenants.list(TenantFilters(status=status), skip=skip, limit=limit)


async def update_tenant(tenant_id: str, data: TenantUpdate, updated_by: str) -> Optional[TenantInDB]:
    d = data.model_dump(exclude_none=True)
    patch = TenantPatch(
        label=d.get("label"), description=d.get("description"), status=d.get("status"),
        settings=d.get("settings"), attributes=d.get("attributes"), updated_by=updated_by,
    )
    clear_quota_cache()
    return await get_storage().tenants.update(tenant_id, patch)


async def ensure_default_tenant() -> bool:
    """Create the default tenant if missing. Returns True if created."""
    if await get_storage().tenants.get(DEFAULT_TENANT_ID):
        return False
    await create_tenant(
        TenantCreate(id=DEFAULT_TENANT_ID, label="Default", description="Default tenant"),
        created_by="system",
    )
    return True


async def run_tenancy_migration() -> Dict[str, int]:
    """Ensure the default tenant exists and stamp every pre-multi-tenancy record.

    Idempotent; called on every startup after the admin account is bootstrapped.
    """
    created = await ensure_default_tenant()
    counts = await get_storage().migrate_tenancy(DEFAULT_TENANT_ID, SYSTEM_GRAPH_IDS)
    if created:
        logger.info(f"Default tenant '{DEFAULT_TENANT_ID}' created")
    return counts
