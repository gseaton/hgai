"""Hypergraph CRUD API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from hgai.api.transfer_http import export_response, read_export_body, read_rdf_body, run_import
from hgai.api.deps import get_current_active_account, parse_sort_param, require_graph_access
from hgai.core import engine
from hgai.core.auth import can_access_graph, can_perform, require_admin
from hgai.core.rdf_import import SUPPORTED_FORMATS
from hgai.models.account import AccountInDB
from hgai.models.common import PaginatedResponse
from hgai.models.hypergraph import (
    HypergraphCreate,
    HypergraphResponse,
    HypergraphUpdate,
)

router = APIRouter(prefix="/graphs", tags=["hypergraphs"])

GRAPH_SORT_FIELDS = {"id", "label", "type", "space_id", "node_count", "edge_count", "status", "system_created", "system_updated"}


@router.get("", response_model=PaginatedResponse)
async def list_graphs(
    status: Optional[str] = Query(default="active"),
    tags: Optional[List[str]] = Query(default=None),
    space_id: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    sort: Optional[str] = Query(default=None, description=f"Comma-separated fields, '-' prefix = descending. Allowed: {sorted(GRAPH_SORT_FIELDS)}"),
    account: AccountInDB = Depends(get_current_active_account),
):
    total, graphs = await engine.list_hypergraphs(
        status=status, tags=tags, space_id=space_id, search=search, skip=skip, limit=limit,
        sort=parse_sort_param(sort, GRAPH_SORT_FIELDS),
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


@router.api_route("/{graph_id}/export", methods=["GET", "POST"])
async def export_graph(
    graph_id: str,
    fmt: str = Query(default="json", alias="format", pattern="^(json|yaml)$",
                     description="`yaml` downloads hgai-hypergraph-<id>-<timestamp>.export.yml"),
    account: AccountInDB = Depends(require_graph_access("read")),
):
    """Export a hypergraph (definition + all nodes and edges) for import into another instance."""
    data = await engine.export_hypergraph(graph_id, space_id=None)
    if not data:
        raise HTTPException(status_code=404, detail=f"Hypergraph '{graph_id}' not found")
    return export_response(data, graph_id, fmt)


@router.post("/import")
async def import_new_graph(
    request: Request,
    graph_id: Optional[str] = Query(default=None, description="Target id; defaults to the id stored in the file"),
    mode: str = Query(default="create", pattern="^(create|merge)$",
                      description="create: fail if the hypergraph exists; merge: load into it (creating it if missing), skipping items already present"),
    account: AccountInDB = Depends(get_current_active_account),
):
    """Import an export file (raw YAML/JSON request body) as an unowned hypergraph,
    creating the hypergraph from the file's own definition."""
    doc = await read_export_body(request)
    target = graph_id or doc["graph"].get("id")
    if target and mode == "merge" and await engine.get_hypergraph(target, space_id=None):
        if not await can_access_graph(account, target) or not await can_perform(account, "write", graph_id=target):
            raise HTTPException(status_code=403, detail=f"Write access to graph '{target}' not permitted")
    return await run_import(doc, account.username, target, None, mode)


@router.post("/import/rdf")
async def import_rdf_graph(
    request: Request,
    graph_id: str = Query(..., description="Target hypergraph id (RDF files have no embedded id, unlike an hgai_export file)"),
    label: Optional[str] = Query(default=None, description="Display label for a newly-created hypergraph; defaults to graph_id"),
    format: str = Query(..., description=f"RDF serialization of the request body — one of: {', '.join(SUPPORTED_FORMATS)}"),
    mode: str = Query(default="create", pattern="^(create|merge)$",
                      description="create: fail if the hypergraph exists; merge: load into it (creating it if missing), skipping items already present"),
    account: AccountInDB = Depends(get_current_active_account),
):
    """Import an RDF file (Turtle, RDF/XML, JSON-LD or Notation3 — raw request body) as an
    unowned hypergraph. Every subject and every resource-valued object becomes a hypernode;
    every literal-valued triple becomes an attribute on its subject; every resource-valued
    triple becomes a `hub` hyperedge (relation = predicate, members = [subject, object])."""
    doc = await read_rdf_body(request, graph_id, format, label)
    if mode == "merge" and await engine.get_hypergraph(graph_id, space_id=None):
        if not await can_access_graph(account, graph_id) or not await can_perform(account, "write", graph_id=graph_id):
            raise HTTPException(status_code=403, detail=f"Write access to graph '{graph_id}' not permitted")
    return await run_import(doc, account.username, graph_id, None, mode)


@router.post("/{graph_id}/import")
async def import_graph(
    graph_id: str,
    data: dict,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    """Import an export document (JSON body) into an EXISTING hypergraph, skipping items already present."""
    from hgai.core import transfer

    try:
        doc = transfer.validate_export(data)
    except transfer.ExportFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return await run_import(doc, account.username, graph_id, None, "merge", require_existing_graph=True)
