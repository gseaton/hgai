"""Parameterized query (prepared statement) CRUD + execution API endpoints.

No ACL — shared across every authenticated account, the same visibility
model as Hypergraphs and the SHQL example library, not per-account like
Notes. Every route just requires authentication.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from hgai.api.deps import get_current_active_account, parse_sort_param
from hgai.core.parameterized_queries import (
    create_parameterized_query,
    delete_parameterized_query,
    execute_parameterized_query,
    get_parameterized_query,
    list_parameterized_queries,
    update_parameterized_query,
)
from hgai.core.query_templates import QueryTemplateError, parse_parameters
from hgai.models.account import AccountInDB
from hgai.models.common import PaginatedResponse
from hgai.models.parameterized_query import (
    ExecuteParameterizedQueryRequest,
    ParameterizedQueryCreate,
    ParameterizedQueryResponse,
    ParameterizedQueryUpdate,
)

router = APIRouter(prefix="/parameterized-queries", tags=["parameterized-queries"])

PQ_SORT_FIELDS = {"name", "label", "status", "system_created", "system_updated"}


class ParseTemplateRequest(BaseModel):
    shql: str


@router.get("", response_model=PaginatedResponse)
async def list_parameterized_queries_route(
    tags: Optional[List[str]] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Substring match against name, label, or description"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    sort: Optional[str] = Query(default=None, description=f"Comma-separated fields, '-' prefix = descending. Allowed: {sorted(PQ_SORT_FIELDS)}"),
    account: AccountInDB = Depends(get_current_active_account),
):
    total, items = await list_parameterized_queries(
        tags=tags, search=search, skip=skip, limit=limit,
        sort=parse_sort_param(sort, PQ_SORT_FIELDS),
    )
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=[q.model_dump() for q in items])


@router.post("/parse")
async def parse_template_route(
    request: ParseTemplateRequest,
    account: AccountInDB = Depends(get_current_active_account),
):
    """Parse `shql` for /$...$/ placeholders without saving anything — lets
    the editor UI preview detected parameters live as the template is typed."""
    try:
        return {"parameters": [p.model_dump() for p in parse_parameters(request.shql)]}
    except QueryTemplateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("", response_model=ParameterizedQueryResponse, status_code=status.HTTP_201_CREATED)
async def create_parameterized_query_route(
    data: ParameterizedQueryCreate,
    account: AccountInDB = Depends(get_current_active_account),
):
    try:
        return await create_parameterized_query(data, account.username)
    except QueryTemplateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{query_id}", response_model=ParameterizedQueryResponse)
async def get_parameterized_query_route(
    query_id: str,
    account: AccountInDB = Depends(get_current_active_account),
):
    query = await get_parameterized_query(query_id)
    if not query:
        raise HTTPException(status_code=404, detail=f"Parameterized query '{query_id}' not found")
    return query


@router.put("/{query_id}", response_model=ParameterizedQueryResponse)
async def update_parameterized_query_route(
    query_id: str,
    data: ParameterizedQueryUpdate,
    account: AccountInDB = Depends(get_current_active_account),
):
    try:
        result = await update_parameterized_query(query_id, data, account.username)
    except QueryTemplateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not result:
        raise HTTPException(status_code=404, detail=f"Parameterized query '{query_id}' not found")
    return result


@router.delete("/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parameterized_query_route(
    query_id: str,
    account: AccountInDB = Depends(get_current_active_account),
):
    deleted = await delete_parameterized_query(query_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Parameterized query '{query_id}' not found")


@router.post("/{query_id}/execute")
async def execute_parameterized_query_route(
    query_id: str,
    request: ExecuteParameterizedQueryRequest,
    account: AccountInDB = Depends(get_current_active_account),
):
    from hgai_module_shql.parser import SHQLError, SHQLPermissionError

    query = await get_parameterized_query(query_id)
    if not query:
        raise HTTPException(status_code=404, detail=f"Parameterized query '{query_id}' not found")
    try:
        rendered, result = await execute_parameterized_query(query_id, request.values, request.use_cache, account=account)
    except QueryTemplateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SHQLPermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except SHQLError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SHQL execution error: {e}")
    return {"rendered_shql": rendered, "result": result.to_dict()}
