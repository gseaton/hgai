"""SHQL REST API router."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hgai.core.auth import get_current_account
from hgai.models.account import AccountInDB

router = APIRouter(prefix="/shql", tags=["shql"])


class SHQLRequest(BaseModel):
    shql: str
    use_cache: bool = True


class SHQLValidateRequest(BaseModel):
    shql: str


@router.post("/query")
async def execute_shql_query(
    request: SHQLRequest,
    account: AccountInDB = Depends(get_current_account),
):
    """Execute an SHQL (Semantic Hypergraph Query Language) query.

    The caller needs the `query` operation on every graph in `from:` (403 otherwise)."""
    from .engine import execute_shql, SHQLResult
    from .parser import SHQLError, SHQLPermissionError
    try:
        result = await execute_shql(request.shql, use_cache=request.use_cache, account=account)
        return result.to_dict()
    except SHQLPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except SHQLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SHQL execution error: {e}")


@router.post("/validate")
async def validate_shql_query(
    request: SHQLValidateRequest,
    account: AccountInDB = Depends(get_current_account),
):
    """Validate an SHQL query without executing it."""
    from .parser import parse_shql, validate_shql, SHQLError
    try:
        shql   = parse_shql(request.shql)
        errors = validate_shql(shql)
        return {"valid": len(errors) == 0, "errors": errors}
    except SHQLError as e:
        return {"valid": False, "errors": [str(e)]}


@router.post("/cache/invalidate")
async def clear_cache(
    graph_id: str = None,
    account: AccountInDB = Depends(get_current_account),
):
    """Flush the shared query result cache (used by SHQL query execution).

    Formerly lived under the now-removed HQL module's router — relocated
    here rather than dropped, since the cache itself (`hgai.core.cache`,
    `query_cache` collection) was never HQL-specific.
    """
    from hgai.core.cache import invalidate_cache
    count = await invalidate_cache(graph_id)
    return {"invalidated": count}


class SHQLHistoryEntryRequest(BaseModel):
    shql: str


@router.get("/history")
async def get_shql_history(
    account: AccountInDB = Depends(get_current_account),
):
    """The caller's own last 50 submitted queries, newest first.

    History is per-account (never shared) and server-side, so it follows
    the account across browsers/devices and survives a server restart —
    unlike the client-only localStorage list this replaced.
    """
    from .history import list_history
    return {"items": await list_history(account.username)}


@router.post("/history")
async def add_shql_history_entry(
    request: SHQLHistoryEntryRequest,
    account: AccountInDB = Depends(get_current_account),
):
    """Record one submitted query. Called by the UI right when a query is
    run, independent of whether it succeeds — this is a history of what
    was *submitted*, not of what executed cleanly."""
    from .history import add_history_entry
    entry = await add_history_entry(account.username, request.shql)
    return entry


@router.delete("/history")
async def clear_shql_history(
    account: AccountInDB = Depends(get_current_account),
):
    """Delete all of the caller's own history entries."""
    from .history import clear_history
    count = await clear_history(account.username)
    return {"deleted": count}
