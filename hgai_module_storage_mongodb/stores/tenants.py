"""MongoDB tenant store implementation."""

from typing import Any, Dict, List, Optional, Tuple

from hgai.models.tenant import TenantInDB
from hgai_module_storage.backend import TenantStore
from hgai_module_storage.filters import TenantFilters, TenantPatch

from ..connection import get_db


def _col():
    return get_db()["tenants"]


class MongoTenantStore(TenantStore):

    async def create(self, doc: Dict[str, Any]) -> TenantInDB:
        await _col().insert_one(doc)
        doc.pop("_id", None)
        return TenantInDB(**doc)

    async def get(self, tenant_id: str) -> Optional[TenantInDB]:
        raw = await _col().find_one({"id": tenant_id})
        if not raw:
            return None
        raw.pop("_id", None)
        return TenantInDB(**raw)

    async def list(
        self, filters: TenantFilters, skip: int = 0, limit: int = 50
    ) -> Tuple[int, List[TenantInDB]]:
        query: Dict[str, Any] = {}
        if filters.status:
            query["status"] = filters.status
        total = await _col().count_documents(query)
        docs = await _col().find(query).skip(skip).limit(limit).sort("id", 1).to_list(length=limit)
        tenants = []
        for doc in docs:
            doc.pop("_id", None)
            tenants.append(TenantInDB(**doc))
        return total, tenants

    async def update(self, tenant_id: str, patch: TenantPatch) -> Optional[TenantInDB]:
        from hgai.models.common import now_utc
        update_fields: Dict[str, Any] = {}
        for attr in ("label", "description", "status", "settings", "attributes"):
            val = getattr(patch, attr, None)
            if val is not None:
                update_fields[attr] = val
        update_fields["system_updated"] = now_utc()
        if patch.updated_by:
            update_fields["updated_by"] = patch.updated_by
        result = await _col().find_one_and_update(
            {"id": tenant_id},
            {"$set": update_fields, "$inc": {"version": 1}},
            return_document=True,
        )
        if not result:
            return None
        result.pop("_id", None)
        return TenantInDB(**result)

    async def count_references(self, tenant_id: str) -> Dict[str, int]:
        db = get_db()
        return {
            name: await db[name].count_documents({"tenant_id": tenant_id})
            for name in ("accounts", "spaces", "hypergraphs", "api_keys")
        }

    async def usage(self, tenant_id: str, only: Optional[List[str]] = None) -> Dict[str, int]:
        db = get_db()
        wanted = set(only) if only is not None else {"accounts", "spaces", "graphs", "nodes", "edges"}
        out: Dict[str, int] = {}
        for key, coll in (("accounts", "accounts"), ("spaces", "spaces"), ("graphs", "hypergraphs")):
            if key in wanted:
                out[key] = await db[coll].count_documents({"tenant_id": tenant_id})
        if wanted & {"nodes", "edges"}:
            rows = await db["hypergraphs"].aggregate([
                {"$match": {"tenant_id": tenant_id}},
                {"$group": {"_id": None, "nodes": {"$sum": "$node_count"}, "edges": {"$sum": "$edge_count"}}},
            ]).to_list(length=1)
            row = rows[0] if rows else {}
            for key in ("nodes", "edges"):
                if key in wanted:
                    out[key] = int(row.get(key) or 0)
        return out

    async def delete(self, tenant_id: str) -> bool:
        result = await _col().delete_one({"id": tenant_id})
        return result.deleted_count > 0
