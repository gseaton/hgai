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

from hgai.db.storage import get_storage
from hgai_module_storage.filters import HyperedgeSearchFilters, HypernodeSearchFilters

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


def _build_node_search_filters(
    graph_ids: List[str],
    match: Dict,
    where: Dict,
    pit: Optional[datetime] = None,
) -> HypernodeSearchFilters:
    """Build HypernodeSearchFilters from HQL match/where clauses."""
    node_type = match.get("node_type")
    # Derive status from where if present
    status = where.get("status", "active")
    tags = None
    attributes: Dict[str, Any] = {}

    node_id = match.get("id")

    for key, value in where.items():
        if key == "tags":
            tags = value if isinstance(value, list) else [value]
        elif key == "status":
            pass  # already handled above
        else:
            # dot-delimited attribute paths go into attributes filter
            attributes[key] = value

    return HypernodeSearchFilters(
        hypergraph_ids=graph_ids,
        node_type=node_type,
        status=status,
        tags=tags,
        pit=pit,
        node_ids_in=[node_id] if node_id else None,
        attributes=attributes if attributes else None,
    )


def _build_edge_search_filters(
    graph_ids: List[str],
    match: Dict,
    where: Dict,
    pit: Optional[datetime] = None,
) -> HyperedgeSearchFilters:
    """Build HyperedgeSearchFilters from HQL match/where clauses."""
    relation = match.get("relation")
    flavor = match.get("flavor")
    status = where.get("status", "active")
    tags = None
    attributes: Dict[str, Any] = {}
    member_node_ids_all: Optional[List[str]] = None

    # member filter (for hyperedges)
    if match.get("nodes"):
        node_ids = match["nodes"] if isinstance(match["nodes"], list) else [match["nodes"]]
        member_node_ids_all = node_ids

    # extra filters from where (pass-through for members.* and other dot-paths)
    extra_filters: Dict[str, Any] = {}
    for key, value in where.items():
        if key == "tags":
            tags = value if isinstance(value, list) else [value]
        elif key == "status":
            pass
        elif key == "members":
            if isinstance(value, dict):
                for mk, mv in value.items():
                    extra_filters[f"members.{mk}"] = mv
        else:
            extra_filters[key] = value

    return HyperedgeSearchFilters(
        hypergraph_ids=graph_ids,
        relation=relation,
        flavor=flavor,
        status=status,
        tags=tags,
        member_node_ids_all=member_node_ids_all,
        pit=pit,
        attributes=attributes if attributes else None,
        extra_filters=extra_filters if extra_filters else None,
    )


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
    """Resolve from field to a list of hypergraph_id refs used in node/edge queries.

    Supports two ref formats:
      - ``graph_id``            — unowned graph (space_id is null)
      - ``space_id/graph_id``   — space-scoped graph (slash separator)

    Returns composite refs matching the hypergraph_id stored in node/edge documents:
      - Unowned graph:      ``"graph_id"``
      - Space-scoped graph: ``"space_id/graph_id"``
    """
    from hgai.core.engine import _hypergraph_ref

    if isinstance(from_field, str):
        graph_ids = [from_field]
    elif isinstance(from_field, list):
        graph_ids = from_field
    else:
        raise HQLError(f"Invalid 'from' value: {from_field}")

    # Expand logical graphs
    resolved = []
    for ref in graph_ids:
        if "/" in ref:
            space_part, gid = ref.split("/", 1)
            doc = await get_storage().hypergraphs.get(gid, space_id=space_part)
        else:
            gid = ref
            doc = await get_storage().hypergraphs.get(gid, space_id=None)
            if not doc:
                # Check if it's a mesh ID — signal federation to the caller
                mesh_doc = await get_storage().meshes.get(gid)
                if mesh_doc:
                    raise _MeshRedirect(gid)
        if not doc:
            raise HQLError(f"Hypergraph not found: {ref!r}")
        if doc.type == "logical" and doc.composition:
            # Logical graph composition: resolve each member graph
            for member_id in doc.composition:
                member_doc = await get_storage().hypergraphs.find_composition_member(member_id)
                if member_doc:
                    resolved.append(
                        _hypergraph_ref(member_doc.id, member_doc.space_id)
                    )
        else:
            resolved.append(_hypergraph_ref(doc.id, doc.space_id))

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
    # 2-dot = mesh.server.graph (unowned), 3-dot = mesh.server.space.graph (space-scoped)
    dot_refs   = [r for r in raw_ids if r.count(".") in (2, 3)]
    plain_refs = [r for r in raw_ids if r.count(".") not in (2, 3)]

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
            node_filters = _build_node_search_filters(graph_ids, match, where, pit)
            docs = await get_storage().hypernodes.search(node_filters, skip=skip, limit=limit)
            for doc in docs:
                for _f in _SKOS_FIELDS:
                    doc.pop(_f, None)
                doc["_entity_type"] = "hypernode"
                projected = _project_fields(doc, return_fields)
                all_items.append(projected)

        if match_type in ("hyperedge", "any"):
            edge_filters = _build_edge_search_filters(graph_ids, match, where, pit)
            docs = await get_storage().hyperedges.search(edge_filters, skip=skip, limit=limit)
            for doc in docs:
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
