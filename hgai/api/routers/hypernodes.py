"""Hypernode CRUD API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hgai.api.deps import require_graph_access
from hgai.core import engine
from hgai.models.account import AccountInDB
from hgai.models.common import PaginatedResponse
from hgai.models.hypernode import HypernodeCreate, HypernodeResponse, HypernodeUpdate

router = APIRouter(prefix="/graphs/{graph_id}/nodes", tags=["hypernodes"])


@router.get("", response_model=PaginatedResponse)
async def list_nodes(
    graph_id: str,
    node_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default="active"),
    tags: Optional[List[str]] = Query(default=None),
    search: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    account: AccountInDB = Depends(require_graph_access("read")),
):
    total, nodes = await engine.list_hypernodes(
        graph_id,
        node_type=node_type,
        status=status,
        tags=tags,
        search=search,
        skip=skip,
        limit=limit,
    )
    return PaginatedResponse(
        total=total, skip=skip, limit=limit,
        items=[n.model_dump() for n in nodes]
    )


@router.post("", response_model=HypernodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(
    graph_id: str,
    data: HypernodeCreate,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    existing = await engine.get_hypernode(graph_id, data.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Node '{data.id}' already exists in graph '{graph_id}'")
    graph = await engine.get_hypergraph(graph_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Hypergraph '{graph_id}' not found")
    node = await engine.create_hypernode(graph_id, data, created_by=account.username)
    return HypernodeResponse(**node.model_dump())


@router.get("/{node_id}", response_model=HypernodeResponse)
async def get_node(
    graph_id: str,
    node_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    node = await engine.get_hypernode(graph_id, node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return HypernodeResponse(**node.model_dump())


@router.put("/{node_id}", response_model=HypernodeResponse)
async def update_node(
    graph_id: str,
    node_id: str,
    data: HypernodeUpdate,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    node = await engine.update_hypernode(graph_id, node_id, data, updated_by=account.username)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return HypernodeResponse(**node.model_dump())


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    graph_id: str,
    node_id: str,
    account: AccountInDB = Depends(require_graph_access("delete")),
):
    deleted = await engine.delete_hypernode(graph_id, node_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
