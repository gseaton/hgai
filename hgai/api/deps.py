"""FastAPI dependency injection for HypergraphAI."""

from fastapi import Depends, HTTPException, status

from hgai.core.auth import can_access_graph, can_perform, get_current_account
from hgai.models.account import AccountInDB


async def get_current_active_account(
    account: AccountInDB = Depends(get_current_account),
) -> AccountInDB:
    if account.status != "active":
        raise HTTPException(status_code=400, detail="Inactive account")
    return account


def require_graph_access(operation: str = "read"):
    async def _dep(
        graph_id: str,
        account: AccountInDB = Depends(get_current_active_account),
    ) -> AccountInDB:
        if not can_access_graph(account, graph_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access to graph '{graph_id}' not permitted"
            )
        if not can_perform(account, operation):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation '{operation}' not permitted"
            )
        return account
    return _dep
