"""Tenant-scoped API key management.

A key belongs to one tenant and acts as an `agent` account of it, limited to the
operations it was issued with. System admins manage keys of any tenant; a tenant admin
manages its own tenant's. The secret is returned once, on creation. Keys only work while
tenancy is enforced (HGAI_MULTITENANCY_ENABLED), since nothing else would confine them.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hgai.core import api_keys, tenant_engine
from hgai.core.auth import (
    multitenancy_on,
    require_tenant_admin,
    require_tenant_reader,
    tenant_scope,
)
from hgai.models.account import AccountInDB
from hgai.models.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyResponse
from hgai.models.common import PaginatedResponse

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _public(key) -> dict:
    return ApiKeyResponse(**key.model_dump()).model_dump()


@router.get("", response_model=PaginatedResponse)
async def list_api_keys(
    tenant_id: Optional[str] = Query(default=None, description="System admin only: list one tenant's keys"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    actor: AccountInDB = Depends(require_tenant_reader),
):
    scope = tenant_scope(actor)
    total, keys = await api_keys_store().list(scope if scope is not None else tenant_id, skip=skip, limit=limit)
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=[_public(k) for k in keys])


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(data: ApiKeyCreate, actor: AccountInDB = Depends(require_tenant_admin)):
    if not multitenancy_on():
        raise HTTPException(status_code=409, detail="Tenant API keys need HGAI_MULTITENANCY_ENABLED=true")
    scope = tenant_scope(actor)
    if scope is not None:
        if data.tenant_id not in (None, scope):
            raise HTTPException(status_code=403, detail="Only a system admin can issue a key for another tenant")
        tenant_id = scope
    else:
        if not data.tenant_id:
            raise HTTPException(status_code=400, detail="tenant_id is required")
        tenant_id = data.tenant_id
    tenant = await tenant_engine.get_tenant(tenant_id)
    if tenant is None or tenant.status != "active":
        raise HTTPException(status_code=400, detail=f"Tenant '{tenant_id}' does not exist or is not active")
    key, raw = await api_keys.create_api_key(data, tenant_id, actor.username)
    return ApiKeyCreated(**ApiKeyResponse(**key.model_dump()).model_dump(), key=raw)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(key_id: str, actor: AccountInDB = Depends(require_tenant_admin)):
    key = await api_keys_store().get(key_id)
    scope = tenant_scope(actor)
    if key is None or (scope is not None and key.tenant_id != scope):
        raise HTTPException(status_code=404, detail=f"API key '{key_id}' not found")
    await api_keys_store().delete(key_id)


def api_keys_store():
    from hgai.db.storage import get_storage
    return get_storage().api_keys
