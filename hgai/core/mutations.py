"""Shared audit-trail helpers for any resource that tracks a `mutations`
list (hypernodes, hyperedges, notes, ...): one entry per create/update, each
with who (`by`), when (`ts`), what kind (`mutation`), and which fields
actually changed (`delta`). A candidate entry that would be empty (nothing
actually changed) or identical to the most recently recorded entry (same
mutation kind + same delta) is never persisted — see `append_mutation`.

Extracted from hgai.core.engine (where hypernode/hyperedge mutation tracking
was first built) so other first-class resources outside the hypergraph
model — like notes — can reuse the exact same semantics without importing
engine.py's internals.
"""

from typing import Any, Dict, List

from hgai.models.common import now_utc


def is_blank(value: Any) -> bool:
    """True for the "nothing was really provided" sentinel values.

    Used only to keep a create-mutation's delta focused on fields the caller
    actually populated, instead of every default (None/[]/{}) tracked field.
    """
    return value is None or value == [] or value == {} or value == ""


def create_delta(doc: Dict[str, Any], tracked_fields: List[str]) -> List[Dict[str, Any]]:
    """Delta for a brand-new document: every non-blank tracked field, old=None."""
    return [
        {"field": f, "old": None, "new": doc.get(f)}
        for f in tracked_fields
        if not is_blank(doc.get(f))
    ]


def update_delta(
    existing_dump: Dict[str, Any], dumped: Dict[str, Any], tracked_fields: List[str]
) -> List[Dict[str, Any]]:
    """Delta for an update: only fields the caller supplied AND that actually
    changed value versus the existing document — a no-op resubmission of an
    already-current value produces no delta entry for that field."""
    delta = []
    for f in tracked_fields:
        if f not in dumped:
            continue
        old = existing_dump.get(f)
        new = dumped.get(f)
        if old != new:
            delta.append({"field": f, "old": old, "new": new})
    return delta


def append_mutation(
    existing_mutations: List[Dict[str, Any]],
    mutation_type: str,
    delta: List[Dict[str, Any]],
    by: str,
) -> List[Dict[str, Any]]:
    """Return the mutations list with a new entry appended, unless the
    candidate is redundant — in which case the original list object is
    returned unchanged (by identity), so callers can detect "nothing to
    persist" with `result is existing_mutations` instead of a deep compare.

    Redundant means: no fields actually changed (empty delta), or the
    candidate (mutation kind + delta) is identical to the most recently
    recorded entry — i.e. the same net change happening again back-to-back.
    """
    if not delta:
        return existing_mutations
    if existing_mutations:
        last = existing_mutations[-1]
        if last.get("mutation") == mutation_type and last.get("delta") == delta:
            return existing_mutations
    return existing_mutations + [
        {"ts": now_utc(), "by": by, "mutation": mutation_type, "delta": delta}
    ]
