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
from typing import Any, Dict, List, Optional, Set

import yaml

from hgai.db.storage import get_storage
from hgai_module_storage.filters import HyperedgeSearchFilters, HypernodeSearchFilters

_SKOS_FIELDS = ("skos_broader", "skos_narrower", "skos_related")

BindingSet = Dict[str, Any]


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
      - {"node": {"bind": "?var", "id": ...}}   nested node form

    Returns an updated BindingSet if all patterns are satisfied, or None.
    """
    new_binding = dict(binding)
    used: Set[int] = set()

    for pat in member_patterns:
        node_pat: Dict[str, Any] = _member_pat_to_node_pat(pat)
        if not node_pat and not isinstance(pat, (str, dict)):
            return None

        bind_var = node_pat.get("bind")
        req_id   = node_pat.get("id")
        req_type = node_pat.get("type")   # not used in member matching (type lives on the node doc)

        # If the bind variable is already resolved, treat its id as the required id
        if bind_var and bind_var in new_binding:
            existing = new_binding[bind_var]
            req_id = existing.get("id") if isinstance(existing, dict) else existing

        # Resolve any variable reference in req_id
        if req_id is not None:
            req_id = _resolve_var(req_id, new_binding) if _is_var(str(req_id)) else req_id

        # Find the first unused edge member that satisfies the requirement
        matched_idx = None
        for i, member in enumerate(edge_members):
            if i in used:
                continue
            mid = member.get("node_id") if isinstance(member, dict) else member
            if req_id is not None and mid != req_id:
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
    """Like _match_members but expands wildcard (id-unconstrained) member patterns
    over ALL matching edge members, producing one BindingSet per member.

    Anchor patterns (those with an explicit ``id``) are matched first to determine
    which member slots are spoken for.  Each remaining member is then yielded as a
    separate binding for the single wildcard pattern.

    Falls back to the single-result ``_match_members`` behaviour when there are
    multiple wildcard patterns (not yet expanded) or no member patterns at all.
    """
    if not member_patterns:
        return [dict(binding)]

    # Classify patterns: anchor (has a required id) vs wildcard (no id constraint)
    anchor_pats: List[tuple] = []   # (raw_pat, resolved_req_id)
    wildcard_pats: List[Any] = []

    for pat in member_patterns:
        np = _member_pat_to_node_pat(pat)
        req_id = np.get("id")
        if req_id and _is_var(str(req_id)):
            resolved = binding.get(req_id)
            req_id = resolved.get("id") if isinstance(resolved, dict) else resolved
        if req_id:
            anchor_pats.append((pat, req_id))
        else:
            wildcard_pats.append(pat)

    # No wildcards — use original single-result matcher unchanged
    if not wildcard_pats:
        result = _match_members(edge_members, member_patterns, binding)
        return [result] if result is not None else []

    # Match anchor patterns first to pin down used member slots
    used_indices: Set[int] = set()
    anchor_binding = dict(binding)

    for pat, req_id in anchor_pats:
        np = _member_pat_to_node_pat(pat)
        bind_var = np.get("bind")
        matched_idx = None
        for i, member in enumerate(edge_members):
            if i in used_indices:
                continue
            mid = member.get("node_id") if isinstance(member, dict) else member
            if mid == req_id:
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

async def _eval_node_pattern(
    pattern: Dict,
    graph_ids: List[str],
    pit: Optional[datetime],
    bindings: List[BindingSet],
) -> List[BindingSet]:
    bind_var  = pattern.get("bind")
    node_id   = pattern.get("id")
    node_type = pattern.get("type")
    tags      = pattern.get("tags")
    attributes = pattern.get("attributes") or {}
    status    = pattern.get("status", "active")

    result: List[BindingSet] = []

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
            result.append(binding)
            continue

        # Build node search filters
        node_ids_in = None
        if node_id is not None:
            resolved_id = _resolve_var(node_id, binding) if _is_var(str(node_id)) else node_id
            if resolved_id is None:
                continue
            node_ids_in = [resolved_id]

        filters = HypernodeSearchFilters(
            hypergraph_ids=graph_ids,
            node_type=node_type,
            status=status,
            tags=tags if not tags or isinstance(tags, list) else [tags],
            pit=pit,
            node_ids_in=node_ids_in,
            attributes=attributes if attributes else None,
        )
        docs = await get_storage().hypernodes.search(filters, skip=0, limit=2000)

        for doc in docs:
            for _f in _SKOS_FIELDS:
                doc.pop(_f, None)
            new_binding = dict(binding)
            if bind_var:
                new_binding[bind_var] = doc
            result.append(new_binding)

    return result


async def _eval_edge_pattern(
    pattern: Dict,
    graph_ids: List[str],
    pit: Optional[datetime],
    bindings: List[BindingSet],
) -> List[BindingSet]:
    bind_var       = pattern.get("bind")
    relation       = pattern.get("relation")
    flavor         = pattern.get("flavor")
    tags           = pattern.get("tags")
    attributes     = pattern.get("attributes") or {}
    member_patterns = pattern.get("members") or []
    status         = pattern.get("status", "active")

    result: List[BindingSet] = []

    for binding in bindings:
        # Already bound: verify relation matches
        if bind_var and bind_var in binding:
            existing = binding[bind_var]
            if isinstance(existing, dict):
                if relation and existing.get("relation") != relation:
                    continue
                if flavor and existing.get("flavor") != flavor:
                    continue
            result.append(binding)
            continue

        # Resolve relation variable if needed
        resolved_rel = None
        if relation:
            resolved_rel = _resolve_var(relation, binding) if _is_var(str(relation)) else relation

        # Add member constraints from already-bound variables to narrow the query
        bound_node_ids: List[str] = []
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

        filters = HyperedgeSearchFilters(
            hypergraph_ids=graph_ids,
            relation=resolved_rel,
            flavor=flavor,
            status=status,
            tags=tags if not tags or isinstance(tags, list) else [tags],
            pit=pit,
            member_node_ids_all=bound_node_ids if bound_node_ids else None,
            attributes=attributes if attributes else None,
        )
        docs = await get_storage().hyperedges.search(filters, skip=0, limit=2000)

        for doc in docs:
            for _f in _SKOS_FIELDS:
                doc.pop(_f, None)
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

    docs = await get_storage().hypernodes.find_by_ids(
        list(ids_needed), graph_ids
    )
    node_map: Dict[str, Dict] = {}
    for doc in docs:
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
) -> List[BindingSet]:
    for pattern in patterns:
        if not isinstance(pattern, dict):
            continue

        if "node" in pattern:
            node_pat = _normalize_node_pattern(pattern)
            bindings = await _eval_node_pattern(node_pat, graph_ids, pit, bindings)

        elif "edge" in pattern:
            edge_pat = _normalize_edge_pattern(pattern)
            bindings = await _eval_edge_pattern(edge_pat, graph_ids, pit, bindings)

        elif "filter" in pattern:
            fval = pattern["filter"]
            fstr = _filter_dict_to_str(fval) if isinstance(fval, dict) else str(fval)
            bindings = _eval_filter(fstr, bindings)

        elif "optional" in pattern:
            # Left outer join: keep original binding if optional branch produces no results
            optional_pats = pattern["optional"]
            new_bindings: List[BindingSet] = []
            for b in bindings:
                extended = await _evaluate_patterns(optional_pats, graph_ids, pit, [b])
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
                for b in await _evaluate_patterns(branch_pats, graph_ids, pit, deepcopy(bindings)):
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


async def execute_shql(shql_text: str, use_cache: bool = True) -> SHQLResult:
    """Parse and execute an SHQL query string."""
    from .parser import parse_shql, validate_shql, SHQLError
    from hgai.core.cache import get_cached_result, set_cached_result

    shql   = parse_shql(shql_text)
    errors = validate_shql(shql)
    if errors:
        raise SHQLError(f"SHQL validation errors: {'; '.join(errors)}")

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

    if isinstance(select_fields, str):
        select_fields = [select_fields]

    # Partition from: values into dot-notation mesh refs and plain local refs
    # 2-dot = mesh.server.graph (unowned), 3-dot = mesh.server.space.graph (space-scoped)
    raw_ids = [from_field] if isinstance(from_field, str) else list(from_field)
    dot_refs   = [r for r in raw_ids if r.count(".") in (2, 3)]
    plain_refs = [r for r in raw_ids if r.count(".") not in (2, 3)]

    # Handle dot-notation mesh refs (mesh_id.server_id.graph_id)
    dot_items: List[Dict] = []
    if dot_refs:
        try:
            from hgai_module_mesh.engine import execute_dot_refs
            dot_result = await execute_dot_refs(dot_refs, shql_text, "shql", use_cache=use_cache)
            dot_items = dot_result["items"]
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
                        fed = await federated_shql(gid, shql_text, use_cache=use_cache)
                        dot_items.extend(fed["items"])
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

    # Execute local patterns (skipped when no local graphs)
    if graph_ids:
        bindings = await _evaluate_patterns(where_patterns, graph_ids, pit, [{}])
        bindings = await _resolve_node_bindings(bindings, graph_ids)
        items = _project_select(bindings, select_fields)
    else:
        items = []

    # Merge dot-notation / federation results
    items.extend(dot_items)

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

    # ORDER BY
    if order_by:
        ob = str(order_by).lstrip("?")

        def sort_key(row: Dict) -> Any:
            if ob in row:
                v = row[ob]
                return v if v is not None else ""
            parts = ob.split(".", 1)
            if parts[0] in row:
                v = row[parts[0]]
                if len(parts) > 1 and isinstance(v, dict):
                    v = _get_nested(v, parts[1])
                return v if v is not None else ""
            return ""

        items = sorted(items, key=sort_key)

    # OFFSET / LIMIT
    items = items[offset: offset + limit]

    meta = {
        "graph_ids":     graph_ids,
        "dot_refs":      dot_refs if dot_refs else None,
        "pit":           pit.isoformat() if pit else None,
        "pattern_count": len(where_patterns),
        "cached":        False,
    }

    result = SHQLResult(alias=alias, items=items, meta=meta)

    if use_cache:
        await set_cached_result(cache_key, result.to_dict(), graph_ids=graph_ids)

    return result
