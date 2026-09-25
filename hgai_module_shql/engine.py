"""SHQL execution engine.

SHQL (Semantic Hypergraph Query Language) is a SPARQL-inspired, YAML-based
pattern-matching query language for HypergraphAI.

Execution model
---------------
A BindingSet is a dict mapping variable names (?var) to resolved documents or
scalar values.  Patterns are evaluated sequentially; each pattern filters or
expands the current set of bindings.  Variables shared across patterns act as
implicit join keys — the same ?var bound in a node pattern and later referenced
in an edge member pattern constrains the edge query to only edges that contain
the already-bound node.

Pattern types
-------------
  node   — match hypernodes
  edge   — match hyperedges; members sub-patterns bind member node IDs
  filter — expression-based post-match filtering
  optional — left-outer-join wrapper around a sub-pattern list
  union  — set union of two or more alternative pattern branches
"""

import hashlib
import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

from hgai.config import get_settings
from hgai.core.auth import PermissionDeniedError, check_graph_permission
from hgai.db.storage import get_storage
from hgai.models.account import AccountInDB
from hgai_module_storage.filters import HyperedgeSearchFilters, HypernodeSearchFilters

from .aggregate_merge import MEASURE_FNS, measure_requests, merge_aggregate_meta, partial_aggregate

_SKOS_FIELDS = ("skos_broader", "skos_narrower", "skos_related")

BindingSet = Dict[str, Any]


async def _search_capped(store, filters, cap: int, what: str) -> List[Dict[str, Any]]:
    """Run `store.search` with a candidate cap, recording truncation.

    Fetches cap+1 so an overflow is detectable without a count query; the
    extra document is discarded.
    """
    from hgai.core.inference import note_truncation
    docs = await store.search(filters, skip=0, limit=cap + 1)
    if len(docs) > cap:
        note_truncation(f"{what} (cap {cap})")
        return docs[:cap]
    return docs


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_var(s: Any) -> bool:
    return isinstance(s, str) and s.startswith("?")


def _get_nested(doc: Any, path: str) -> Any:
    """Navigate a dot-delimited path through nested dicts."""
    val = doc
    for part in path.split("."):
        if isinstance(val, dict):
            val = val.get(part)
        else:
            return None
    return val


def _parse_order_by(order_by: Any) -> List[tuple]:
    """Normalize `order_by` into an ordered list of (field, descending) pairs.

    Accepts a single field or a list of fields (primary key first). Each
    field is a `?var.field`-style string (leading `?` optional) with an
    optional trailing " asc"/" desc" (case-insensitive) — a bare field with
    no suffix sorts ascending, matching SQL's own default.
    """
    specs = order_by if isinstance(order_by, list) else [order_by]
    parsed: List[tuple] = []
    for spec in specs:
        text = str(spec).strip()
        descending = False
        head, _, tail = text.rpartition(" ")
        if head and tail.lower() in ("asc", "desc"):
            text, descending = head.strip(), tail.lower() == "desc"
        parsed.append((text.lstrip("?"), descending))
    return parsed


def _order_by_value(row: Dict, field: str) -> Any:
    """Resolve one `order_by` field against a projected result row; None when
    missing or null (which sorts first — see `_apply_order_by`)."""
    if field in row:
        return row[field]
    parts = field.split(".", 1)
    if parts[0] in row:
        v = row[parts[0]]
        if len(parts) > 1 and isinstance(v, dict):
            v = _get_nested(v, parts[1])
        return v
    return None


def _apply_order_by(items: List[Dict], order_by: Any) -> List[Dict]:
    """Sort projected result rows per `order_by` (see `_parse_order_by`).

    Multi-key sort with independent per-key direction is done as a series
    of stable single-key sorts, lowest priority first — Python's sort
    stability means each subsequent (higher-priority) pass only reorders
    rows that tied on every pass before it, which is the standard technique
    for composing a multi-key sort out of single-key ones.
    """
    # Values are compared with the storage layer's `sort_key` (missing/null first,
    # numbers < strings < ...), the same total order storage-side ordering uses,
    # so the two paths agree — and mixed-type columns no longer raise TypeError.
    from hgai_module_storage.aggregate import sort_key

    for field, descending in reversed(_parse_order_by(order_by)):
        items = sorted(items, key=lambda row, f=field: sort_key(_order_by_value(row, f)), reverse=descending)
    return items


def _resolve_var(val: Any, binding: BindingSet) -> Any:
    """Resolve ?var to its bound node id (or scalar). Returns literal unchanged."""
    if not _is_var(val):
        return val
    bound = binding.get(val)
    if isinstance(bound, dict):
        return bound.get("id")
    return bound


def _resolve_binding_path(expr: str, binding: BindingSet) -> Any:
    """Resolve ?var or ?var.field.path against a binding set for FILTER expressions."""
    parts = expr.split(".", 1)
    var = parts[0]
    if not _is_var(var):
        return expr  # literal
    doc = binding.get(var)
    if doc is None:
        return None
    if len(parts) == 1:
        return doc
    return _get_nested(doc, parts[1]) if isinstance(doc, dict) else None


# ── Member pattern matching ───────────────────────────────────────────────────

def _member_pat_to_node_pat(pat: Any) -> Dict[str, Any]:
    """Normalise a raw member pattern to a flat node-pattern dict."""
    if isinstance(pat, str) and _is_var(pat):
        return {"bind": pat}
    if isinstance(pat, dict) and "node" in pat:
        return pat["node"] if isinstance(pat["node"], dict) else {}
    if isinstance(pat, dict):
        return pat
    return {}


def _resolve_member_pat(node_pat: Dict[str, Any], binding: BindingSet) -> Dict[str, Any]:
    """Resolve a normalised member pattern's bind var, required node_id, and
    required seq against the current binding set.

    An already-bound ``bind`` variable takes priority over a literal/variable
    ``id`` (it reflects a join constraint from an earlier pattern). ``seq`` is
    resolved the same way ``id`` is when given as a variable reference.
    """
    bind_var = node_pat.get("bind")
    req_id   = node_pat.get("id")
    req_seq  = node_pat.get("seq")

    if bind_var and bind_var in binding:
        existing = binding[bind_var]
        req_id = existing.get("id") if isinstance(existing, dict) else existing
    elif req_id is not None and _is_var(str(req_id)):
        req_id = _resolve_var(req_id, binding)

    if req_seq is not None and _is_var(str(req_seq)):
        req_seq = _resolve_var(req_seq, binding)

    return {"bind": bind_var, "id": req_id, "seq": req_seq}


def _member_satisfies(member: Any, req_id: Any, req_seq: Any) -> bool:
    """Check a single edge member dict against required node_id / seq constraints."""
    mid = member.get("node_id") if isinstance(member, dict) else member
    if req_id is not None and mid != req_id:
        return False
    if req_seq is not None:
        mseq = member.get("seq") if isinstance(member, dict) else None
        if mseq != req_seq:
            return False
    return True


def _match_members(
    edge_members: List[Dict],
    member_patterns: List[Any],
    binding: BindingSet,
) -> Optional[BindingSet]:
    """Try to match a list of member patterns against an edge's members.

    Each pattern may be:
      - "?var"                                  shorthand variable
      - {"bind": "?var"}                        bind any unmatched member
      - {"bind": "?var", "id": "literal-id"}    bind a member with a specific id
      - {"bind": "?var", "seq": 0}               bind the member at a specific sequence position
      - {"node": {"bind": "?var", "id": ...}}   nested node form

    ``id`` and ``seq``, when both given on the same pattern, must be satisfied
    by the same edge member (e.g. "the seq-0 member has id X").

    Returns an updated BindingSet if all patterns are satisfied, or None.
    """
    new_binding = dict(binding)
    used: Set[int] = set()

    for pat in member_patterns:
        node_pat: Dict[str, Any] = _member_pat_to_node_pat(pat)
        if not node_pat and not isinstance(pat, (str, dict)):
            return None

        resolved = _resolve_member_pat(node_pat, new_binding)
        bind_var, req_id, req_seq = resolved["bind"], resolved["id"], resolved["seq"]

        # Find the first unused edge member that satisfies the requirement
        matched_idx = None
        for i, member in enumerate(edge_members):
            if i in used:
                continue
            if not _member_satisfies(member, req_id, req_seq):
                continue
            matched_idx = i
            break

        if matched_idx is None:
            return None  # Pattern not satisfied

        used.add(matched_idx)
        matched_member = edge_members[matched_idx]
        matched_node_id = (
            matched_member.get("node_id")
            if isinstance(matched_member, dict)
            else matched_member
        )

        # Bind the variable to the node_id string for now; full doc resolved later
        if bind_var and bind_var not in new_binding:
            new_binding[bind_var] = matched_node_id

    return new_binding


def _match_members_expand(
    edge_members: List[Dict],
    member_patterns: List[Any],
    binding: BindingSet,
) -> List[BindingSet]:
    """Like _match_members but expands wildcard (fully unconstrained) member
    patterns over ALL matching edge members, producing one BindingSet per member.

    Anchor patterns — those that resolve to a required ``id`` and/or ``seq``,
    including via an already-bound ``bind`` variable — are matched first to
    determine which member slots are spoken for. Each remaining member is then
    yielded as a separate binding for the single wildcard pattern.

    Falls back to the single-result ``_match_members`` behaviour when there are
    multiple wildcard patterns (not yet expanded) or no member patterns at all.
    """
    if not member_patterns:
        return [dict(binding)]

    # Classify patterns: anchor (resolves to a required id and/or seq) vs
    # wildcard (no constraint at all — enumerate every remaining member).
    anchor_pats: List[tuple] = []   # (raw_pat, req_id, req_seq)
    wildcard_pats: List[Any] = []

    for pat in member_patterns:
        np = _member_pat_to_node_pat(pat)
        resolved = _resolve_member_pat(np, binding)
        req_id, req_seq = resolved["id"], resolved["seq"]
        if req_id is not None or req_seq is not None:
            anchor_pats.append((pat, req_id, req_seq))
        else:
            wildcard_pats.append(pat)

    # No wildcards — use original single-result matcher unchanged
    if not wildcard_pats:
        result = _match_members(edge_members, member_patterns, binding)
        return [result] if result is not None else []

    # Match anchor patterns first to pin down used member slots
    used_indices: Set[int] = set()
    anchor_binding = dict(binding)

    for pat, req_id, req_seq in anchor_pats:
        np = _member_pat_to_node_pat(pat)
        bind_var = np.get("bind")
        matched_idx = None
        for i, member in enumerate(edge_members):
            if i in used_indices:
                continue
            if not _member_satisfies(member, req_id, req_seq):
                continue
            matched_idx = i
            break
        if matched_idx is None:
            return []  # anchor not satisfied → edge doesn't match at all
        used_indices.add(matched_idx)
        matched_id = (
            edge_members[matched_idx].get("node_id")
            if isinstance(edge_members[matched_idx], dict)
            else edge_members[matched_idx]
        )
        if bind_var and bind_var not in anchor_binding:
            anchor_binding[bind_var] = matched_id

    # Collect remaining members available for wildcard patterns
    remaining = [
        (i, m) for i, m in enumerate(edge_members) if i not in used_indices
    ]

    # Single wildcard: yield one binding per remaining member
    if len(wildcard_pats) == 1:
        np = _member_pat_to_node_pat(wildcard_pats[0])
        bind_var = np.get("bind")
        results: List[BindingSet] = []
        for _, member in remaining:
            mid = member.get("node_id") if isinstance(member, dict) else member
            b = dict(anchor_binding)
            if bind_var:
                b[bind_var] = mid
            results.append(b)
        return results

    # Multiple wildcards: fall back to original sequential first-match behaviour
    result = _match_members(edge_members, member_patterns, binding)
    return [result] if result is not None else []


# ── Pattern evaluators ────────────────────────────────────────────────────────

def _node_filters(
    pattern: Dict,
    graph_ids: List[str],
    pit: Optional[datetime],
    node_ids_in: Optional[List[str]] = None,
) -> HypernodeSearchFilters:
    """Storage filters for a node pattern — shared by matching and aggregate pushdown."""
    tags = pattern.get("tags")
    attributes = pattern.get("attributes") or {}
    return HypernodeSearchFilters(
        hypergraph_ids=graph_ids,
        node_type=pattern.get("type"),
        status=pattern.get("status", "active"),
        tags=tags if not tags or isinstance(tags, list) else [tags],
        pit=pit,
        node_ids_in=node_ids_in,
        attributes=attributes if attributes else None,
    )


def _edge_filters(
    pattern: Dict,
    graph_ids: List[str],
    pit: Optional[datetime],
    *,
    relation: Optional[str],
    member_node_ids_all: Optional[List[str]] = None,
    member_node_ids_any: Optional[List[str]] = None,
    edge_id: Optional[str] = None,
) -> HyperedgeSearchFilters:
    """Storage filters for an edge pattern — shared by matching and aggregate pushdown.

    `relation` and `member_node_ids_all` are passed in because matching
    deliberately widens them under `infer: true`.
    """
    tags = pattern.get("tags")
    attributes = pattern.get("attributes") or {}
    return HyperedgeSearchFilters(
        hypergraph_ids=graph_ids,
        relation=relation,
        flavor=pattern.get("flavor"),
        status=pattern.get("status", "active"),
        tags=tags if not tags or isinstance(tags, list) else [tags],
        pit=pit,
        member_node_ids_all=member_node_ids_all,
        member_node_ids_any=member_node_ids_any,
        attributes=attributes if attributes else None,
        extra_filters={"id": edge_id} if edge_id is not None else None,
    )


_RESOLVE_CHUNK = 5000   # node ids per `find_by_ids` when resolving bound variables


def _chunks(items: List[Any], size: int):
    for i in range(0, len(items), size):
        yield items[i: i + size]


# Joins: a pattern is evaluated against every binding produced so far. Rather
# than one storage query per binding, bindings are first reduced to the
# distinct *search keys* they imply (a resolved node id; a relation / edge id /
# set of already-bound member ids), each distinct key is fetched once — many
# keys per query where the store can filter by "any of these ids" — and the
# documents are then handed back to the bindings in their original order.
# `HGAI_SHQL_JOIN_BATCH_SIZE` bounds keys per query; a batch that might have
# lost documents to the candidate cap is retried key by key, so results and
# truncation reporting are identical to the one-query-per-binding behaviour.

async def _fetch_node_docs(
    pattern: Dict,
    graph_ids: List[str],
    pit: Optional[datetime],
    keys: List[Tuple],
) -> Dict[Tuple, List[Dict]]:
    """Documents for each node search key: ("any",) or ("id", <resolved id>)."""
    store = get_storage().hypernodes
    cap = get_settings().shql_max_node_candidates
    out: Dict[Tuple, List[Dict]] = {}

    async def single(key: Tuple) -> List[Dict]:
        ids = [key[1]] if key[0] == "id" else None
        docs = await _search_capped(
            store, _node_filters(pattern, graph_ids, pit, ids), cap, "node pattern candidates",
        )
        return docs

    id_keys: List[Tuple] = []
    for key in keys:
        if key[0] == "id":
            id_keys.append(key)
        else:
            out[key] = await single(key)

    batch = get_settings().shql_join_batch_size
    for chunk in _chunks(id_keys, batch):
        if len(chunk) == 1:
            out[chunk[0]] = await single(chunk[0])
            continue
        ids = [k[1] for k in chunk]
        # (id, hypergraph_id) is unique, so a lookup by ids can return at most
        # len(ids) * len(graph_ids) documents — this limit can never truncate.
        docs = await store.search(
            _node_filters(pattern, graph_ids, pit, ids), skip=0, limit=len(ids) * len(graph_ids),
        )
        by_id: Dict[Any, List[Dict]] = {}
        for doc in docs:
            by_id.setdefault(doc.get("id"), []).append(doc)
        for key in chunk:
            out[key] = by_id.get(key[1], [])

    for docs in out.values():
        for doc in docs:
            for _f in _SKOS_FIELDS:
                doc.pop(_f, None)
    return out


async def _eval_node_pattern(
    pattern: Dict,
    graph_ids: List[str],
    pit: Optional[datetime],
    bindings: List[BindingSet],
) -> List[BindingSet]:
    bind_var  = pattern.get("bind")
    node_id   = pattern.get("id")
    node_type = pattern.get("type")

    # Phase 1: classify each binding (pass through / drop / needs a search key).
    entries: List[Tuple[BindingSet, Optional[Tuple]]] = []
    keys: List[Tuple] = []
    seen_keys: Set[Tuple] = set()
    for binding in bindings:
        # If bind_var is already bound, just verify the conditions hold
        if bind_var and bind_var in binding:
            existing = binding[bind_var]
            if isinstance(existing, dict):
                if node_type and existing.get("type") != node_type:
                    continue
                if node_id:
                    req = _resolve_var(node_id, binding) if _is_var(str(node_id)) else node_id
                    if req and existing.get("id") != req:
                        continue
            entries.append((binding, None))
            continue

        key: Tuple = ("any",)
        if node_id is not None:
            resolved_id = _resolve_var(node_id, binding) if _is_var(str(node_id)) else node_id
            if resolved_id is None:
                continue
            key = ("id", resolved_id)
        entries.append((binding, key))
        if key not in seen_keys:
            seen_keys.add(key)
            keys.append(key)

    # Phase 2: one fetch per distinct key (batched); phase 3: expand in binding order.
    docs_by_key = await _fetch_node_docs(pattern, graph_ids, pit, keys) if keys else {}

    result: List[BindingSet] = []
    for binding, key in entries:
        if key is None:
            result.append(binding)
            continue
        for doc in docs_by_key[key]:
            new_binding = dict(binding)
            if bind_var:
                new_binding[bind_var] = doc
            result.append(new_binding)

    return result


def _bound_member_ids(member_patterns: List[Any], binding: BindingSet) -> List[Any]:
    """Member node ids already fixed for this binding, to narrow the edge query."""
    bound_node_ids: List[Any] = []
    for pat in member_patterns:
        np = (
            pat if isinstance(pat, str)
            else (pat.get("node", pat) if isinstance(pat, dict) else {})
        )
        bv  = np.get("bind") if isinstance(np, dict) else (pat if _is_var(pat) else None)
        rid = np.get("id") if isinstance(np, dict) else None

        if bv and bv in binding:
            existing = binding[bv]
            nid = existing.get("id") if isinstance(existing, dict) else existing
            if nid:
                bound_node_ids.append(nid)
        elif rid and not _is_var(str(rid)):
            bound_node_ids.append(rid)
        elif rid and _is_var(str(rid)):
            resolved = _resolve_var(rid, binding)
            if resolved:
                bound_node_ids.append(resolved)
    return bound_node_ids


async def _fetch_edge_docs(
    pattern: Dict,
    graph_ids: List[str],
    pit: Optional[datetime],
    infer: bool,
    keys: List[Tuple],
    ids_of: Dict[Tuple, List[Any]],
) -> Dict[Tuple, List[Dict]]:
    """Documents for each edge search key `(relation, member-id set, edge id)`.

    `ids_of[key]` holds the (unsorted) already-bound member ids behind a key.
    """
    store = get_storage().hyperedges
    cap = get_settings().shql_max_edge_candidates
    out: Dict[Tuple, List[Dict]] = {}

    async def finish(docs: List[Dict], resolved_rel: Any) -> List[Dict]:
        # infer: true extends the literal candidate set with synthesized
        # edges before member-pattern matching runs, so an inferred edge is
        # first-class in exactly the same way a literal one is — it can
        # bind ?vars, anchor a later hop, chain into a further pattern.
        # Computed live per pattern evaluation, never persisted. Opt-in
        # only: no `infer` flag means this whole block never runs.
        #
        # expand_edge_closure covers owl:inverse-of/owl:symmetric/
        # skos:broaderTransitive/narrowerTransitive AND owl:transitive
        # (see hgai/core/inference.py) — so a fully-resolved 2-endpoint
        # pattern like `members: [{id: A}, {id: B}]` gets its transitive
        # chain, if any, from the same general mechanism as any other
        # inferred edge; no separate check_transitive call needed here.
        if infer:
            from hgai.core.inference import expand_edge_closure
            docs = docs + await expand_edge_closure(docs, graph_ids, pit=pit)

            # Now that expansion has run over the full (relation-agnostic)
            # candidate set, narrow back down to what the caller actually
            # asked for — otherwise a query for one relation would silently
            # include literal/inferred edges of every other relation that
            # merely happened to expand from the same source docs.
            if resolved_rel:
                docs = [d for d in docs if d.get("relation") == resolved_rel]
        for doc in docs:
            for _f in _SKOS_FIELDS:
                doc.pop(_f, None)
        return docs

    async def single(key: Tuple) -> List[Dict]:
        resolved_rel, _members, resolved_id = key
        bound = ids_of[key]
        filters = _edge_filters(
            pattern, graph_ids, pit,
            # When inferring, a `relation:` filter names the relation the
            # CALLER wants — which may only ever exist as something
            # synthesized (e.g. `rel:member-of`, derived from `rel:member`
            # via an `owl:inverse-of` axiom). Filtering the literal search
            # by it would starve expand_edge_closure of anything to derive
            # from, since it only ever expands edges it's handed. So the
            # literal fetch stays relation-agnostic here, and `resolved_rel`
            # is applied as a post-filter in `finish`, after expansion —
            # matching the design intent that `rel:member` and
            # `rel:member-of` are interchangeable query surfaces regardless
            # of which one is asserted vs. inferred.
            relation=None if infer else resolved_rel,
            # Same reasoning as `relation` above: a transitive fact spans
            # MULTIPLE literal edges, none of which individually contains
            # both endpoints — pre-filtering the literal fetch down to
            # "edges containing all of these already-bound members" would
            # starve owl:transitive expansion of the very chain it needs to
            # walk, for a fully-resolved 2-endpoint pattern like
            # `members: [{id: A}, {id: B}]` under `infer: true`. Dropping it
            # here only widens the literal candidate set fed into
            # expansion; final results are still narrowed correctly by the
            # member-pattern matching loop, same as dropping `relation`
            # doesn't loosen the final `docs` filter.
            member_node_ids_all=None if infer else (bound if bound else None),
            edge_id=resolved_id,
        )
        docs = await _search_capped(store, filters, cap, "edge pattern candidates")
        return await finish(docs, resolved_rel)

    # Keys that differ only in their member-id sets can share one query.
    groups: Dict[Tuple, List[Tuple]] = {}
    for key in keys:
        groups.setdefault((key[0], key[2]), []).append(key)

    batch = get_settings().shql_join_batch_size
    for (resolved_rel, resolved_id), group in groups.items():
        constrained = [k for k in group if k[1]]
        for key in group:
            if not key[1]:
                out[key] = await single(key)
        for chunk in _chunks(constrained, batch):
            if len(chunk) == 1:
                out[chunk[0]] = await single(chunk[0])
                continue
            # Fetch every edge touching any bound id, at most enough to serve
            # `cap` edges per key. Hitting that limit means some key's edges
            # may be missing, so fall back to exact per-key queries.
            limit = cap * len(chunk) + 1
            any_ids = sorted({i for k in chunk for i in ids_of[k]}, key=str)
            docs = await store.search(
                _edge_filters(pattern, graph_ids, pit, relation=resolved_rel,
                              member_node_ids_any=any_ids, edge_id=resolved_id),
                skip=0, limit=limit,
            )
            if len(docs) >= limit:
                for key in chunk:
                    out[key] = await single(key)
                continue
            member_sets = [
                {m.get("node_id") if isinstance(m, dict) else m for m in d.get("members", [])}
                for d in docs
            ]
            for key in chunk:
                need = set(ids_of[key])
                matched = [d for d, ms in zip(docs, member_sets) if need <= ms]
                if len(matched) > cap:
                    from hgai.core.inference import note_truncation
                    note_truncation(f"edge pattern candidates (cap {cap})")
                    matched = matched[:cap]
                out[key] = await finish(matched, resolved_rel)
    return out


async def _eval_edge_pattern(
    pattern: Dict,
    graph_ids: List[str],
    pit: Optional[datetime],
    bindings: List[BindingSet],
    infer: bool = False,
) -> List[BindingSet]:
    bind_var       = pattern.get("bind")
    edge_id        = pattern.get("id")
    relation       = pattern.get("relation")
    flavor         = pattern.get("flavor")
    member_patterns = pattern.get("members") or []

    # Phase 1: classify each binding (pass through / drop / needs a search key).
    entries: List[Tuple[BindingSet, Optional[Tuple]]] = []
    keys: List[Tuple] = []
    ids_of: Dict[Tuple, List[Any]] = {}
    for binding in bindings:
        # Already bound: verify relation/flavor/id match
        if bind_var and bind_var in binding:
            existing = binding[bind_var]
            if isinstance(existing, dict):
                if relation and existing.get("relation") != relation:
                    continue
                if flavor and existing.get("flavor") != flavor:
                    continue
                if edge_id:
                    req = _resolve_var(edge_id, binding) if _is_var(str(edge_id)) else edge_id
                    if req and existing.get("id") != req:
                        continue
            entries.append((binding, None))
            continue

        # Resolve relation variable if needed
        resolved_rel = None
        if relation:
            resolved_rel = _resolve_var(relation, binding) if _is_var(str(relation)) else relation

        # Resolve edge id variable if needed
        resolved_id = None
        if edge_id is not None:
            resolved_id = _resolve_var(edge_id, binding) if _is_var(str(edge_id)) else edge_id
            if resolved_id is None:
                continue

        # Add member constraints from already-bound variables to narrow the query
        # (ignored when inferring — see `_fetch_edge_docs`).
        bound = [] if infer else _bound_member_ids(member_patterns, binding)
        key = (resolved_rel, tuple(sorted({str(i) for i in bound})), resolved_id)
        entries.append((binding, key))
        if key not in ids_of:
            ids_of[key] = bound
            keys.append(key)

    # Phase 2: one fetch per distinct key (batched); phase 3: expand in binding order.
    docs_by_key = await _fetch_edge_docs(pattern, graph_ids, pit, infer, keys, ids_of) if keys else {}

    result: List[BindingSet] = []
    for binding, key in entries:
        if key is None:
            result.append(binding)
            continue
        for doc in docs_by_key[key]:
            edge_members = doc.get("members", [])

            expanded = (
                _match_members_expand(edge_members, member_patterns, binding)
                if member_patterns
                else [dict(binding)]
            )

            for new_binding in expanded:
                if bind_var:
                    new_binding[bind_var] = doc
                result.append(new_binding)

    return result


# ── Filter expression evaluator ───────────────────────────────────────────────

def _eval_filter(expression: str, bindings: List[BindingSet]) -> List[BindingSet]:
    return [b for b in bindings if _eval_expr(expression.strip(), b)]


def _find_keyword(expr: str, keyword: str) -> int:
    """Find a keyword in expr that is not inside parentheses or quotes."""
    depth = 0
    in_quote: Optional[str] = None
    i = 0
    kw = keyword.upper()
    while i < len(expr):
        c = expr[i]
        if c in ('"', "'") and in_quote is None:
            in_quote = c
        elif c == in_quote:
            in_quote = None
        elif in_quote is None:
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif depth == 0 and expr[i:i + len(kw)].upper() == kw:
                # Make sure it's a word boundary (not inside an identifier)
                before = expr[i - 1] if i > 0 else " "
                after  = expr[i + len(kw)] if i + len(kw) < len(expr) else " "
                if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                    return i
        i += 1
    return -1


def _coerce(s: str, ref: Any) -> Any:
    s = s.strip().strip("\"'")
    if isinstance(ref, bool):
        return s.lower() in ("true", "1", "yes")
    if isinstance(ref, int):
        try:
            return int(s)
        except ValueError:
            pass
    if isinstance(ref, float):
        try:
            return float(s)
        except ValueError:
            pass
    return s


def _eval_expr(expr: str, binding: BindingSet) -> bool:
    expr = expr.strip()
    if not expr:
        return True

    # OR (lowest precedence)
    idx = _find_keyword(expr, " OR ")
    if idx >= 0:
        return (
            _eval_expr(expr[:idx], binding)
            or _eval_expr(expr[idx + 4:], binding)
        )

    # AND
    idx = _find_keyword(expr, " AND ")
    if idx >= 0:
        return (
            _eval_expr(expr[:idx], binding)
            and _eval_expr(expr[idx + 5:], binding)
        )

    # NOT
    if expr.upper().startswith("NOT "):
        return not _eval_expr(expr[4:].strip(), binding)

    # Strip outer parentheses
    if expr.startswith("(") and expr.endswith(")"):
        return _eval_expr(expr[1:-1], binding)

    # Function calls
    upper = expr.upper()
    if upper.startswith("CONTAINS("):
        inner = expr[9:-1]
        parts = [p.strip() for p in inner.split(",", 1)]
        if len(parts) == 2:
            val    = _resolve_binding_path(parts[0], binding)
            needle = parts[1].strip("\"'")
            return isinstance(val, str) and needle.lower() in val.lower()
        return False
    if upper.startswith("STARTS_WITH("):
        inner = expr[12:-1]
        parts = [p.strip() for p in inner.split(",", 1)]
        if len(parts) == 2:
            val    = _resolve_binding_path(parts[0], binding)
            prefix = parts[1].strip("\"'")
            return isinstance(val, str) and val.lower().startswith(prefix.lower())
        return False
    if upper.startswith("ENDS_WITH("):
        inner = expr[10:-1]
        parts = [p.strip() for p in inner.split(",", 1)]
        if len(parts) == 2:
            val    = _resolve_binding_path(parts[0], binding)
            suffix = parts[1].strip("\"'")
            return isinstance(val, str) and val.lower().endswith(suffix.lower())
        return False
    if upper.startswith("MATCHES("):
        inner = expr[8:-1]
        parts = [p.strip() for p in inner.split(",", 1)]
        if len(parts) == 2:
            import re as _re
            val     = _resolve_binding_path(parts[0], binding)
            pattern = parts[1].strip("\"'")
            try:
                return isinstance(val, str) and bool(_re.search(pattern, val))
            except _re.error:
                return False
        return False
    if upper.startswith("BOUND("):
        var = expr[6:-1].strip()
        return var in binding and binding[var] is not None
    if upper.startswith("IS_TYPE("):
        inner = expr[8:-1]
        parts = [p.strip() for p in inner.split(",", 1)]
        if len(parts) == 2:
            doc  = binding.get(parts[0])
            typ  = parts[1].strip("\"'")
            return isinstance(doc, dict) and doc.get("type") == typ
        return False

    # Comparison operators (longest first to avoid prefix clashes)
    for op in ("<=", ">=", "!=", "<>", " IN ", "<", ">", "="):
        idx = _find_keyword(expr, op) if " " in op else _find_keyword(expr, op)
        if idx < 0:
            # plain string search as fallback for single-char ops
            # use _find_keyword only for word-boundary ops; do manual scan for symbols
            if op in ("<=", ">=", "!=", "<>", "<", ">", "="):
                idx = _find_symbol(expr, op)
        if idx >= 0:
            left_expr  = expr[:idx].strip()
            right_expr = expr[idx + len(op):].strip()
            left_val   = _resolve_binding_path(left_expr, binding)

            if op.strip() == "IN":
                try:
                    right_list = yaml.safe_load(right_expr)
                    if isinstance(right_list, list):
                        return left_val in right_list
                except Exception:
                    pass
                return False

            right_val = _coerce(right_expr, left_val)
            try:
                if op == "=":   return left_val == right_val
                if op in ("!=", "<>"): return left_val != right_val
                if op == "<":   return left_val < right_val  # type: ignore[operator]
                if op == ">":   return left_val > right_val  # type: ignore[operator]
                if op == "<=":  return left_val <= right_val  # type: ignore[operator]
                if op == ">=":  return left_val >= right_val  # type: ignore[operator]
            except TypeError:
                return False

    return False


def _find_symbol(expr: str, sym: str) -> int:
    """Find a symbol operator not inside quotes or parentheses."""
    depth = 0
    in_quote: Optional[str] = None
    for i in range(len(expr) - len(sym) + 1):
        c = expr[i]
        if c in ('"', "'") and in_quote is None:
            in_quote = c
        elif c == in_quote:
            in_quote = None
        elif in_quote is None:
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif depth == 0 and expr[i:i + len(sym)] == sym:
                return i
    return -1


# ── Post-processing ───────────────────────────────────────────────────────────

async def _resolve_node_bindings(
    bindings: List[BindingSet],
    graph_ids: List[str],
) -> List[BindingSet]:
    """Resolve any variable bound to a bare node_id string to a full node document.

    Edge member matching binds variables to node_id strings for efficiency.
    This step promotes them to full documents so that ?var.label etc. work in
    SELECT projections and ORDER BY.
    """
    # Collect all unresolved (string) variable bindings
    ids_needed: Set[str] = set()
    for binding in bindings:
        for k, v in binding.items():
            if _is_var(k) and isinstance(v, str):
                ids_needed.add(v)

    if not ids_needed:
        return bindings

    # Chunked so a huge join never builds one oversized `$in` list.
    node_map: Dict[str, Dict] = {}
    for chunk in _chunks(sorted(ids_needed), _RESOLVE_CHUNK):
        for doc in await get_storage().hypernodes.find_by_ids(chunk, graph_ids):
            for _f in _SKOS_FIELDS:
                doc.pop(_f, None)
            node_map[doc["id"]] = doc

    result = []
    for binding in bindings:
        new_b = {}
        for k, v in binding.items():
            if _is_var(k) and isinstance(v, str) and v in node_map:
                new_b[k] = node_map[v]
            else:
                new_b[k] = v
        result.append(new_b)
    return result


def _project_select(bindings: List[BindingSet], select_fields: List[str]) -> List[Dict]:
    """Project select fields from binding sets into result rows."""
    results = []
    for binding in bindings:
        if not select_fields or select_fields == ["*"]:
            row = {k.lstrip("?"): v for k, v in binding.items() if _is_var(k)}
            results.append(row)
            continue

        row: Dict[str, Any] = {}
        for field in select_fields:
            if field == "*":
                row.update({k.lstrip("?"): v for k, v in binding.items() if _is_var(k)})
                continue

            top = field.split(".")[0]
            if not _is_var(top):
                row[field] = None
                continue

            doc = binding.get(top)
            rest = field[len(top) + 1:] if "." in field else None

            if rest is None:
                row[top.lstrip("?")] = doc
            else:
                key = f"{top.lstrip('?')}.{rest}"
                row[key] = _get_nested(doc, rest) if isinstance(doc, dict) else None

        results.append(row)
    return results


# ── Pattern normalizers ───────────────────────────────────────────────────────

def _normalize_member_pat(pat: Any) -> Any:
    """Normalize member pattern to engine-internal form.

    Converts ``{"node_id": "?var"}`` → ``{"bind": "?var"}``
    and      ``{"node_id": "literal-id"}`` → ``{"id": "literal-id"}``.
    """
    if isinstance(pat, str):
        return pat
    if isinstance(pat, dict) and "node_id" in pat and "bind" not in pat:
        nid = pat["node_id"]
        new_pat = {k: v for k, v in pat.items() if k != "node_id"}
        if _is_var(str(nid)):
            new_pat["bind"] = nid
        else:
            new_pat["id"] = nid
        return new_pat
    return pat


def _filter_dict_to_str(expr: Any) -> str:
    """Convert a structured filter dict to a string expression for _eval_expr.

    Handles the YAML form::

        CONTAINS:
          - ?p.label
          - "Shemp"

    as well as comparison operators like ``">=": [?n.attributes.score, 90]``.
    """
    if isinstance(expr, str):
        return expr
    if not isinstance(expr, dict):
        return str(expr)

    op = next(iter(expr))
    args = expr[op]
    op_upper = op.upper()

    if op_upper in ("AND", "OR"):
        parts = [_filter_dict_to_str(a) for a in (args if isinstance(args, list) else [args])]
        return f" {op_upper} ".join(f"({p})" for p in parts)

    if op_upper == "NOT":
        inner = _filter_dict_to_str(args[0] if isinstance(args, list) else args)
        return f"NOT ({inner})"

    if op_upper in ("CONTAINS", "STARTS_WITH", "ENDS_WITH", "IS_TYPE", "MATCHES"):
        a, b = args[0], args[1]
        b_str = f'"{b}"' if isinstance(b, str) else str(b)
        return f"{op_upper}({a}, {b_str})"

    if op_upper == "BOUND":
        return f"BOUND({args if isinstance(args, str) else args[0]})"

    # Comparison operators: {">=": [left, right]} or {"IN": [left, [...]]}
    sym_map = {"EQ": "=", "==": "=", "NEQ": "!=", "!=": "!=", "LT": "<", "GT": ">", "LTE": "<=", "GTE": ">="}
    sym = sym_map.get(op_upper, op)  # use raw op for symbols like >=, <=, etc.
    if isinstance(args, list) and len(args) == 2:
        left, right = args[0], args[1]
        right_str = f'"{right}"' if isinstance(right, str) else str(right)
        return f"{left} {sym} {right_str}"

    return str(expr)


def _normalize_node_pattern(pattern: Dict) -> Dict:
    """Flatten ``{"node": "?var", "node_type": "X", ...}`` to ``{"bind": "?var", "type": "X", ...}``.

    When an explicit ``bind`` key is also present alongside ``node: "?var"``, the
    ``node`` value is treated as an id reference (variable or literal) to look up,
    and ``bind`` names the variable that receives the full node document.  This
    allows patterns like::

        - node: "?member"      # ?member holds a node_id string from a prior edge pattern
          bind: "?member_node" # fetch the full doc and bind it here
    """
    node_val = pattern["node"]
    if isinstance(node_val, str):
        node_pat = {k: v for k, v in pattern.items() if k != "node"}
        if "bind" in node_pat:
            # explicit bind present: node_val is an id reference, not the bind target
            node_pat.setdefault("id", node_val)
        else:
            node_pat["bind"] = node_val
    elif isinstance(node_val, dict):
        node_pat = dict(node_val)
    else:
        node_pat = {}
    # Normalise node_type → type (SHQL YAML uses node_type; engine uses type)
    if "node_type" in node_pat:
        node_pat["type"] = node_pat.pop("node_type")
    return node_pat


def _normalize_edge_pattern(pattern: Dict) -> Dict:
    """Flatten ``{"edge": "?var", "relation": "X", "members": [...], ...}`` to engine form."""
    edge_val = pattern["edge"]
    if isinstance(edge_val, str):
        edge_pat = {k: v for k, v in pattern.items() if k != "edge"}
        edge_pat["bind"] = edge_val
    elif isinstance(edge_val, dict):
        edge_pat = dict(edge_val)
    else:
        edge_pat = {}
    if "members" in edge_pat:
        edge_pat["members"] = [_normalize_member_pat(m) for m in edge_pat["members"]]
    return edge_pat


# ── Pattern evaluation loop ───────────────────────────────────────────────────

async def _evaluate_patterns(
    patterns: List[Any],
    graph_ids: List[str],
    pit: Optional[datetime],
    bindings: List[BindingSet],
    infer: bool = False,
) -> List[BindingSet]:
    for pattern in patterns:
        if not isinstance(pattern, dict):
            continue

        if "node" in pattern:
            node_pat = _normalize_node_pattern(pattern)
            bindings = await _eval_node_pattern(node_pat, graph_ids, pit, bindings)

        elif "edge" in pattern:
            edge_pat = _normalize_edge_pattern(pattern)
            bindings = await _eval_edge_pattern(edge_pat, graph_ids, pit, bindings, infer=infer)

        elif "filter" in pattern:
            fval = pattern["filter"]
            fstr = _filter_dict_to_str(fval) if isinstance(fval, dict) else str(fval)
            bindings = _eval_filter(fstr, bindings)

        elif "optional" in pattern:
            # Left outer join: keep original binding if optional branch produces no results
            optional_pats = pattern["optional"]
            new_bindings: List[BindingSet] = []
            for b in bindings:
                extended = await _evaluate_patterns(optional_pats, graph_ids, pit, [b], infer=infer)
                if extended:
                    new_bindings.extend(extended)
                else:
                    new_bindings.append(b)
            bindings = new_bindings

        elif "union" in pattern:
            union_result: List[BindingSet] = []
            seen: Set[str] = set()
            for branch in pattern["union"]:
                # branches are lists of patterns (not dicts with "patterns" key)
                branch_pats = branch if isinstance(branch, list) else branch.get("patterns", [])
                for b in await _evaluate_patterns(branch_pats, graph_ids, pit, deepcopy(bindings), infer=infer):
                    key = json.dumps({k: str(v) for k, v in sorted(b.items())}, sort_keys=True)
                    if key not in seen:
                        seen.add(key)
                        union_result.append(b)
            bindings = union_result

    return bindings


# ── Public entry point ────────────────────────────────────────────────────────

class SHQLResult:
    def __init__(self, alias: str, items: List[Dict], meta: Dict):
        self.alias = alias
        self.items = items
        self.meta  = meta

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alias": self.alias,
            "count": len(self.items),
            "items": self.items,
            "meta":  self.meta,
        }


def _from_refs(shql: Dict[str, Any]) -> List[str]:
    from_field = shql["from"]
    return [str(r) for r in ([from_field] if isinstance(from_field, str) else list(from_field))]


async def _authorize_query(shql: Dict[str, Any], account: AccountInDB) -> None:
    """Raise SHQLPermissionError unless `account` may query every graph the query reads.

    Runs BEFORE the result cache is consulted: the cache key does not include
    the caller, so a hit must only ever be served to someone already
    authorized for the same graphs. Rules (admins pass everything):

      * each `from:` graph needs the `query` operation on it — direct
        permissions.graphs for unowned graphs, space membership for
        space-scoped ones ("space_id/graph_id");
      * a logical graph additionally requires access to every graph it
        composes, since composition reads their data;
      * mesh references (dot-notation, or a bare mesh id) require the admin
        role — federation runs with the mesh's stored server credentials, not
        the caller's.
    """
    from .parser import SHQLPermissionError

    if "admin" in account.roles:
        return

    async def _check(gid: str, space_id: Optional[str]) -> None:
        try:
            await check_graph_permission(account, gid, "query", space_id=space_id, unowned=space_id is None)
        except PermissionDeniedError as e:
            raise SHQLPermissionError(str(e))

    for ref in _from_refs(shql):
        if ref.count(".") in (2, 3):
            raise SHQLPermissionError(
                f"Mesh reference '{ref}' requires the admin role (federated queries use the mesh's own credentials)"
            )
        space_id, gid = ref.split("/", 1) if "/" in ref else (None, ref)
        space_id = space_id or None
        await _check(gid, space_id)

        doc = await get_storage().hypergraphs.get(gid, space_id=space_id)
        if doc is None:
            if space_id is None and await get_storage().meshes.get(gid):
                raise SHQLPermissionError(
                    f"Mesh '{gid}' requires the admin role (federated queries use the mesh's own credentials)"
                )
            continue  # unknown graph: execution reports "not found" once access has been established
        if doc.type == "logical" and doc.composition:
            for member_id in doc.composition:
                member = await get_storage().hypergraphs.find_composition_member(member_id)
                if member:
                    await _check(member.id, member.space_id)


# ── Aggregate pushdown ────────────────────────────────────────────────────────
#
# `aggregate: {count, group_by}` is normally computed in memory over the
# matched rows, which are capped at the candidate limit. When the query is
# simple enough that storage can answer it exactly, the aggregate is computed
# by `store.aggregate(...)` instead: exact regardless of graph size, and never
# subject to the candidate caps. Anything the planner cannot prove equivalent
# returns None and takes the in-memory path unchanged.

_PUSHDOWN_NODE_KEYS = frozenset({"bind", "id", "type", "tags", "attributes", "status"})
_PUSHDOWN_EDGE_KEYS = frozenset({"bind", "id", "relation", "flavor", "tags", "attributes", "status"})


_AGGREGATE_KEYS = frozenset({"count", "group_by", *MEASURE_FNS})
_measure_requests = measure_requests   # (fn, projected row key) pairs; shared with federation merging


def _aggregate_in_memory(items: List[Dict], aggregate: Dict[str, Any]) -> Dict[str, Any]:
    """`aggregate:` over already-fetched rows, using the storage layer's reducer semantics.

    Result shape (keys present only when requested):
      count             number of rows
      sum/avg/min/max   {row_key: value} over all rows
      groups            {str(group value): row count}   ("unknown" if the row key is absent)
      group_measures    {str(group value): {fn: {row_key: value}}}
    """
    from hgai_module_storage.aggregate import reduce_values

    pairs = _measure_requests(aggregate)
    out: Dict[str, Any] = {}
    if "count" in aggregate:
        out["count"] = len(items)
    for fn, key in pairs:
        out.setdefault(fn, {})[key] = reduce_values(fn, (it.get(key) for it in items))
    if "group_by" in aggregate:
        field = aggregate["group_by"]
        buckets: Dict[str, List[Dict]] = {}
        for item in items:
            buckets.setdefault(str(item.get(field, "unknown")), []).append(item)
        out["groups"] = {k: len(v) for k, v in buckets.items()}
        if pairs:
            out["group_measures"] = {
                k: _shape_measures((fn, key, reduce_values(fn, (it.get(key) for it in v)))
                                   for fn, key in pairs)
                for k, v in buckets.items()
            }
    return out


def _shape_measures(triples: Any) -> Dict[str, Dict[str, Any]]:
    shaped: Dict[str, Dict[str, Any]] = {}
    for fn, key, value in triples:
        shaped.setdefault(fn, {})[key] = value
    return shaped


class _AggregatePlan:
    def __init__(
        self,
        store: Any,
        filters: Any,
        group_path: Optional[str],
        measures: List[Tuple[str, str, str]],
    ):
        self.store = store
        self.filters = filters
        self.group_path = group_path   # store field path, or None for a global aggregate
        self.measures = measures       # (fn, projected row key, store field path)


def _pushdown_field(key: Any, bind: Any, select_fields: List[str]) -> Optional[str]:
    """Store field path for a projected row key like `n.attributes.age`, or None if not pushdownable.

    The key must be `<pattern variable>.<scalar store field>` AND be projected by
    `select:` — otherwise the in-memory row has no such key and yields
    different (empty) results. `tags` is excluded: storage unwinds arrays for
    grouping and orders them differently for min/max, while the in-memory path
    treats the whole list as one value.
    """
    from hgai_module_storage.aggregate import UNWOUND_FIELDS, AggregateSpecError, validate_field_path

    if not isinstance(key, str) or not isinstance(bind, str) or not _is_var(bind):
        return None
    prefix = bind.lstrip("?") + "."
    if not key.startswith(prefix):
        return None
    path = key[len(prefix):]
    if f"{bind}.{path}" not in [f for f in select_fields if isinstance(f, str)]:
        return None
    try:
        validate_field_path(path)
    except AggregateSpecError:
        return None
    return None if path in UNWOUND_FIELDS else path


class _SinglePattern:
    def __init__(self, store: Any, filters: Any, bind: Optional[str]):
        self.store = store
        self.filters = filters
        self.bind = bind


def _single_pattern(
    where_patterns: List[Any],
    graph_ids: List[str],
    pit: Optional[datetime],
    infer: bool,
    distinct: bool,
) -> Optional[_SinglePattern]:
    """The store + filters for a query that is exactly one simple `node:`/`edge:` pattern, else None.

    "Simple": no filters, OPTIONAL, UNION or members, no variables in `id`/
    `relation`, and no `infer`/`distinct` (both change which rows exist).
    Shared by aggregate and paging pushdown so both accept the same shapes.
    """
    if infer or distinct or not graph_ids:
        return None
    if len(where_patterns) != 1 or not isinstance(where_patterns[0], dict):
        return None

    raw = where_patterns[0]
    if "node" in raw:
        pattern = _normalize_node_pattern(raw)
        if set(pattern) - _PUSHDOWN_NODE_KEYS:
            return None
        node_id = pattern.get("id")
        if node_id is not None and _is_var(str(node_id)):
            return None
        filters = _node_filters(
            pattern, graph_ids, pit, [node_id] if node_id is not None else None,
        )
        return _SinglePattern(get_storage().hypernodes, filters, pattern.get("bind"))
    if "edge" in raw:
        pattern = _normalize_edge_pattern(raw)
        if set(pattern) - _PUSHDOWN_EDGE_KEYS:
            return None
        if any(v is not None and _is_var(str(v)) for v in (pattern.get("id"), pattern.get("relation"))):
            return None
        filters = _edge_filters(pattern, graph_ids, pit,
                                relation=pattern.get("relation"), edge_id=pattern.get("id"))
        return _SinglePattern(get_storage().hyperedges, filters, pattern.get("bind"))
    return None


def _plan_aggregate_pushdown(
    *,
    aggregate: Dict[str, Any],
    where_patterns: List[Any],
    select_fields: List[str],
    graph_ids: List[str],
    pit: Optional[datetime],
    infer: bool,
    distinct: bool,
) -> Optional[_AggregatePlan]:
    """Return a plan when `aggregate` can be served exactly by storage, else None.

    Eligible only for a `_single_pattern` query where every `group_by` / `sum` /
    `avg` / `min` / `max` key passes `_pushdown_field`.
    """
    if not isinstance(aggregate, dict) or not (_AGGREGATE_KEYS & set(aggregate)):
        return None
    single = _single_pattern(where_patterns, graph_ids, pit, infer, distinct)
    if single is None:
        return None

    bind = single.bind
    group_path: Optional[str] = None
    if "group_by" in aggregate:
        group_path = _pushdown_field(aggregate["group_by"], bind, select_fields)
        if group_path is None:
            return None

    measures: List[Tuple[str, str, str]] = []
    try:
        pairs = _measure_requests(aggregate)
    except TypeError:
        return None
    for fn, key in pairs:
        path = _pushdown_field(key, bind, select_fields)
        if path is None:
            return None
        measures.append((fn, key, path))
    return _AggregatePlan(single.store, single.filters, group_path, measures)


async def _run_aggregate_pushdown(
    plan: _AggregatePlan, aggregate: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Execute a plan and shape it exactly like `_aggregate_in_memory`.

    Group keys are `str(value)` (a missing/null value is "None"), matching the
    in-memory path. Returns None — caller falls back to memory — in the one
    case that cannot be merged exactly: distinct group values that collide
    after `str()` (e.g. 1 and "1") while measures are requested.
    """
    from hgai_module_storage.filters import AggregateMeasure, AggregateSpec

    measures = [AggregateMeasure(fn, path, alias=f"m{i}") for i, (fn, _k, path) in enumerate(plan.measures)]

    def shape(row: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        return _shape_measures((fn, key, row[f"m{i}"]) for i, (fn, key, _p) in enumerate(plan.measures))

    out: Dict[str, Any] = {}
    if plan.group_path is None:
        (row,) = await plan.store.aggregate(
            plan.filters, AggregateSpec(measures=[AggregateMeasure("count")] + measures),
        )
        if "count" in aggregate:
            out["count"] = row["count"]
        out.update(shape(row))
        return out

    rows = await plan.store.aggregate(
        plan.filters,
        AggregateSpec(group_by=[plan.group_path], measures=[AggregateMeasure("count")] + measures),
    )
    groups: Dict[str, int] = {}
    group_measures: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for row in rows:
        key = str(row[plan.group_path])
        if key in groups and plan.measures:
            return None
        groups[key] = groups.get(key, 0) + row["count"]
        if plan.measures:
            group_measures[key] = shape(row)
    if "count" in aggregate:
        out["count"] = sum(groups.values())
    if plan.measures:
        (total,) = await plan.store.aggregate(plan.filters, AggregateSpec(measures=measures))
        out.update(shape(total))
    out["groups"] = groups
    if plan.measures:
        out["group_measures"] = group_measures
    return out


# ── Paging pushdown (order_by / offset / limit) ──────────────────────────────
#
# For a `_single_pattern` query, the storage layer sorts and pages the matching
# documents itself (`search_ordered`, or plain `search` with skip/limit when
# there is no `order_by`), so the result is exact however many documents match
# and never limited by the candidate caps. Anything else keeps the in-memory
# path (fetch up to the cap, sort, slice).

class _PagingPlan:
    def __init__(self, single: _SinglePattern, order: List[Tuple[str, bool]]):
        self.single = single
        self.order = order   # [(store field path, descending)]; empty = natural order


def _pushdown_sort_field(key: str, bind: str, select_fields: List[str]) -> Optional[str]:
    """Store field path for one `order_by` key, or None if it can't be pushed down.

    In-memory ordering reads either the projected row key or, failing that,
    the whole bound document from the row. Both equal the document field, so
    a key is pushdownable when `select:` projects that exact key or projects
    the whole variable. Otherwise the in-memory value is missing for every
    row (ordering is a no-op there) and storage ordering would differ.
    """
    from hgai_module_storage.aggregate import UNWOUND_FIELDS, AggregateSpecError, validate_field_path

    prefix = bind.lstrip("?") + "."
    if not key.startswith(prefix):
        return None
    path = key[len(prefix):]
    whole_var = not select_fields or select_fields == ["*"] or "*" in select_fields or bind in select_fields
    if not whole_var and f"{bind}.{path}" not in select_fields:
        return None
    try:
        validate_field_path(path)
    except AggregateSpecError:
        return None
    return None if path in UNWOUND_FIELDS else path


def _plan_paging_pushdown(
    *,
    order_by: Any,
    where_patterns: List[Any],
    select_fields: List[str],
    graph_ids: List[str],
    pit: Optional[datetime],
    infer: bool,
    distinct: bool,
) -> Optional[_PagingPlan]:
    single = _single_pattern(where_patterns, graph_ids, pit, infer, distinct)
    if single is None or not isinstance(single.bind, str) or not _is_var(single.bind):
        return None   # rows are built from the bound variable

    order: List[Tuple[str, bool]] = []
    if order_by:
        for key, descending in _parse_order_by(order_by):
            path = _pushdown_sort_field(key, single.bind, select_fields)
            if path is None:
                return None
            order.append((path, descending))
        if len({p for p, _ in order}) != len(order):
            return None   # duplicate keys: in-memory applies both passes, storage rejects
    return _PagingPlan(single, order)


async def _run_paging_pushdown(
    plan: _PagingPlan, select_fields: List[str], offset: int, limit: int,
) -> List[Dict]:
    """Fetch one sorted page from storage and project it exactly like the in-memory path."""
    store, filters = plan.single.store, plan.single.filters
    if plan.order:
        docs = await store.search_ordered(filters, plan.order, skip=offset, limit=limit)
    else:
        docs = await store.search(filters, skip=offset, limit=limit)
    bindings: List[BindingSet] = []
    for doc in docs:
        for _f in _SKOS_FIELDS:
            doc.pop(_f, None)
        bindings.append({plan.single.bind: doc})
    return _project_select(bindings, select_fields)


async def execute_shql(shql_text: str, use_cache: bool = True, *, account: AccountInDB) -> SHQLResult:
    """Parse and execute an SHQL query string on behalf of `account`.

    `account` is required and enforced: see `_authorize_query`. Callers acting
    for the system itself (there are none today) must pass an explicit admin
    account rather than skip the check.
    """
    from .parser import parse_shql, validate_shql, SHQLError
    from hgai.core.cache import get_cached_result, set_cached_result

    shql   = parse_shql(shql_text)
    errors = validate_shql(shql)
    if errors:
        raise SHQLError(f"SHQL validation errors: {'; '.join(errors)}")

    await _authorize_query(shql, account)

    cache_key = "shql:" + hashlib.md5(
        json.dumps(shql, sort_keys=True, default=str).encode()
    ).hexdigest()

    if use_cache:
        cached = await get_cached_result(cache_key)
        if cached:
            return SHQLResult(
                alias=cached.get("alias", "result"),
                items=cached.get("items", []),
                meta={**cached.get("meta", {}), "cached": True},
            )

    from_field      = shql["from"]
    select_fields   = shql.get("select", ["*"])
    where_patterns  = shql.get("where", [])
    alias           = shql.get("as", "result")
    limit           = shql.get("limit", 500)
    offset          = shql.get("offset", 0)
    distinct        = shql.get("distinct", False)
    order_by        = shql.get("order_by")
    infer           = shql.get("infer", False)
    aggregate       = shql.get("aggregate", {})

    if isinstance(select_fields, str):
        select_fields = [select_fields]

    # Partition from: values into dot-notation mesh refs and plain local refs
    # 2-dot = mesh.server.graph (unowned), 3-dot = mesh.server.space.graph (space-scoped)
    raw_ids = [from_field] if isinstance(from_field, str) else list(from_field)
    dot_refs   = [r for r in raw_ids if r.count(".") in (2, 3)]
    plain_refs = [r for r in raw_ids if r.count(".") not in (2, 3)]

    # Handle dot-notation mesh refs (mesh_id.server_id.graph_id)
    dot_items: List[Dict] = []
    fed_partials: List[Dict] = []     # {server_id, meta} of each federated server that answered
    fed_errors: List[Dict] = []       # {server_id, error} of each that did not
    if dot_refs:
        try:
            from hgai_module_mesh.engine import execute_dot_refs
            dot_result = await execute_dot_refs(dot_refs, shql_text, use_cache=use_cache, account=account)
            dot_items = dot_result["items"]
            fed_partials.extend(dot_result.get("partials", []))
            fed_errors.extend(dot_result.get("errors", []))
        except ImportError:
            from .parser import SHQLError
            raise SHQLError("Mesh dot-notation requires hgai_module_mesh to be installed")

    # Resolve local graph IDs to hypergraph_id refs used in node/edge queries.
    # Supports "graph_id" (unowned) and "space_id/graph_id" (space-scoped) formats.
    from hgai.core.engine import _hypergraph_ref
    graph_ids: List[str] = []
    for ref in plain_refs:
        if "/" in ref:
            space_part, gid = ref.split("/", 1)
            doc = await get_storage().hypergraphs.get(gid, space_id=space_part)
        else:
            gid = ref
            doc = await get_storage().hypergraphs.get(gid, space_id=None)
            if not doc:
                # Check if it's a bare mesh ID — route to federation
                mesh_doc = await get_storage().meshes.get(gid)
                if mesh_doc:
                    try:
                        from hgai_module_mesh.engine import federated_shql
                        fed = await federated_shql(gid, shql_text, use_cache=use_cache, account=account)
                        dot_items.extend(fed["items"])
                        fed_partials.extend(fed.get("partials", []))
                        fed_errors.extend(fed.get("errors", []))
                        continue
                    except ImportError:
                        from .parser import SHQLError
                        raise SHQLError("Mesh federation requires hgai_module_mesh to be installed")
        if not doc:
            from .parser import SHQLError
            raise SHQLError(f"Hypergraph not found: {ref!r}")
        if doc.type == "logical" and doc.composition:
            # Logical graph composition: resolve each member graph
            for member_id in doc.composition:
                member_doc = await get_storage().hypergraphs.find_composition_member(member_id)
                if member_doc:
                    graph_ids.append(
                        _hypergraph_ref(member_doc.id, member_doc.space_id)
                    )
        else:
            graph_ids.append(_hypergraph_ref(doc.id, doc.space_id))
    graph_ids = list(set(graph_ids))

    # Parse point-in-time
    pit: Optional[datetime] = None
    if "at" in shql:
        from dateutil.parser import parse as parse_dt
        pit = parse_dt(shql["at"])

    # Federation: every server aggregates its own graphs and returns partials
    # (see aggregate_merge); they are merged with this server's own partial
    # below. `distinct` needs the merged rows, so it keeps the row-based path.
    federated = bool(dot_items) or bool(fed_partials)
    merge_partials = bool(aggregate) and federated and not distinct
    agg_req = partial_aggregate(aggregate) if merge_partials else aggregate

    # Aggregate pushdown: when storage can answer `aggregate:` exactly, it does,
    # independent of the candidate caps. With federation this is the *local*
    # partial only.
    agg_results: Dict[str, Any] = {}
    pushed_down = False
    if aggregate:
        plan = _plan_aggregate_pushdown(
            aggregate=agg_req, where_patterns=where_patterns, select_fields=select_fields,
            graph_ids=graph_ids, pit=pit, infer=infer, distinct=distinct,
        )
        if plan is not None:
            pushed = await _run_aggregate_pushdown(plan, agg_req)
            if pushed is not None:
                agg_results, pushed_down = pushed, True

    # Paging pushdown: storage sorts and pages the rows itself. Needs every
    # aggregate (if any) to be storage-computed already — an in-memory
    # aggregate needs all rows — and no federated rows to merge in.
    rows_pushed_down = False
    items: List[Dict] = []
    if graph_ids and not federated and (not aggregate or pushed_down) and not (pushed_down and limit == 0):
        paging = _plan_paging_pushdown(
            order_by=order_by, where_patterns=where_patterns, select_fields=select_fields,
            graph_ids=graph_ids, pit=pit, infer=infer, distinct=distinct,
        )
        if paging is not None:
            items = await _run_paging_pushdown(paging, select_fields, offset, limit)
            rows_pushed_down = True

    # Execute local patterns (skipped when no local graphs). A pushed-down
    # aggregate with `limit: 0` needs no rows at all, so nothing is fetched.
    truncated_by: List[str] = []
    if graph_ids and not rows_pushed_down and not (pushed_down and limit == 0):
        from hgai.core.inference import truncation_sink
        sink_token = truncation_sink.set(truncated_by)
        try:
            bindings = await _evaluate_patterns(where_patterns, graph_ids, pit, [{}], infer=infer)
        finally:
            truncation_sink.reset(sink_token)
        bindings = await _resolve_node_bindings(bindings, graph_ids)
        items = _project_select(bindings, select_fields)
    elif not rows_pushed_down:
        items = []

    # Merge dot-notation / federation results
    local_items = items
    items = items + dot_items

    # DISTINCT
    if distinct:
        seen_keys: Set[str] = set()
        deduped: List[Dict] = []
        for item in items:
            k = json.dumps(item, sort_keys=True, default=str)
            if k not in seen_keys:
                seen_keys.add(k)
                deduped.append(item)
        items = deduped

    # AGGREGATE — `count`, `group_by`, and `sum`/`avg`/`min`/`max`, spread
    # additively into meta (see `_aggregate_in_memory` for the shape). Computed
    # over the full matched, deduplicated item set — before ORDER
    # BY/OFFSET/LIMIT paginate it — so the values describe the whole result,
    # not just the returned page. Every field named (`group_by`, `sum`, ...)
    # is a *projected row key*, since an SHQL item is a `select:`-projected
    # row keyed by variable — e.g. `select: [?e.relation]` produces the row
    # key `"e.relation"`. Skipped when storage already answered it (pushdown).
    federation_merged = False
    if merge_partials:
        local_part = agg_results if pushed_down else (
            _aggregate_in_memory(local_items, agg_req) if graph_ids else None
        )
        parts = ([local_part] if local_part is not None else []) + [p["meta"] for p in fed_partials]
        merged = merge_aggregate_meta(parts, aggregate) if parts else None
        if merged is not None:
            agg_results, federation_merged = merged, True
        else:
            # A server could not supply the partials (e.g. an older version):
            # aggregate the merged rows instead, as before.
            agg_results = _aggregate_in_memory(items, aggregate)
    elif aggregate and not pushed_down:
        agg_results = _aggregate_in_memory(items, aggregate)

    # ORDER BY — `order_by` accepts a single field or a list of fields, each
    # optionally suffixed with " asc"/" desc" (case-insensitive, SQL-style;
    # e.g. "?e.relation desc"), for multi-key sort with independent
    # directions per key. A bare field with no suffix sorts ascending.
    if order_by and not rows_pushed_down:
        items = _apply_order_by(items, order_by)

    # OFFSET / LIMIT
    if not rows_pushed_down:
        items = items[offset: offset + limit]

    meta = {
        "graph_ids":     graph_ids,
        "dot_refs":      dot_refs if dot_refs else None,
        "pit":           pit.isoformat() if pit else None,
        "pattern_count": len(where_patterns),
        "infer":         infer,
        "cached":        False,
        # True when a pattern hit its candidate cap: `items` (and any
        # in-memory count/group_by aggregates) cover only the fetched
        # candidates. Aggregates with `aggregate_pushdown: true` were computed
        # by storage and are exact regardless of this flag.
        "truncated":     bool(truncated_by),
        "truncated_by":  truncated_by,
        # Storage computed the aggregate — on every participating server when federated.
        "aggregate_pushdown": (
            (pushed_down or not graph_ids) and all(p["meta"].get("aggregate_pushdown") for p in fed_partials)
            if federation_merged else pushed_down
        ),
        # True when storage sorted and paged the rows (order_by/offset/limit):
        # `items` are then exact and not subject to the candidate caps.
        "paging_pushdown": rows_pushed_down,
        **agg_results,
    }
    if federated or fed_errors:
        meta["federation"] = {
            "servers": [p["server_id"] for p in fed_partials],
            "errors": fed_errors,           # servers that failed are absent from rows AND aggregates
            "aggregate_merged": federation_merged,
        }
        for p in fed_partials:               # a server's truncation is this result's truncation
            for what in p["meta"].get("truncated_by", []) or []:
                meta["truncated_by"] = meta["truncated_by"] + [f"{p['server_id']}: {what}"]
        meta["truncated"] = bool(meta["truncated_by"])

    result = SHQLResult(alias=alias, items=items, meta=meta)

    if use_cache:
        await set_cached_result(cache_key, result.to_dict(), graph_ids=graph_ids)

    return result
