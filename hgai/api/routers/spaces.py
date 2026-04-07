"""Spaces CRUD, membership, and space-scoped graph/node/edge API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hgai.api.deps import get_current_active_account, require_graph_access, require_space_role
from hgai.core import engine, space_engine
from hgai.models.account import AccountInDB
from hgai.models.common import PaginatedResponse
from hgai.models.hyperedge import HyperedgeCreate, HyperedgeResponse, HyperedgeUpdate
from hgai.models.hypergraph import HypergraphCreate, HypergraphResponse, HypergraphUpdate
from hgai.models.hypernode import HypernodeCreate, HypernodeResponse, HypernodeUpdate
from hgai.models.space import (
    AddMemberRequest,
    SpaceCreate,
    SpaceResponse,
    SpaceRole,
    SpaceUpdate,
    UpdateMemberRoleRequest,
)

router = APIRouter(prefix="/spaces", tags=["spaces"])


@router.get("", response_model=PaginatedResponse)
async def list_spaces(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    account: AccountInDB = Depends(get_current_active_account),
):
    username = None if "admin" in account.roles else account.username
    total, spaces = await space_engine.list_spaces(username=username, skip=skip, limit=limit)
    return PaginatedResponse(
        total=total, skip=skip, limit=limit,
        items=[s.model_dump() for s in spaces]
    )


@router.post("", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED)
async def create_space(
    data: SpaceCreate,
    account: AccountInDB = Depends(get_current_active_account),
):
    existing = await space_engine.get_space(data.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Space '{data.id}' already exists")
    space = await space_engine.create_space(data, created_by=account.username)
    return SpaceResponse(**space.model_dump())


@router.get("/{space_id}", response_model=SpaceResponse)
async def get_space(
    space_id: str,
    account: AccountInDB = Depends(require_space_role(SpaceRole.viewer)),
):
    space = await space_engine.get_space(space_id)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
    return SpaceResponse(**space.model_dump())


@router.put("/{space_id}", response_model=SpaceResponse)
async def update_space(
    space_id: str,
    data: SpaceUpdate,
    account: AccountInDB = Depends(require_space_role(SpaceRole.admin)),
):
    space = await space_engine.update_space(space_id, data, updated_by=account.username)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
    return SpaceResponse(**space.model_dump())


@router.delete("/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_space(
    space_id: str,
    delete_graphs: bool = Query(default=False),
    account: AccountInDB = Depends(require_space_role(SpaceRole.owner)),
):
    deleted = await space_engine.delete_space(space_id, delete_graphs=delete_graphs)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")


# ─── Membership ───────────────────────────────────────────────────────────────

@router.get("/{space_id}/members")
async def list_members(
    space_id: str,
    account: AccountInDB = Depends(require_space_role(SpaceRole.viewer)),
):
    space = await space_engine.get_space(space_id)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
    return {"members": [m.model_dump() for m in space.members]}


@router.post("/{space_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    space_id: str,
    body: AddMemberRequest,
    account: AccountInDB = Depends(require_space_role(SpaceRole.admin)),
):
    space = await space_engine.add_member(space_id, body.username, body.role)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
    return SpaceResponse(**space.model_dump())


@router.put("/{space_id}/members/{username}")
async def update_member_role(
    space_id: str,
    username: str,
    body: UpdateMemberRoleRequest,
    account: AccountInDB = Depends(require_space_role(SpaceRole.admin)),
):
    space = await space_engine.add_member(space_id, username, body.role)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
    return SpaceResponse(**space.model_dump())


@router.delete("/{space_id}/members/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    space_id: str,
    username: str,
    account: AccountInDB = Depends(require_space_role(SpaceRole.admin)),
):
    space = await space_engine.remove_member(space_id, username)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")


# ─── Space-scoped graph CRUD ──────────────────────────────────────────────────

@router.get("/{space_id}/graphs", response_model=PaginatedResponse)
async def list_space_graphs(
    space_id: str,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    account: AccountInDB = Depends(require_space_role(SpaceRole.viewer)),
):
    total, graphs = await space_engine.list_space_graphs(space_id, skip=skip, limit=limit)
    return PaginatedResponse(
        total=total, skip=skip, limit=limit,
        items=[g.model_dump() for g in graphs]
    )


@router.post("/{space_id}/graphs", response_model=HypergraphResponse, status_code=status.HTTP_201_CREATED)
async def create_space_graph(
    space_id: str,
    data: HypergraphCreate,
    account: AccountInDB = Depends(require_space_role(SpaceRole.member)),
):
    space = await space_engine.get_space(space_id)
    if not space:
        raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
    existing = await engine.get_hypergraph(data.id, space_id=space_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Graph '{data.id}' already exists in space '{space_id}'")
    # Force space_id onto the document
    data_dict = data.model_dump()
    data_dict["space_id"] = space_id
    graph = await engine.create_hypergraph(HypergraphCreate(**data_dict), created_by=account.username)
    return HypergraphResponse(**graph.model_dump())


@router.get("/{space_id}/graphs/{graph_id}", response_model=HypergraphResponse)
async def get_space_graph(
    space_id: str,
    graph_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    graph = await engine.get_hypergraph(graph_id, space_id=space_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_id}' not found in space '{space_id}'")
    return HypergraphResponse(**graph.model_dump())


@router.put("/{space_id}/graphs/{graph_id}", response_model=HypergraphResponse)
async def update_space_graph(
    space_id: str,
    graph_id: str,
    data: HypergraphUpdate,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    graph = await engine.update_hypergraph(graph_id, data, updated_by=account.username, space_id=space_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_id}' not found in space '{space_id}'")
    return HypergraphResponse(**graph.model_dump())


@router.delete("/{space_id}/graphs/{graph_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_space_graph(
    space_id: str,
    graph_id: str,
    account: AccountInDB = Depends(require_graph_access("delete")),
):
    deleted = await engine.delete_hypergraph(graph_id, space_id=space_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_id}' not found in space '{space_id}'")


@router.get("/{space_id}/graphs/{graph_id}/stats")
async def get_space_graph_stats(
    space_id: str,
    graph_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    return await engine.get_hypergraph_stats(graph_id, space_id=space_id)


@router.post("/{space_id}/graphs/{graph_id}/export")
async def export_space_graph(
    space_id: str,
    graph_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    data = await engine.export_hypergraph(graph_id, space_id=space_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_id}' not found in space '{space_id}'")
    return data


@router.post("/{space_id}/graphs/{graph_id}/import")
async def import_space_graph(
    space_id: str,
    graph_id: str,
    data: dict,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    return await engine.import_hypergraph_data(graph_id, data, created_by=account.username, space_id=space_id)


# ─── Space-scoped nodes ───────────────────────────────────────────────────────

@router.get("/{space_id}/graphs/{graph_id}/nodes", response_model=PaginatedResponse)
async def list_space_nodes(
    space_id: str,
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
        graph_id, node_type=node_type, status=status,
        tags=tags, search=search, skip=skip, limit=limit, space_id=space_id,
    )
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=[n.model_dump() for n in nodes])


@router.post("/{space_id}/graphs/{graph_id}/nodes", response_model=HypernodeResponse, status_code=status.HTTP_201_CREATED)
async def create_space_node(
    space_id: str,
    graph_id: str,
    data: HypernodeCreate,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    existing = await engine.get_hypernode(graph_id, data.id, space_id=space_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Node '{data.id}' already exists in graph '{graph_id}'")
    graph = await engine.get_hypergraph(graph_id, space_id=space_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_id}' not found in space '{space_id}'")
    node = await engine.create_hypernode(graph_id, data, created_by=account.username, space_id=space_id)
    return HypernodeResponse(**node.model_dump())


@router.get("/{space_id}/graphs/{graph_id}/nodes/{node_id}", response_model=HypernodeResponse)
async def get_space_node(
    space_id: str,
    graph_id: str,
    node_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    node = await engine.get_hypernode(graph_id, node_id, space_id=space_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return HypernodeResponse(**node.model_dump())


@router.put("/{space_id}/graphs/{graph_id}/nodes/{node_id}", response_model=HypernodeResponse)
async def update_space_node(
    space_id: str,
    graph_id: str,
    node_id: str,
    data: HypernodeUpdate,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    node = await engine.update_hypernode(graph_id, node_id, data, updated_by=account.username, space_id=space_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")
    return HypernodeResponse(**node.model_dump())


@router.delete("/{space_id}/graphs/{graph_id}/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_space_node(
    space_id: str,
    graph_id: str,
    node_id: str,
    account: AccountInDB = Depends(require_graph_access("delete")),
):
    deleted = await engine.delete_hypernode(graph_id, node_id, space_id=space_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Node '{node_id}' not found")


# ─── Space-scoped edges ───────────────────────────────────────────────────────

@router.get("/{space_id}/graphs/{graph_id}/edges", response_model=PaginatedResponse)
async def list_space_edges(
    space_id: str,
    graph_id: str,
    relation: Optional[str] = Query(default=None),
    flavor: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default="active"),
    tags: Optional[List[str]] = Query(default=None),
    node_id: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    account: AccountInDB = Depends(require_graph_access("read")),
):
    total, edges = await engine.list_hyperedges(
        graph_id, relation=relation, flavor=flavor, status=status,
        tags=tags, node_id=node_id, skip=skip, limit=limit, space_id=space_id,
    )
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=[e.model_dump() for e in edges])


@router.post("/{space_id}/graphs/{graph_id}/edges", response_model=HyperedgeResponse, status_code=status.HTTP_201_CREATED)
async def create_space_edge(
    space_id: str,
    graph_id: str,
    data: HyperedgeCreate,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    graph = await engine.get_hypergraph(graph_id, space_id=space_id)
    if not graph:
        raise HTTPException(status_code=404, detail=f"Graph '{graph_id}' not found in space '{space_id}'")
    if data.id:
        existing = await engine.get_hyperedge(graph_id, data.id, space_id=space_id)
        if existing:
            raise HTTPException(status_code=409, detail=f"Edge '{data.id}' already exists in graph '{graph_id}'")
    edge = await engine.create_hyperedge(graph_id, data, created_by=account.username, space_id=space_id)
    return HyperedgeResponse(**edge.model_dump())


@router.get("/{space_id}/graphs/{graph_id}/edges/{edge_id}", response_model=HyperedgeResponse)
async def get_space_edge(
    space_id: str,
    graph_id: str,
    edge_id: str,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    edge = await engine.get_hyperedge(graph_id, edge_id, space_id=space_id)
    if not edge:
        raise HTTPException(status_code=404, detail=f"Edge '{edge_id}' not found")
    return HyperedgeResponse(**edge.model_dump())


@router.put("/{space_id}/graphs/{graph_id}/edges/{edge_id}", response_model=HyperedgeResponse)
async def update_space_edge(
    space_id: str,
    graph_id: str,
    edge_id: str,
    data: HyperedgeUpdate,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    edge = await engine.update_hyperedge(graph_id, edge_id, data, updated_by=account.username, space_id=space_id)
    if not edge:
        raise HTTPException(status_code=404, detail=f"Edge '{edge_id}' not found")
    return HyperedgeResponse(**edge.model_dump())


@router.delete("/{space_id}/graphs/{graph_id}/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_space_edge(
    space_id: str,
    graph_id: str,
    edge_id: str,
    account: AccountInDB = Depends(require_graph_access("delete")),
):
    deleted = await engine.delete_hyperedge(graph_id, edge_id, space_id=space_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Edge '{edge_id}' not found")
