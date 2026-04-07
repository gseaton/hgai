"""Hypergraph CRUD API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hgai.api.deps import get_current_active_account, require_graph_access
from hgai.core import engine
from hgai.core.auth import require_admin
from hgai.models.account import AccountInDB
from hgai.models.common import PaginatedResponse
from hgai.models.hypergraph import (
    HypergraphCreate,
    HypergraphResponse,
    HypergraphUpdate,
)

router = APIRouter(prefix="/graphs", tags=["hypergraphs"])


@router.get("", response_model=PaginatedResponse)
async def list_graphs(
    status: Optional[str] = Query(default="active"),
    tags: Optional[List[str]] = Query(default=None),
    space_id: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    account: AccountInDB = Depends(get_current_active_account),
):
    total, graphs = await engine.list_hypergraphs(
        status=status, tags=tags, space_id=space_id, skip=skip, limit=limit
    )
    # Filter by account permissions (direct + space membership)
    if "admin" not in account.roles and "*" not in account.permissions.graphs:
        from hgai.core.space_engine import get_accessible_graph_ids_via_spaces
        space_graph_ids = set(await get_accessible_graph_ids_via_spaces(account.username))
        direct_ids = set(account.permissions.graphs)
        allowed = direct_ids | space_graph_ids
        graphs = [g for g in graphs if g.id in allowed]
        total = len(graphs)
    return PaginatedResponse(
        total=total, skip=skip, limit=limit,
        items=[g.model_dump() for g in graphs]
    )


@router.post("", response_model=HypergraphResponse, status_code=status.HTTP_201_CREATED)
async def create_graph(
    data: HypergraphCreate,
    account: AccountInDB = Depends(get_current_active_account),
):
    """Create an unowned (no space) hypergraph. For space-owned graphs use POST /spaces/{space_id}/graphs."""
    existing = await engine.get_hypergraph(data.id, space_id=None)
    if existing:
        raise HTTPException(status_code=409, detail=f"Hypergraph '{data.id}' already exists")
    graph = await engine.create_hypergraph(data, created_by=account.username)
    return HypergraphResponse(**graph.model_dump())


@router.get("/{graph_id}", response_model=HypergraphResponse)
async def get_graph(
    graph_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    """Get an unowned hypergraph. For space-owned graphs use GET /spaces/{space_id}/graphs/{graph_id}."""
    graph = await engine.get_hypergraph(graph_id, space_id=None)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Hypergraph '{graph_id}' not found")
    return HypergraphResponse(**graph.model_dump())


@router.put("/{graph_id}", response_model=HypergraphResponse)
async def update_graph(
    graph_id: str,
    data: HypergraphUpdate,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    graph = await engine.update_hypergraph(graph_id, data, updated_by=account.username, space_id=None)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Hypergraph '{graph_id}' not found")
    return HypergraphResponse(**graph.model_dump())


@router.delete("/{graph_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_graph(
    graph_id: str,
    account: AccountInDB = Depends(require_graph_access("delete")),
):
    deleted = await engine.delete_hypergraph(graph_id, space_id=None)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Hypergraph '{graph_id}' not found")


@router.get("/{graph_id}/stats")
async def get_graph_stats(
    graph_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    stats = await engine.get_hypergraph_stats(graph_id, space_id=None)
    return stats


@router.post("/{graph_id}/export")
async def export_graph(
    graph_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    data = await engine.export_hypergraph(graph_id, space_id=None)
    if not data:
        raise HTTPException(status_code=404, detail=f"Hypergraph '{graph_id}' not found")
    return data


@router.post("/{graph_id}/import")
async def import_graph(
    graph_id: str,
    data: dict,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    result = await engine.import_hypergraph_data(graph_id, data, created_by=account.username)
    return result
