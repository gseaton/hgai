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
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    account: AccountInDB = Depends(get_current_active_account),
):
    total, graphs = await engine.list_hypergraphs(
        status=status, tags=tags, skip=skip, limit=limit
    )
    # Filter by account permissions
    if "admin" not in account.roles and "*" not in account.permissions.graphs:
        graphs = [g for g in graphs if g.id in account.permissions.graphs]
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
    existing = await engine.get_hypergraph(data.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Hypergraph '{data.id}' already exists")
    graph = await engine.create_hypergraph(data, created_by=account.username)
    return HypergraphResponse(**graph.model_dump())


@router.get("/{graph_id}", response_model=HypergraphResponse)
async def get_graph(
    graph_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    graph = await engine.get_hypergraph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Hypergraph '{graph_id}' not found")
    return HypergraphResponse(**graph.model_dump())


@router.put("/{graph_id}", response_model=HypergraphResponse)
async def update_graph(
    graph_id: str,
    data: HypergraphUpdate,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    graph = await engine.update_hypergraph(graph_id, data, updated_by=account.username)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Hypergraph '{graph_id}' not found")
    return HypergraphResponse(**graph.model_dump())


@router.delete("/{graph_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_graph(
    graph_id: str,
    account: AccountInDB = Depends(require_graph_access("delete")),
):
    deleted = await engine.delete_hypergraph(graph_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Hypergraph '{graph_id}' not found")


@router.get("/{graph_id}/stats")
async def get_graph_stats(
    graph_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    stats = await engine.get_hypergraph_stats(graph_id)
    return stats


@router.post("/{graph_id}/export")
async def export_graph(
    graph_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    data = await engine.export_hypergraph(graph_id)
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
