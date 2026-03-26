"""HQL REST API router."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from hgai.api.deps import get_current_active_account
from hgai.core.cache import invalidate_cache
from hgai.models.account import AccountInDB

router = APIRouter(prefix="/query", tags=["query"])


class HQLRequest(BaseModel):
    hql: str = Field(..., description="HQL query text (YAML or JSON)")
    use_cache: bool = Field(default=True)


class HQLValidateRequest(BaseModel):
    hql: str = Field(..., description="HQL query text to validate")


@router.post("")
async def run_query(
    request: HQLRequest,
    account: AccountInDB = Depends(get_current_active_account),
):
    from .engine import execute_hql, HQLError
    try:
        result = await execute_hql(request.hql, use_cache=request.use_cache)
        return result.to_dict()
    except HQLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query execution error: {e}")


@router.post("/validate")
async def validate_query(
    request: HQLValidateRequest,
    account: AccountInDB = Depends(get_current_active_account),
):
    from .engine import parse_hql, validate_hql, HQLError
    try:
        hql = parse_hql(request.hql)
        errors = validate_hql(hql)
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "parsed": hql,
        }
    except HQLError as e:
        return {"valid": False, "errors": [str(e)], "parsed": None}


@router.post("/cache/invalidate")
async def clear_cache(
    graph_id: str = None,
    account: AccountInDB = Depends(get_current_active_account),
):
    count = await invalidate_cache(graph_id)
    return {"invalidated": count}
