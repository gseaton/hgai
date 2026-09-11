"""Semantic inferencing API endpoints.

Relation semantics (which relations are transitive, symmetric, each
other's inverse, or broader/narrower than one another) are never
hardcoded — they're declared as ordinary hyperedges asserting a small,
fixed set of control-vocabulary relations (owl:transitive, owl:symmetric,
owl:inverse-of, skos:narrowerTransitive/broaderTransitive) between
relation-hypernodes. See hgai/core/inference.py.

These routes are direct programmatic access to the same reasoning engine
already wired into HQL/SHQL behind `infer: true` — useful when a caller
wants a single expansion/reachability answer without composing a full
query. Everything here is computed live, at read time; nothing is
persisted.
"""

from datetime import datetime
from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from hgai.api.deps import require_graph_access
from hgai.core import engine
from hgai.core.auth import can_access_graph
from hgai.core.inference import check_transitive, expand_edge_closure, project_inference
from hgai.models.account import AccountInDB
from hgai.models.hypergraph import HypergraphCreate

router = APIRouter(prefix="/graphs/{graph_id}/infer", tags=["inference"])


class TransitiveRequest(BaseModel):
    relation: str = Field(..., description="Relation to walk; must carry an owl:transitive axiom hyperedge")
    start_id: str = Field(..., description="Node (or relation, for axiom-graph walks) to start from")
    end_id: Optional[str] = Field(default=None, description="Required for mode='bool'/'path'")
    mode: str = Field(default="bool", description="'bool' (reachable?), 'closure' (all reachable nodes), or 'path' (ordered hyperedge ids)")


class TransitiveResponse(BaseModel):
    relation: str
    start_id: str
    end_id: Optional[str]
    mode: str
    result: Union[bool, List[str]]


class ExpandRequest(BaseModel):
    edge_id: str = Field(..., description="The hyperedge to expand (id or hyperkey)")


class ExpandResponse(BaseModel):
    source_edge: str
    inferred: List[dict]


@router.post("/transitive", response_model=TransitiveResponse)
async def infer_transitive(
    graph_id: str,
    request: TransitiveRequest,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    if request.mode not in ("bool", "closure", "path"):
        raise HTTPException(status_code=400, detail="mode must be 'bool', 'closure', or 'path'")
    if request.mode in ("bool", "path") and not request.end_id:
        raise HTTPException(status_code=400, detail=f"mode={request.mode!r} requires end_id")

    result = await check_transitive(
        request.relation, [graph_id], request.start_id,
        end_id=request.end_id, mode=request.mode,
    )
    return TransitiveResponse(
        relation=request.relation, start_id=request.start_id, end_id=request.end_id,
        mode=request.mode, result=result,
    )


@router.post("/expand", response_model=ExpandResponse)
async def infer_expand(
    graph_id: str,
    request: ExpandRequest,
    account: AccountInDB = Depends(require_graph_access("read")),
):
    edge = await engine.get_hyperedge(graph_id, request.edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail=f"Edge '{request.edge_id}' not found in graph '{graph_id}'")

    inferred = await expand_edge_closure([edge.model_dump()], [graph_id])
    return ExpandResponse(source_edge=request.edge_id, inferred=inferred)


class ProjectInferenceRequest(BaseModel):
    source_graph_ids: List[str] = Field(..., description="Source hypergraph(s) to run inference over")
    mode: str = Field(default="expand", description="'expand', 'transitive', or 'both'")
    relation: Optional[str] = Field(default=None, description="Required for mode='transitive'/'both'")
    pit: Optional[datetime] = Field(default=None, description="Only consider facts/axioms valid at this instant")
    create_target: bool = Field(default=False, description="Create the target graph (path graph_id) first if it doesn't already exist")
    target_label: Optional[str] = Field(default=None, description="Label for the newly-created target graph, if create_target is true")
    dry_run: bool = Field(default=False, description="Compute and return what would happen without writing anything")


class ProjectInferenceResponse(BaseModel):
    created: int
    skipped: int
    errors: int
    error_details: List[str]
    edges: List[str]
    preview: List[dict]
    dry_run: bool


@router.post("/project", response_model=ProjectInferenceResponse)
async def infer_project(
    graph_id: str,
    request: ProjectInferenceRequest,
    account: AccountInDB = Depends(require_graph_access("write")),
):
    """Materialize inference results from source graph(s) into this (target) graph.

    Unlike /transitive and /expand, this WRITES — every materialized edge
    is persisted through the normal create path, exactly like a
    hand-asserted fact (same hyperkey dedup, same mutations audit trail).
    Safe to re-run: an unchanged source produces zero new edges. Pass
    `dry_run: true` to preview the result (including the target graph
    NOT being created) without writing anything at all.
    """
    for src in request.source_graph_ids:
        if not await can_access_graph(account, src):
            raise HTTPException(status_code=403, detail=f"Access to source graph '{src}' not permitted")

    if request.create_target and not request.dry_run:
        existing = await engine.get_hypergraph(graph_id)
        if not existing:
            await engine.create_hypergraph(
                HypergraphCreate(id=graph_id, label=request.target_label or graph_id),
                created_by=account.username,
            )

    try:
        result = await project_inference(
            request.source_graph_ids, graph_id, request.mode,
            relation=request.relation, pit=request.pit, projected_by=account.username,
            dry_run=request.dry_run,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ProjectInferenceResponse(**result)
