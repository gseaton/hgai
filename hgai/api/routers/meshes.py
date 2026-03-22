"""Mesh management API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hgai.core.auth import require_admin
from hgai.db.mongodb import col_meshes
from hgai.models.common import PaginatedResponse, now_utc
from hgai.models.mesh import MeshCreate, MeshResponse, MeshUpdate

router = APIRouter(prefix="/meshes", tags=["meshes"])


@router.get("", response_model=PaginatedResponse)
async def list_meshes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _admin=Depends(require_admin),
):
    total = await col_meshes().count_documents({})
    cursor = col_meshes().find({}).skip(skip).limit(limit).sort("system_created", -1)
    docs = await cursor.to_list(length=limit)
    meshes = []
    for doc in docs:
        doc.pop("_id", None)
        meshes.append(doc)
    return PaginatedResponse(total=total, skip=skip, limit=limit, items=meshes)


@router.post("", response_model=MeshResponse, status_code=status.HTTP_201_CREATED)
async def create_mesh(data: MeshCreate, admin=Depends(require_admin)):
    existing = await col_meshes().find_one({"id": data.id})
    if existing:
        raise HTTPException(status_code=409, detail=f"Mesh '{data.id}' already exists")

    now = now_utc()
    doc = {**data.model_dump(), "system_created": now, "system_updated": now, "created_by": admin.username, "version": 1}
    await col_meshes().insert_one(doc)
    doc.pop("_id", None)
    return MeshResponse(**doc)


@router.get("/{mesh_id}", response_model=MeshResponse)
async def get_mesh(mesh_id: str, _admin=Depends(require_admin)):
    doc = await col_meshes().find_one({"id": mesh_id})
    if not doc:
        raise HTTPException(status_code=404, detail=f"Mesh '{mesh_id}' not found")
    doc.pop("_id", None)
    return MeshResponse(**doc)


@router.put("/{mesh_id}", response_model=MeshResponse)
async def update_mesh(mesh_id: str, data: MeshUpdate, admin=Depends(require_admin)):
    update_fields = {k: v for k, v in data.model_dump(exclude_none=True).items()}
    update_fields["system_updated"] = now_utc()
    result = await col_meshes().find_one_and_update(
        {"id": mesh_id},
        {"$set": update_fields, "$inc": {"version": 1}},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail=f"Mesh '{mesh_id}' not found")
    result.pop("_id", None)
    return MeshResponse(**result)


@router.delete("/{mesh_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mesh(mesh_id: str, _admin=Depends(require_admin)):
    result = await col_meshes().delete_one({"id": mesh_id})
    if not result.deleted_count:
        raise HTTPException(status_code=404, detail=f"Mesh '{mesh_id}' not found")
