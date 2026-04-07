"""Hyperedge CRUD API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hgai.api.deps import require_graph_access
from hgai.core import engine
from hgai.models.account import AccountInDB
from hgai.models.common import PaginatedResponse
from hgai.models.hyperedge import HyperedgeCreate, HyperedgeResponse, HyperedgeUpdate

router = APIRouter(prefix="/graphs/{graph_id}/edges", tags=["hyperedges"])


@router.get("", response_model=PaginatedResponse)
async def list_edges(
    graph_id: str,
    relation: Optional[str] = Query(default=None),
    flavor: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default="active"),
    tags: Optional[List[str]] = Query(default=None),
    node_id: Optional[str] = Query(default=None, description="Filter edges containing this node"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    account: AccountInDB = Depends(require_graph_access("read")),
):
    total, edges = await engine.list_hyperedges(
        graph_id,
        relation=relation,
        flavor=flavor,
        status=status,
        tags=tags,
        node_id=node_id,
        skip=skip,
        limit=limit,
    )
    return PaginatedResponse(
        total=total, skip=skip, limit=limit,
        items=[e.model_dump() for e in edges]
    )


@router.post("", response_model=HyperedgeResponse, status_code=status.HTTP_201_CREATED)
async def create_edge(
    graph_id: str,
    data: HyperedgeCreate,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    graph = await engine.get_hypergraph(graph_id, space_id=None)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Hypergraph '{graph_id}' not found")

    if data.id:
        existing = await engine.get_hyperedge(graph_id, data.id, space_id=None)
        if existing:
            raise HTTPException(
                status_code=409, detail=f"Edge '{data.id}' already exists in graph '{graph_id}'"
            )

    edge = await engine.create_hyperedge(graph_id, data, created_by=account.username, space_id=None)
    return HyperedgeResponse(**edge.model_dump())


@router.get("/{edge_id}", response_model=HyperedgeResponse)
async def get_edge(
    graph_id: str,
    edge_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    edge = await engine.get_hyperedge(graph_id, edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail=f"Edge '{edge_id}' not found")
    return HyperedgeResponse(**edge.model_dump())


@router.put("/{edge_id}", response_model=HyperedgeResponse)
async def update_edge(
    graph_id: str,
    edge_id: str,
    data: HyperedgeUpdate,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    edge = await engine.update_hyperedge(graph_id, edge_id, data, updated_by=account.username, space_id=None)
    if not edge:
        raise HTTPException(status_code=404, detail=f"Edge '{edge_id}' not found")
    return HyperedgeResponse(**edge.model_dump())


@router.delete("/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edge(
    graph_id: str,
    edge_id: str,
    account: AccountInDB = Depends(require_graph_access("delete")),
):
    deleted = await engine.delete_hyperedge(graph_id, edge_id, space_id=None)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Edge '{edge_id}' not found")
