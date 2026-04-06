"""HypergraphAI Query Engine - HQL (Hypergraph Query Language).

HQL is a YAML-based declarative query language for querying hypergraphs.

Example:
    hql:
      from: my-graph
      match:
        type: hyperedge
        relation: has-member
      where:
        tags:
          - original
      return:
        - members
        - attributes
      as: result
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import yaml

from hgai.db.mongodb import col_hyperedges, col_hypernodes, col_hypergraphs

_SKOS_FIELDS = ("skos_broader", "skos_narrower", "skos_related")


class HQLError(Exception):
    pass


class _MeshRedirect(Exception):
    """Internal signal: the from-field references a mesh ID, not a graph ID."""
    def __init__(self, mesh_id: str):
        self.mesh_id = mesh_id


class HQLResult:
    def __init__(self, alias: str, items: List[Dict], meta: Dict):
        self.alias = alias
        self.items = items
        self.meta = meta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alias": self.alias,
            "count": len(self.items),
            "items": self.items,
            "meta": self.meta,
        }


def parse_hql(hql_text: str) -> Dict[str, Any]:
    """Parse HQL YAML text into a query dict."""
    try:
        if hql_text.strip().startswith("{"):
            data = json.loads(hql_text)
        else:
            data = yaml.safe_load(hql_text)
    except Exception as e:
        raise HQLError(f"Failed to parse HQL: {e}")

    if not isinstance(data, dict):
        raise HQLError("HQL must be a YAML/JSON object")

    if "hql" not in data:
        raise HQLError("HQL must have a top-level 'hql' key")

    return data["hql"]


def validate_hql(hql: Dict) -> List[str]:
    """Validate HQL structure. Returns list of validation errors."""
    errors = []

    if "from" not in hql:
        errors.append("'from' field is required (graph ID or list of graph IDs)")

    match = hql.get("match", {})
    if match and "type" not in match:
        errors.append("'match.type' must be 'hypernode' or 'hyperedge'")
    elif match and match.get("type") not in ("hypernode", "hyperedge", "any"):
        errors.append("'match.type' must be one of: hypernode, hyperedge, any")

    return errors


def _build_mongo_query(
    graph_ids: List[str],
    match: Dict,
    where: Dict,
    pit: Optional[datetime] = None,
) -> Dict:
    """Build MongoDB query from HQL match/where clauses."""
    query: Dict[str, Any] = {"hypergraph_id": {"$in": graph_ids}, "status": "active"}

    # match conditions
    if match.get("relation"):
        query["relation"] = match["relation"]
    if match.get("node_type"):
        query["type"] = match["node_type"]
    if match.get("flavor"):
        query["flavor"] = match["flavor"]
    if match.get("id"):
        query["id"] = match["id"]

    # member filter (for hyperedges)
    if match.get("nodes"):
        node_ids = match["nodes"] if isinstance(match["nodes"], list) else [match["nodes"]]
        query["members.node_id"] = {"$all": node_ids}

    # where conditions (dot-delimited attribute paths supported)
    for key, value in where.items():
        if key == "tags":
            tags = value if isinstance(value, list) else [value]
            query["tags"] = {"$all": tags}
        elif key == "status":
            query["status"] = value
        elif key == "members":
            # e.g. where.members.node_id: some-id
            if isinstance(value, dict):
                for mk, mv in value.items():
                    query[f"members.{mk}"] = mv
        else:
            # Support dot-delimited paths: attributes.city -> attributes.city
            query[key] = value

    # Point-in-time filter
    if pit:
        pit_filter = [
            {"$or": [{"valid_from": None}, {"valid_from": {"$lte": pit}}]},
            {"$or": [{"valid_to": None}, {"valid_to": {"$gte": pit}}]},
        ]
        existing_and = query.pop("$and", [])
        query["$and"] = existing_and + pit_filter

    return query


def _project_fields(doc: Dict, return_fields: List[str]) -> Dict:
    """Project only requested fields from a document."""
    if not return_fields or "*" in return_fields or "all" in return_fields:
        return doc

    result = {}
    for field in return_fields:
        if field == "id":
            result["id"] = doc.get("id")
        elif field == "label":
            result["label"] = doc.get("label")
        elif field == "members":
            result["members"] = doc.get("members", [])
        elif field == "attributes":
            result["attributes"] = doc.get("attributes", {})
        elif field == "tags":
            result["tags"] = doc.get("tags", [])
        elif field == "relation":
            result["relation"] = doc.get("relation")
        elif field == "type":
            result["type"] = doc.get("type")
        elif "." in field:
            # Dot-delimited path
            parts = field.split(".")
            val = doc
            for p in parts:
                if isinstance(val, dict):
                    val = val.get(p)
                else:
                    val = None
                    break
            result[field] = val
        else:
            result[field] = doc.get(field)
    return result


async def _resolve_graph_ids(from_field: Any) -> List[str]:
    """Resolve from field to list of physical graph IDs (handles logical graphs)."""
    if isinstance(from_field, str):
        graph_ids = [from_field]
    elif isinstance(from_field, list):
        graph_ids = from_field
    else:
        raise HQLError(f"Invalid 'from' value: {from_field}")

    # Expand logical graphs
    resolved = []
    for gid in graph_ids:
        doc = await col_hypergraphs().find_one({"id": gid})
        if not doc:
            # Check if it's a mesh ID — signal federation to the caller
            from hgai.db.mongodb import col_meshes
            if await col_meshes().find_one({"id": gid}):
                raise _MeshRedirect(gid)
            raise HQLError(f"Hypergraph not found: {gid}")
        if doc.get("type") == "logical" and doc.get("composition"):
            resolved.extend(doc["composition"])
        else:
            resolved.append(gid)

    return list(set(resolved))


def _hql_cache_key(hql: Dict) -> str:
    payload = json.dumps(hql, sort_keys=True, default=str)
    return hashlib.md5(payload.encode()).hexdigest()


async def execute_hql(hql_text: str, use_cache: bool = True) -> HQLResult:
    """Parse and execute an HQL query."""
    from hgai.core.cache import get_cached_result, set_cached_result

    hql = parse_hql(hql_text)
    errors = validate_hql(hql)
    if errors:
        raise HQLError(f"HQL validation errors: {'; '.join(errors)}")

    cache_key = _hql_cache_key(hql)
    if use_cache:
        cached = await get_cached_result(cache_key)
        if cached:
            result = HQLResult(
                alias=cached.get("alias", "result"),
                items=cached.get("items", []),
                meta={**cached.get("meta", {}), "cached": True},
            )
            return result

    from_field = hql["from"]
    raw_ids = [from_field] if isinstance(from_field, str) else list(from_field)
    dot_refs   = [r for r in raw_ids if r.count(".") == 2]
    plain_refs = [r for r in raw_ids if r.count(".") != 2]

    match = hql.get("match", {})
    where = hql.get("where", {})
    return_fields = hql.get("return", ["*"])
    alias = hql.get("as", "result")
    limit = hql.get("limit", 500)
    skip = hql.get("skip", 0)
    distinct = hql.get("distinct", False)

    # Parse point-in-time
    pit: Optional[datetime] = None
    if "at" in hql:
        from dateutil.parser import parse as parse_dt
        pit = parse_dt(hql["at"])

    # Aggregation
    aggregate = hql.get("aggregate", {})

    all_items: List[Dict] = []

    # ── Dot-notation mesh refs (mesh_id.server_id.graph_id) ──────────────────
    if dot_refs:
        try:
            from hgai_module_mesh.engine import execute_dot_refs
            dot_result = await execute_dot_refs(dot_refs, hql_text, "hql", use_cache=use_cache)
            all_items.extend(dot_result["items"])
        except ImportError:
            raise HQLError("Mesh dot-notation requires hgai_module_mesh to be installed")

    # ── Local graph IDs / bare mesh IDs ──────────────────────────────────────
    graph_ids: List[str] = []
    if plain_refs:
        try:
            graph_ids = await _resolve_graph_ids(
                plain_refs[0] if len(plain_refs) == 1 else plain_refs
            )
        except _MeshRedirect as redirect:
            try:
                from hgai_module_mesh.engine import federated_hql
                fed = await federated_hql(redirect.mesh_id, hql_text, use_cache=use_cache)
                all_items.extend(fed["items"])
            except ImportError:
                raise HQLError("Mesh federation requires hgai_module_mesh to be installed")

    match_type = match.get("type", "any")

    if graph_ids:
        if match_type in ("hypernode", "any"):
            query = _build_mongo_query(graph_ids, match, where, pit)
            # Remove hyperedge-only fields from query
            node_query = {k: v for k, v in query.items() if k not in ("relation", "flavor", "members.node_id")}
            cursor = col_hypernodes().find(node_query).skip(skip).limit(limit)
            async for doc in cursor:
                doc.pop("_id", None)
                for _f in _SKOS_FIELDS:
                    doc.pop(_f, None)
                doc["_entity_type"] = "hypernode"
                projected = _project_fields(doc, return_fields)
                all_items.append(projected)

        if match_type in ("hyperedge", "any"):
            query = _build_mongo_query(graph_ids, match, where, pit)
            # Remove hypernode-only fields
            edge_query = {k: v for k, v in query.items() if k not in ("type",)}
            cursor = col_hyperedges().find(edge_query).skip(skip).limit(limit)
            async for doc in cursor:
                doc.pop("_id", None)
                for _f in _SKOS_FIELDS:
                    doc.pop(_f, None)
                doc["_entity_type"] = "hyperedge"
                projected = _project_fields(doc, return_fields)
                all_items.append(projected)

    items = all_items

    # DISTINCT — deduplicate by id when available, otherwise by full row content
    if distinct:
        seen: set = set()
        deduped = []
        for item in items:
            key = item.get("id") or json.dumps(item, sort_keys=True, default=str)
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        items = deduped

    # Apply aggregations
    agg_results = {}
    if aggregate:
        if "count" in aggregate:
            agg_results["count"] = len(items)
        if "group_by" in aggregate:
            field = aggregate["group_by"]
            groups: Dict[str, int] = {}
            for item in items:
                key = str(item.get(field, "unknown"))
                groups[key] = groups.get(key, 0) + 1
            agg_results["groups"] = groups

    meta = {
        "graph_ids": graph_ids,
        "dot_refs": dot_refs if dot_refs else None,
        "match_type": match_type,
        "pit": pit.isoformat() if pit else None,
        "distinct": distinct,
        "cached": False,
        **agg_results,
    }

    result = HQLResult(alias=alias, items=items, meta=meta)

    if use_cache:
        await set_cached_result(cache_key, result.to_dict(), graph_ids=graph_ids)

    return result
