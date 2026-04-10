"""Account management API endpoints (admin only)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hgai.core.auth import hash_password, require_admin
from hgai.db.storage import get_storage
from hgai.models.account import AccountCreate, AccountInDB, AccountResponse, AccountUpdate
from hgai.models.common import PaginatedResponse, now_utc
from hgai.models.space import SpaceRole, UpdateMemberRoleRequest
from hgai_module_storage.filters import AccountFilters

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=PaginatedResponse)
async def list_accounts(
    status: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _admin=Depends(require_admin),
):
    filters = AccountFilters(status=status)
    total, docs = await get_storage().accounts.list(filters, skip=skip, limit=limit)
    accounts = []
    for doc in docs:
        doc.pop("password_hash", None)
        accounts.append(doc)
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=accounts)


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    data: AccountCreate,
    admin=Depends(require_admin),
):
    if await get_storage().accounts.exists(data.username):
        raise HTTPException(status_code=409, detail=f"Account '{data.username}' already exists")

    now = now_utc()
    doc = {
        **data.model_dump(exclude={"password"}),
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
async def get_account(username: str, _admin=Depends(require_admin)):
    doc = await get_storage().accounts.get_by_username(username)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Account '{username}' not found")
    doc.pop("password_hash", None)
    return AccountResponse(**doc)


@router.put("/{username}", response_model=AccountResponse)
async def update_account(
    username: str,
    data: AccountUpdate,
    admin=Depends(require_admin),
):
    update_fields = {k: v for k, v in data.model_dump(exclude_none=True).items() if k != "password"}
    if data.password:
        update_fields["password_hash"] = hash_password(data.password)
    update_fields["system_updated"] = now_utc()
    update_fields["updated_by"] = admin.username

    result = await get_storage().accounts.update(username, update_fields)
    if not result:
        raise HTTPException(status_code=404, detail=f"Account '{username}' not found")
    result.pop("password_hash", None)
    return AccountResponse(**result)


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    username: str,
    admin=Depends(require_admin),
):
    if username == admin.username:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    deleted = await get_storage().accounts.delete(username)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Account '{username}' not found")
    # Remove deleted user from all space member arrays
    await get_storage().spaces.remove_user_from_all_spaces(username)


@router.get("/{username}/spaces", response_model=PaginatedResponse)
async def list_account_spaces(
    username: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _admin=Depends(require_admin),
):
    """List all spaces the account is a member of."""
    if not await get_storage().accounts.exists(username):
        raise HTTPException(status_code=404, detail=f"Account '{username}' not found")
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
    _admin=Depends(require_admin),
):
    """Assign an account to a space with the given role (admin shortcut)."""
    if not await get_storage().accounts.exists(username):
        raise HTTPException(status_code=404, detail=f"Account '{username}' not found")
    from hgai.core.space_engine import add_member, get_space
    if not await get_space(space_id):
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
    space = await add_member(space_id, username, body.role)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
    return {"space_id": space_id, "username": username, "role": body.role}


@router.delete("/{username}/spaces/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_account_from_space(
    username: str,
    space_id: str,
    _admin=Depends(require_admin),
):
    """Remove an account from a space (admin shortcut)."""
    from hgai.core.space_engine import remove_member
    space = await remove_member(space_id, username)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
