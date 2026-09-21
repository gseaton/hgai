"""FastAPI dependency injection for HypergraphAI."""

from typing import List, Optional, Set, Tuple

from fastapi import Depends, HTTPException, status

from hgai.core.auth import (
    PermissionDeniedError,
    check_graph_permission,
    check_space_role,
    get_current_account,
)
from hgai.models.account import AccountInDB
from hgai.models.space import SpaceRole


def parse_sort_param(sort: Optional[str], allowed_fields: Set[str]) -> Optional[List[Tuple[str, int]]]:
    """Parse a comma-separated multi-column sort spec into [(field, direction), ...].

    Format: "field1,-field2,field3" — a leading '-' means descending; fields
    are applied in the order given (first = primary sort key). Raises 400 if
    a field isn't in `allowed_fields`.
    """
    if not sort:
        return None
    result: List[Tuple[str, int]] = []
    for part in sort.split(","):
        part = part.strip()
        if not part:
            continue
        direction = -1 if part.startswith("-") else 1
        field = part[1:] if part.startswith("-") else part
        if field not in allowed_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sort field '{field}'. Allowed: {sorted(allowed_fields)}",
            )
        result.append((field, direction))
    return result or None


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
        try:
            await check_graph_permission(account, graph_id, operation, space_id=space_id)
        except PermissionDeniedError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        return account
    return _dep


def require_space_role(minimum_role: SpaceRole = SpaceRole.viewer):
    async def _dep(
        space_id: str,
        account: AccountInDB = Depends(get_current_active_account),
    ) -> AccountInDB:
        try:
            await check_space_role(account, space_id, minimum_role.value)
        except PermissionDeniedError as e:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        return account
    return _dep
