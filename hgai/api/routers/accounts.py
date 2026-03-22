"""Account management API endpoints (admin only)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hgai.core.auth import hash_password, require_admin
from hgai.db.mongodb import col_accounts
from hgai.models.account import AccountCreate, AccountInDB, AccountResponse, AccountUpdate
from hgai.models.common import PaginatedResponse, now_utc

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=PaginatedResponse)
async def list_accounts(
    status: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _admin=Depends(require_admin),
):
    query = {}
    if status:
        query["status"] = status
    total = await col_accounts().count_documents(query)
    cursor = col_accounts().find(query).skip(skip).limit(limit).sort("system_created", -1)
    docs = await cursor.to_list(length=limit)
    accounts = []
    for doc in docs:
        doc.pop("_id", None)
        doc.pop("password_hash", None)
        accounts.append(doc)
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=accounts)


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    data: AccountCreate,
    admin=Depends(require_admin),
):
    existing = await col_accounts().find_one({"username": data.username})
    if existing:
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
    await col_accounts().insert_one(doc)
    doc.pop("_id", None)
    doc.pop("password_hash", None)
    return AccountResponse(**doc)


@router.get("/{username}", response_model=AccountResponse)
async def get_account(username: str, _admin=Depends(require_admin)):
    doc = await col_accounts().find_one({"username": username})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Account '{username}' not found")
    doc.pop("_id", None)
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

    result = await col_accounts().find_one_and_update(
        {"username": username},
        {"$set": update_fields, "$inc": {"version": 1}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"Account '{username}' not found")
    result.pop("_id", None)
    result.pop("password_hash", None)
    return AccountResponse(**result)


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    username: str,
    admin=Depends(require_admin),
):
    if username == admin.username:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    result = await col_accounts().delete_one({"username": username})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail=f"Account '{username}' not found")
