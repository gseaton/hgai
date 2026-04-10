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
from hgai.models.account import AccountResponse, TokenResponse

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


@router.get("/me", response_model=AccountResponse)
async def get_me(account=Depends(get_current_account)):
    return AccountResponse(**account.model_dump())
