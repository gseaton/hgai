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
    """Execute an SHQL (Semantic Hypergraph Query Language) query."""
    from .engine import execute_shql, SHQLResult
    from .parser import SHQLError
    try:
        result = await execute_shql(request.shql, use_cache=request.use_cache)
        return result.to_dict()
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
