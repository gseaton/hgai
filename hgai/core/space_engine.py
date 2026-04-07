"""Space engine — CRUD and membership operations for HypergraphAI spaces."""

from typing import Any, Dict, List, Optional, Tuple

from hgai.db.mongodb import col_hyperedges, col_hypergraphs, col_hypernodes, col_spaces
from hgai.models.common import now_utc
from hgai.models.hypergraph import HypergraphInDB
from hgai.models.space import SpaceCreate, SpaceInDB, SpaceRole, SpaceUpdate


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
    await col_spaces().insert_one(doc)
    doc.pop("_id", None)
    return SpaceInDB(**doc)


async def get_space(space_id: str) -> Optional[SpaceInDB]:
    doc = await col_spaces().find_one({"id": space_id})
    if not doc:
        return None
    doc.pop("_id", None)
    return SpaceInDB(**doc)


async def list_spaces(
    username: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[int, List[SpaceInDB]]:
    """List spaces. If username given, scoped to spaces where user is a member."""
    query: Dict[str, Any] = {"status": "active"}
    if username:
        query["members.username"] = username

    total = await col_spaces().count_documents(query)
    cursor = col_spaces().find(query).skip(skip).limit(limit).sort("system_created", -1)
    docs = await cursor.to_list(length=limit)
    spaces = []
    for doc in docs:
        doc.pop("_id", None)
        spaces.append(SpaceInDB(**doc))
    return total, spaces


async def update_space(
    space_id: str, data: SpaceUpdate, updated_by: str
) -> Optional[SpaceInDB]:
    update_fields = {
        k: v for k, v in data.model_dump(exclude_none=True).items() if k != "version"
    }
    update_fields["system_updated"] = now_utc()
    update_fields["updated_by"] = updated_by

    result = await col_spaces().find_one_and_update(
        {"id": space_id},
        {"$set": update_fields, "$inc": {"version": 1}},
        return_document=True,
    )
    if not result:
        return None
    result.pop("_id", None)
    return SpaceInDB(**result)


async def delete_space(space_id: str, delete_graphs: bool = False) -> bool:
    """Delete a space. If delete_graphs=True, also delete all contained graphs and
    their nodes/edges. Otherwise, graphs are unassigned (space_id set to None)."""
    result = await col_spaces().delete_one({"id": space_id})
    if not result.deleted_count:
        return False

    if delete_graphs:
        from hgai.core.cache import invalidate_cache
        async for doc in col_hypergraphs().find({"space_id": space_id}, {"id": 1}):
            gid = doc["id"]
            await col_hypernodes().delete_many({"hypergraph_id": gid})
            await col_hyperedges().delete_many({"hypergraph_id": gid})
            await invalidate_cache(gid)
        await col_hypergraphs().delete_many({"space_id": space_id})
    else:
        await col_hypergraphs().update_many(
            {"space_id": space_id},
            {"$set": {"space_id": None, "system_updated": now_utc()}},
        )
    return True


# ─── Membership ───────────────────────────────────────────────────────────────

async def add_member(space_id: str, username: str, role: str) -> Optional[SpaceInDB]:
    """Add or update a member in a space. Replaces any existing role for the user."""
    now = now_utc()
    # Remove existing entry for this user, then add fresh entry
    await col_spaces().update_one(
        {"id": space_id},
        {"$pull": {"members": {"username": username}}},
    )
    result = await col_spaces().find_one_and_update(
        {"id": space_id},
        {
            "$push": {"members": {"username": username, "role": role}},
            "$set": {"system_updated": now},
            "$inc": {"version": 1},
        },
        return_document=True,
    )
    if not result:
        return None
    result.pop("_id", None)
    return SpaceInDB(**result)


async def remove_member(space_id: str, username: str) -> Optional[SpaceInDB]:
    result = await col_spaces().find_one_and_update(
        {"id": space_id},
        {
            "$pull": {"members": {"username": username}},
            "$set": {"system_updated": now_utc()},
            "$inc": {"version": 1},
        },
        return_document=True,
    )
    if not result:
        return None
    result.pop("_id", None)
    return SpaceInDB(**result)


async def get_member_role(space_id: str, username: str) -> Optional[str]:
    """Return the role of a member within a space, or None if not a member."""
    doc = await col_spaces().find_one(
        {"id": space_id, "members.username": username},
        {"members.$": 1},
    )
    if not doc or not doc.get("members"):
        return None
    return doc["members"][0].get("role")


# ─── Graph assignment ─────────────────────────────────────────────────────────

async def get_space_for_graph(graph_id: str) -> Optional[str]:
    """Return the space_id of a graph, or None if unowned."""
    doc = await col_hypergraphs().find_one({"id": graph_id}, {"space_id": 1})
    if not doc:
        return None
    return doc.get("space_id")


async def list_space_graphs(
    space_id: str, skip: int = 0, limit: int = 50
) -> Tuple[int, List[HypergraphInDB]]:
    query = {"space_id": space_id, "status": "active"}
    total = await col_hypergraphs().count_documents(query)
    cursor = col_hypergraphs().find(query).skip(skip).limit(limit).sort("system_created", -1)
    docs = await cursor.to_list(length=limit)
    graphs = []
    for doc in docs:
        doc.pop("_id", None)
        graphs.append(HypergraphInDB(**doc))
    return total, graphs


async def assign_graph_to_space(graph_id: str, space_id: str) -> bool:
    """Assign an unowned graph to a space. Only operates on graphs with space_id=None."""
    result = await col_hypergraphs().update_one(
        {"id": graph_id, "space_id": None},
        {"$set": {"space_id": space_id, "system_updated": now_utc()}},
    )
    return result.modified_count > 0


async def remove_graph_from_space(graph_id: str, space_id: str) -> bool:
    """Unassign a graph from its space. Requires the current space_id to prevent mis-targeting."""
    result = await col_hypergraphs().update_one(
        {"id": graph_id, "space_id": space_id},
        {"$set": {"space_id": None, "system_updated": now_utc()}},
    )
    return result.modified_count > 0


async def get_accessible_graph_ids_via_spaces(username: str) -> List[str]:
    """Return all graph IDs the user can access through space membership."""
    space_id_cursor = col_spaces().find(
        {"members.username": username, "status": "active"},
        {"id": 1},
    )
    space_ids = [doc["id"] async for doc in space_id_cursor]
    if not space_ids:
        return []
    graph_cursor = col_hypergraphs().find(
        {"space_id": {"$in": space_ids}, "status": "active"},
        {"id": 1},
    )
    return [doc["id"] async for doc in graph_cursor]
