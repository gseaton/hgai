"""Authentication API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from hgai.core.auth import (
    authenticate_account,
    create_access_token,
    get_current_account,
)
from hgai.db.storage import get_storage
from hgai.core.auth import multitenancy_on
from hgai.core.tenant_engine import effective_tenant_id
from hgai.models.account import MeResponse, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    account = await authenticate_account(form.username, form.password)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = create_access_token(account.username, account.roles)

    # Update last_login
    await get_storage().accounts.record_login(account.username)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        username=account.username,
        roles=account.roles,
    )


@router.get("/me", response_model=MeResponse)
async def get_me(account=Depends(get_current_account)):
    enabled = multitenancy_on()
    label = None
    tenant_id = effective_tenant_id(account) if enabled else None
    if tenant_id:
        tenant = await get_storage().tenants.get(tenant_id)
        label = tenant.label if tenant else tenant_id
    return MeResponse(**account.model_dump(), multitenancy_enabled=enabled, tenant_label=label)
