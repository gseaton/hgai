"""Account management API endpoints.

System admins manage every account. While tenancy is enforced, a tenant admin
manages the accounts of its own tenant only: it cannot see or touch another
tenant's (or any system) account, create an account elsewhere, or grant
`admin` / `system_role`. Another tenant's account is reported as not found.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hgai.core.auth import (
    hash_password,
    is_system_admin,
    multitenancy_on,
    require_tenant_admin,
    require_tenant_reader,
    tenant_scope,
)
from hgai.core.tenant_engine import TenancyError, enforce_quota, check_member_tenant, validate_account_tenancy
from hgai.models.tenant import DEFAULT_TENANT_ID
from hgai.db.storage import get_storage
from hgai.models.account import AccountCreate, AccountInDB, AccountResponse, AccountUpdate
from hgai.models.common import PaginatedResponse, now_utc
from hgai.models.space import SpaceRole, UpdateMemberRoleRequest
from hgai_module_storage.filters import AccountFilters

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _not_found(username: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Account '{username}' not found")


async def _load_target(username: str, actor: AccountInDB) -> Dict[str, Any]:
    """The stored account `actor` is allowed to manage, else 404."""
    doc = await get_storage().accounts.get_by_username(username)
    if not doc:
        raise _not_found(username)
    scope = tenant_scope(actor)
    if scope is not None:
        target = AccountInDB(**doc)
        if is_system_admin(target) or (target.tenant_id or DEFAULT_TENANT_ID) != scope:
            raise _not_found(username)
    return doc


def _reject_privilege(actor: AccountInDB, system_role, roles, tenant_id) -> None:
    """A tenant admin may not grant system rights or move an account out of its tenant."""
    if is_system_admin(actor):
        return
    if system_role or (roles and "admin" in roles):
        raise HTTPException(status_code=403, detail="Only a system admin can grant system roles")
    if tenant_id is not None and tenant_id != tenant_scope(actor):
        raise HTTPException(status_code=403, detail="Only a system admin can assign another tenant")


async def _scoped_space(space_id: str, actor: AccountInDB):
    from hgai.core.space_engine import get_space
    space = await get_space(space_id)
    scope = tenant_scope(actor)
    if not space or (scope is not None and space.tenant_id != scope):
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
    return space


@router.get("", response_model=PaginatedResponse)
async def list_accounts(
    status: Optional[str] = Query(default=None),
    tenant_id: Optional[str] = Query(default=None, description="System admin only: list one tenant's accounts"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    actor: AccountInDB = Depends(require_tenant_reader),
):
    scope = tenant_scope(actor)
    filters = AccountFilters(status=status, tenant_id=scope if scope is not None else tenant_id)
    total, docs = await get_storage().accounts.list(filters, skip=skip, limit=limit)
    accounts = []
    for doc in docs:
        doc.pop("password_hash", None)
        accounts.append(doc)
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=accounts)


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    data: AccountCreate,
    admin=Depends(require_tenant_admin),
):
    if await get_storage().accounts.exists(data.username):
        raise HTTPException(status_code=409, detail=f"Account '{data.username}' already exists")

    _reject_privilege(admin, data.system_role, data.roles, data.tenant_id)
    # A tenant admin always creates in its own tenant.
    scope = tenant_scope(admin)
    tenant_id = scope if scope is not None else data.tenant_id
    # Every non-system account belongs to a tenant: default unless one is named.
    if data.system_role is None and not tenant_id:
        tenant_id = DEFAULT_TENANT_ID
    if multitenancy_on():
        try:
            await validate_account_tenancy(data.system_role, tenant_id, data.roles)
        except TenancyError as e:
            raise HTTPException(status_code=400, detail=str(e))

    if not data.system_role:
        await enforce_quota(tenant_id, "accounts")

    now = now_utc()
    doc = {
        **data.model_dump(exclude={"password"}),
        "tenant_id": None if data.system_role else tenant_id,
        "password_hash": hash_password(data.password),
        "system_created": now,
        "system_updated": now,
        "created_by": admin.username,
        "version": 1,
        "last_login": None,
    }
    result = await get_storage().accounts.create(doc)
    result.pop("password_hash", None)
    return AccountResponse(**result)


@router.get("/{username}", response_model=AccountResponse)
async def get_account(username: str, actor: AccountInDB = Depends(require_tenant_reader)):
    doc = await _load_target(username, actor)
    doc.pop("password_hash", None)
    return AccountResponse(**doc)


@router.put("/{username}", response_model=AccountResponse)
async def update_account(
    username: str,
    data: AccountUpdate,
    admin=Depends(require_tenant_admin),
):
    existing = await _load_target(username, admin)
    _reject_privilege(admin, data.system_role, data.roles, data.tenant_id)

    update_fields = {k: v for k, v in data.model_dump(exclude_none=True).items() if k not in ("password", "version")}
    if data.password:
        update_fields["password_hash"] = hash_password(data.password)
    update_fields["system_updated"] = now_utc()
    update_fields["updated_by"] = admin.username

    # Re-check the assignment that would result, and drop memberships that would
    # otherwise end up spanning tenants.
    new_roles = update_fields.get("roles", existing.get("roles", []))
    new_system_role = update_fields.get("system_role", existing.get("system_role"))
    new_tenant = update_fields.get("tenant_id", existing.get("tenant_id"))
    if new_system_role is None and "admin" in new_roles:
        new_system_role = "system_admin"
    if multitenancy_on() and ({"roles", "system_role", "tenant_id"} & set(update_fields)):
        try:
            await validate_account_tenancy(new_system_role, new_tenant or DEFAULT_TENANT_ID, new_roles)
        except TenancyError as e:
            raise HTTPException(status_code=400, detail=str(e))
    moved = "tenant_id" in update_fields and update_fields["tenant_id"] != existing.get("tenant_id")

    result = await get_storage().accounts.update(username, update_fields)
    if not result:
        raise _not_found(username)
    if moved:
        await get_storage().spaces.remove_user_from_all_spaces(username)
    result.pop("password_hash", None)
    return AccountResponse(**result)


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    username: str,
    admin=Depends(require_tenant_admin),
):
    if username == admin.username:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    await _load_target(username, admin)
    deleted = await get_storage().accounts.delete(username)
    if not deleted:
        raise _not_found(username)
    # Remove deleted user from all space member arrays
    await get_storage().spaces.remove_user_from_all_spaces(username)


@router.get("/{username}/spaces", response_model=PaginatedResponse)
async def list_account_spaces(
    username: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    actor: AccountInDB = Depends(require_tenant_reader),
):
    """List all spaces the account is a member of."""
    await _load_target(username, actor)
    from hgai.core.space_engine import list_spaces
    total, spaces = await list_spaces(username=username, skip=skip, limit=limit)
    return PaginatedResponse(
        total=total, skip=skip, limit=limit,
        items=[s.model_dump() for s in spaces],
    )


@router.post("/{username}/spaces/{space_id}", status_code=status.HTTP_201_CREATED)
async def assign_account_to_space(
    username: str,
    space_id: str,
    body: UpdateMemberRoleRequest,
    actor: AccountInDB = Depends(require_tenant_admin),
):
    """Assign an account to a space with the given role (admin shortcut)."""
    await _load_target(username, actor)
    space = await _scoped_space(space_id, actor)
    if multitenancy_on():
        try:
            await check_member_tenant(space.tenant_id, username)
        except TenancyError as e:
            raise HTTPException(status_code=400, detail=str(e))
    from hgai.core.space_engine import add_member
    space = await add_member(space_id, username, body.role)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
    return {"space_id": space_id, "username": username, "role": body.role}


@router.delete("/{username}/spaces/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_account_from_space(
    username: str,
    space_id: str,
    actor: AccountInDB = Depends(require_tenant_admin),
):
    """Remove an account from a space (admin shortcut)."""
    await _scoped_space(space_id, actor)
    from hgai.core.space_engine import remove_member
    space = await remove_member(space_id, username)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
