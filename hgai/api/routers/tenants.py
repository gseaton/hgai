"""Tenant management API. See docs/architecture/hypergraph-ai-multi-tenancy-*.md §6 Phase 3.

System admins manage every tenant. A tenant admin (while tenancy is enforced) can
list and read its own tenant. Any other account can read only its own tenant.
Another tenant is reported as not found, never as forbidden.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hgai.api.deps import get_current_active_account
from hgai.core import tenant_engine
from hgai.core.auth import require_system_admin, require_tenant_reader, sees_all_tenants
from hgai.core.tenant_engine import TenancyError, effective_tenant_id
from hgai.models.account import AccountInDB
from hgai.models.common import PaginatedResponse
from hgai.models.tenant import TenantCreate, TenantResponse, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _not_found(tenant_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Tenant '{tenant_id}' not found")


@router.get("", response_model=PaginatedResponse)
async def list_tenants(
    status_filter: str = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    account: AccountInDB = Depends(require_tenant_reader),
):
    if sees_all_tenants(account):
        total, tenants = await tenant_engine.list_tenants(status=status_filter, skip=skip, limit=limit)
    else:
        own = await tenant_engine.get_tenant(effective_tenant_id(account))
        tenants = [own] if own else []
        total = len(tenants)
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=[t.model_dump() for t in tenants])


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(data: TenantCreate, admin: AccountInDB = Depends(require_system_admin)):
    if await tenant_engine.get_tenant(data.id):
        raise HTTPException(status_code=409, detail=f"Tenant '{data.id}' already exists")
    tenant = await tenant_engine.create_tenant(data, created_by=admin.username)
    return TenantResponse(**tenant.model_dump())


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(tenant_id: str, account: AccountInDB = Depends(get_current_active_account)):
    if not sees_all_tenants(account) and effective_tenant_id(account) != tenant_id:
        raise _not_found(tenant_id)
    tenant = await tenant_engine.get_tenant(tenant_id)
    if not tenant:
        raise _not_found(tenant_id)
    return TenantResponse(**tenant.model_dump())


@router.get("/{tenant_id}/usage")
async def get_tenant_usage(tenant_id: str, account: AccountInDB = Depends(get_current_active_account)):
    """What the tenant uses against its quotas: {"usage": {...}, "quotas": {...}}."""
    if not sees_all_tenants(account) and effective_tenant_id(account) != tenant_id:
        raise _not_found(tenant_id)
    if not await tenant_engine.get_tenant(tenant_id):
        raise _not_found(tenant_id)
    return await tenant_engine.tenant_usage(tenant_id)


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str, data: TenantUpdate, admin: AccountInDB = Depends(require_system_admin),
):
    if tenant_id == "default" and data.status == "suspended":
        raise HTTPException(status_code=400, detail="The default tenant cannot be suspended")
    tenant = await tenant_engine.update_tenant(tenant_id, data, updated_by=admin.username)
    if not tenant:
        raise _not_found(tenant_id)
    return TenantResponse(**tenant.model_dump())


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(tenant_id: str, admin: AccountInDB = Depends(require_system_admin)):
    if not await tenant_engine.get_tenant(tenant_id):
        raise _not_found(tenant_id)
    try:
        remaining = await tenant_engine.delete_tenant(tenant_id)
    except TenancyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if remaining:
        raise HTTPException(
            status_code=409,
            detail=f"Tenant '{tenant_id}' is not empty: {remaining}. Move or delete its accounts, spaces and graphs first.",
        )
