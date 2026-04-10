"""Mesh REST API router."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from hgai.core.auth import require_admin
from hgai.db.storage import get_storage
from hgai.models.common import PaginatedResponse, now_utc

from .models import MeshCreate, MeshResponse, MeshUpdate

router = APIRouter(prefix="/meshes", tags=["meshes"])


# ─── Registry CRUD ────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse)
async def list_meshes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _admin=Depends(require_admin),
):
    from hgai_module_storage.filters import MeshFilters
    total, docs = await get_storage().meshes.list(MeshFilters(), skip=skip, limit=limit)
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=docs)


@router.post("", response_model=MeshResponse, status_code=status.HTTP_201_CREATED)
async def create_mesh(data: MeshCreate, admin=Depends(require_admin)):
    existing = await get_storage().meshes.get(data.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Mesh '{data.id}' already exists")

    now = now_utc()
    doc = {
        **data.model_dump(),
        "system_created": now,
        "system_updated": now,
        "created_by": admin.username,
        "version": 1,
    }
    result = await get_storage().meshes.create(doc)
    return MeshResponse(**result)


@router.get("/{mesh_id}", response_model=MeshResponse)
async def get_mesh(mesh_id: str, _admin=Depends(require_admin)):
    doc = await get_storage().meshes.get(mesh_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Mesh '{mesh_id}' not found")
    return MeshResponse(**doc)


@router.put("/{mesh_id}", response_model=MeshResponse)
async def update_mesh(mesh_id: str, data: MeshUpdate, admin=Depends(require_admin)):
    update_fields = {k: v for k, v in data.model_dump(exclude_none=True).items() if k != "version"}
    update_fields["system_updated"] = now_utc()
    result = await get_storage().meshes.update(mesh_id, update_fields)
    if not result:
        raise HTTPException(status_code=404, detail=f"Mesh '{mesh_id}' not found")
    return MeshResponse(**result)


@router.delete("/{mesh_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mesh(mesh_id: str, _admin=Depends(require_admin)):
    deleted = await get_storage().meshes.delete(mesh_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Mesh '{mesh_id}' not found")


# ─── Active Mesh Operations ───────────────────────────────────────────────────

@router.get("/{mesh_id}/ping")
async def ping_mesh(mesh_id: str, _admin=Depends(require_admin)):
    """Health-check all servers in a mesh."""
    from .engine import ping_mesh as _ping_mesh
    try:
        return {"mesh_id": mesh_id, "results": await _ping_mesh(mesh_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{mesh_id}/sync")
async def sync_mesh(mesh_id: str, _admin=Depends(require_admin)):
    """Refresh each server's graph list from the live remotes."""
    from .engine import sync_mesh_graphs
    try:
        return await sync_mesh_graphs(mesh_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{mesh_id}/query")
async def query_mesh(
    mesh_id: str,
    body: dict,
    _admin=Depends(require_admin),
):
    """Fan out an HQL or SHQL query across all servers in a mesh and merge results.

    Provide either an 'hql' key (HQL query text) or an 'shql' key (SHQL query text).
    """
    from .engine import federated_hql, federated_shql
    use_cache = body.get("use_cache", True)

    if "hql" in body:
        try:
            return await federated_hql(mesh_id, body["hql"], use_cache=use_cache)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    if "shql" in body:
        try:
            return await federated_shql(mesh_id, body["shql"], use_cache=use_cache)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    raise HTTPException(status_code=400, detail="Request body must contain an 'hql' or 'shql' field")


@router.api_route(
    "/{mesh_id}/servers/{server_id}/proxy/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
)
async def proxy_to_server(
    mesh_id: str,
    server_id: str,
    path: str,
    request: Request,
    _admin=Depends(require_admin),
):
    """Forward a request to a specific server in a mesh.

    The request method, path, and body are forwarded as-is.
    Example: POST /meshes/my-mesh/servers/srv-1/proxy/api/v1/graphs
    """
    from .engine import proxy_request
    try:
        body = await request.json() if request.method in ("POST", "PUT", "PATCH") else None
    except Exception:
        body = None
    params = dict(request.query_params)
    try:
        return await proxy_request(mesh_id, server_id, request.method, path, body=body, params=params)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
