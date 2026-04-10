"""Space engine — CRUD and membership operations for HypergraphAI spaces."""

from typing import Any, Dict, List, Optional, Tuple

from hgai.db.storage import get_storage
from hgai.models.common import now_utc
from hgai.models.hypergraph import HypergraphInDB
from hgai.models.space import SpaceCreate, SpaceInDB, SpaceRole, SpaceUpdate
from hgai_module_storage.filters import SpaceFilters, SpacePatch


async def create_space(data: SpaceCreate, created_by: str) -> SpaceInDB:
    """Create a space. The creator is automatically added as owner."""
    now = now_utc()
    doc = data.model_dump()

    # Ensure creator is present as owner
    members = doc.get("members", [])
    if not any(m.get("username") == created_by for m in members):
        members.insert(0, {"username": created_by, "role": SpaceRole.owner})
    else:
        # Upgrade any existing entry for creator to owner
        for m in members:
            if m.get("username") == created_by:
                m["role"] = SpaceRole.owner

    doc["members"] = members
    doc.update(
        system_created=now,
        system_updated=now,
        created_by=created_by,
        version=1,
    )
    return await get_storage().spaces.create(doc)


async def get_space(space_id: str) -> Optional[SpaceInDB]:
    return await get_storage().spaces.get(space_id)


async def list_spaces(
    username: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[int, List[SpaceInDB]]:
    """List spaces. If username given, scoped to spaces where user is a member."""
    filters = SpaceFilters(username=username)
    return await get_storage().spaces.list(filters, skip=skip, limit=limit)


async def update_space(
    space_id: str, data: SpaceUpdate, updated_by: str
) -> Optional[SpaceInDB]:
    dumped = {
        k: v for k, v in data.model_dump(exclude_none=True).items() if k != "version"
    }
    patch = SpacePatch(
        label=dumped.get("label"),
        description=dumped.get("description"),
        status=dumped.get("status"),
        attributes=dumped.get("attributes"),
        updated_by=updated_by,
    )
    return await get_storage().spaces.update(space_id, patch)


async def delete_space(space_id: str, delete_graphs: bool = False) -> bool:
    """Delete a space. If delete_graphs=True, also delete all contained graphs and
    their nodes/edges. Otherwise, graphs are unassigned (space_id set to None)."""
    deleted = await get_storage().spaces.delete(space_id)
    if not deleted:
        return False

    if delete_graphs:
        from hgai.core.cache import invalidate_cache
        graph_ids = await get_storage().hypergraphs.list_ids_for_space(space_id)
        for gid in graph_ids:
            ref = f"{space_id}/{gid}"
            await get_storage().hypernodes.delete_by_graph(ref)
            await get_storage().hyperedges.delete_by_graph(ref)
            await invalidate_cache(gid)
            # Delete the graph document itself
            await get_storage().hypergraphs.delete(gid, space_id)
    else:
        await get_storage().spaces.update_many_hypergraphs(
            space_id,
            {"$set": {"space_id": None, "system_updated": now_utc()}},
        )
    return True


# ─── Membership ───────────────────────────────────────────────────────────────

async def add_member(space_id: str, username: str, role: str) -> Optional[SpaceInDB]:
    """Add or update a member in a space. Replaces any existing role for the user."""
    return await get_storage().spaces.add_member(space_id, username, role)


async def remove_member(space_id: str, username: str) -> Optional[SpaceInDB]:
    return await get_storage().spaces.remove_member(space_id, username)


async def get_member_role(space_id: str, username: str) -> Optional[str]:
    """Return the role of a member within a space, or None if not a member."""
    return await get_storage().spaces.get_member_role(space_id, username)


# ─── Graph assignment ─────────────────────────────────────────────────────────

async def get_space_for_graph(graph_id: str) -> Optional[str]:
    """Return the space_id of a graph, or None if unowned."""
    return await get_storage().spaces.get_space_for_graph(graph_id)


async def list_space_graphs(
    space_id: str, skip: int = 0, limit: int = 50
) -> Tuple[int, List[HypergraphInDB]]:
    return await get_storage().hypergraphs.list_space_graphs(space_id, skip=skip, limit=limit)


async def assign_graph_to_space(graph_id: str, space_id: str) -> bool:
    """Assign an unowned graph to a space. Only operates on graphs with space_id=None."""
    return await get_storage().hypergraphs.reassign_space(graph_id, old_space_id=None, new_space_id=space_id)


async def remove_graph_from_space(graph_id: str, space_id: str) -> bool:
    """Unassign a graph from its space. Requires the current space_id to prevent mis-targeting."""
    return await get_storage().hypergraphs.reassign_space(graph_id, old_space_id=space_id, new_space_id=None)


async def get_accessible_graph_ids_via_spaces(username: str) -> List[str]:
    """Return all graph IDs the user can access through space membership."""
    space_ids = await get_storage().spaces.list_active_space_ids_for_user(username)
    if not space_ids:
        return []
    return await get_storage().hypergraphs.list_by_space_ids(space_ids, status="active")
