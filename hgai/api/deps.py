"""FastAPI dependency injection for HypergraphAI."""

from typing import Optional

from fastapi import Depends, HTTPException, status

from hgai.core.auth import can_access_graph, can_perform, get_current_account
from hgai.models.account import AccountInDB
from hgai.models.space import SpaceRole


async def get_current_active_account(
    account: AccountInDB = Depends(get_current_account),
) -> AccountInDB:
    if account.status != "active":
        raise HTTPException(status_code=400, detail="Inactive account")
    return account


def require_graph_access(operation: str = "read"):
    async def _dep(
        graph_id: str,
        space_id: Optional[str] = None,  # injected from path on nested /spaces/{space_id}/graphs/... routes
        account: AccountInDB = Depends(get_current_active_account),
    ) -> AccountInDB:
        if not await can_access_graph(account, graph_id, space_id=space_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to graph '{graph_id}' not permitted"
            )
        if not await can_perform(account, operation, graph_id=graph_id, space_id=space_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation '{operation}' not permitted"
            )
        return account
    return _dep


_ROLE_RANK = {
    SpaceRole.viewer: 0,
    SpaceRole.member: 1,
    SpaceRole.admin: 2,
    SpaceRole.owner: 3,
}


def require_space_role(minimum_role: SpaceRole = SpaceRole.viewer):
    async def _dep(
        space_id: str,
        account: AccountInDB = Depends(get_current_active_account),
    ) -> AccountInDB:
        if "admin" in account.roles:
            return account
        from hgai.core.space_engine import get_member_role
        role_str = await get_member_role(space_id, account.username)
        if role_str is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not a member of space '{space_id}'"
            )
        role = SpaceRole(role_str)
        if _ROLE_RANK.get(role, -1) < _ROLE_RANK[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Space role '{minimum_role.value}' or higher required"
            )
        return account
    return _dep
