"""Semantic inferencing for HypergraphAI.

Relation semantics (which relations are transitive, symmetric, each other's
inverse, or broader/narrower than one another) are never hardcoded here —
they're declared as ordinary hyperedges asserting a small, fixed set of
control-vocabulary relation strings ("owl:transitive", "owl:symmetric",
"owl:inverse-of", "skos:broaderTransitive", "skos:narrowerTransitive", ...)
between relation-hypernodes. This module recognizes those strings; it never
knows anything about a specific domain relation. See
docs/dev_notes/skhg-inferencing-notes.md.

`atomic_pairs`, `get_axiom_edges`, and `walk_closure` are the shared
primitives every higher-level reasoning operation is built from.
`expand_edge`/`expand_edge_closure` (inverse-of/symmetric/superproperty
expansion) and `check_transitive` (transitive-closure reachability) are
both wired into HQL behind the same `infer: true` flag.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from hgai.db.storage import get_storage
from hgai_module_storage.filters import TransitiveSearchFilter


def atomic_pairs(members: List[Dict[str, Any]], flavor: str) -> List[Tuple[str, str]]:
    """Decompose a hyperedge's members into the directed binary facts it
    actually represents, given its flavor.

    `hub`: the first member (by `seq`) is the hub; every other member is a
    spoke. Represents N independent (hub, spoke) facts — e.g. "adam is
    father of cain/abel/seth" — not one N-ary fact about all spokes at once.

    `symmetric`: every member is mutually equivalent to every other. Returns
    both directions of every pair — e.g. sibling(moe, larry, curly) yields
    (moe,larry), (larry,moe), (moe,curly), (curly,moe), (larry,curly),
    (curly,moe) — so downstream consumers never need flavor-specific
    handling once they have this list.

    Raises on any other flavor value — `EdgeFlavor` only ever produces
    "hub" or "symmetric", so anything else means a caller passed something
    that didn't come from a real hyperedge, not a case to degrade quietly.
    """
    ordered = sorted(members, key=lambda m: (m.get("seq", 0) if isinstance(m, dict) else m.seq))
    ids = [m["node_id"] if isinstance(m, dict) else m.node_id for m in ordered]

    if flavor == "hub":
        if not ids:
            return []
        hub, spokes = ids[0], ids[1:]
        return [(hub, spoke) for spoke in spokes]

    if flavor == "symmetric":
        return [(a, b) for a in ids for b in ids if a != b]

    raise ValueError(f"atomic_pairs: unsupported flavor {flavor!r}")


async def get_axiom_edges(
    relation_id: str,
    axiom: str,
    graph_ids: List[str],
    pit: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Find axiom hyperedges asserting `axiom` about `relation_id`.

    An axiom hyperedge is an ordinary, user/agent-asserted hyperedge whose
    `relation` is a recognized control-vocabulary string and whose members
    include the relation-hypernode(s) it's making an assertion about — e.g.
    `relation="owl:transitive", members=[rel:contains]` or
    `relation="skos:narrowerTransitive", members=[rel:parent, rel:father]`.
    This is a plain hyperedge query; nothing here decides which relations
    carry which axioms.
    """
    tsf = TransitiveSearchFilter(
        hypergraph_ids=graph_ids,
        relation=axiom,
        member_node_ids=[relation_id],
        pit=pit,
    )
    return await get_storage().hyperedges.find_for_transitive(tsf)


async def walk_closure(
    start_id: str,
    relation: str,
    graph_ids: List[str],
    direction: str = "forward",
    max_depth: int = 10,
    pit: Optional[datetime] = None,
) -> Dict[str, Tuple[str, str]]:
    """Cycle-safe BFS over hyperedges of `relation`, starting from `start_id`.

    Shared by both reasoning shapes in this system: walking *fact* edges
    (e.g. "contains" hyperedges, to answer "is B transitively contained in
    A?") and walking *axiom* edges (e.g. "skos:narrowerTransitive" edges
    between relation-hypernodes, to project a fact from a narrower relation
    up through however many broader relations it has). Both are just "BFS
    over hyperedges of one relation" once each edge is decomposed into
    atomic pairs via `atomic_pairs` — this function doesn't distinguish
    fact-relations from axiom-relations at all.

    `direction="forward"` follows each atomic pair (a, b) from a to b (a is
    the already-reached node, b is newly reached); `direction="backward"`
    follows it from b to a — e.g. walking from a narrower relation up to its
    broader ancestors via `skos:narrowerTransitive` edges (whose atomic
    pairs are (broader, narrower) per hub decomposition) requires
    `direction="backward"`.

    Returns `{reached_node_id: (via_hyperedge_id, predecessor_node_id)}` for
    every node reachable from `start_id` (excluding `start_id` itself).
    `via_hyperedge_id` is the specific edge that first reached that node;
    `predecessor_node_id` is the node one hop closer to `start_id`, so a
    caller can reconstruct the full explanatory path by following
    predecessors back to `start_id` (see `check_transitive`'s `path` mode).
    Cycle-safe: a node already reached is never re-expanded, regardless of
    how many further edges lead back to it. Bounded by `max_depth` hops as
    a belt-and-suspenders safety valve underneath that cycle guard.
    """
    if direction not in ("forward", "backward"):
        raise ValueError(f"walk_closure: direction must be 'forward' or 'backward', got {direction!r}")

    reached: Dict[str, Tuple[str, str]] = {}
    visited: Set[str] = {start_id}
    frontier = [start_id]
    depth = 0

    while frontier and depth < max_depth:
        depth += 1
        tsf = TransitiveSearchFilter(
            hypergraph_ids=graph_ids,
            relation=relation,
            member_node_ids=frontier,
            pit=pit,
        )
        edges = await get_storage().hyperedges.find_for_transitive(tsf)

        next_frontier: List[str] = []
        for edge in edges:
            pairs = atomic_pairs(edge.get("members", []), edge.get("flavor", "hub"))
            for a, b in pairs:
                src, dst = (a, b) if direction == "forward" else (b, a)
                if src in visited and dst not in visited:
                    visited.add(dst)
                    reached[dst] = (edge.get("id") or edge.get("hyperkey"), src)
                    next_frontier.append(dst)
        frontier = next_frontier

    return reached


def _member_ids(edge: Dict[str, Any]) -> List[str]:
    return [m["node_id"] if isinstance(m, dict) else m.node_id for m in edge.get("members", [])]


def _other_member(axiom_edge: Dict[str, Any], relation_id: str) -> Optional[str]:
    """The other endpoint of a binary axiom edge, given one of its two
    members — used for order-irrelevant axioms like owl:inverse-of, where a
    single stored edge answers the lookup from either side.

    Returns None (rather than an arbitrary member) unless `relation_id` is
    actually one of this edge's members — a caller passing an id this edge
    doesn't even mention is a bug to surface, not a query to guess at."""
    ids = _member_ids(axiom_edge)
    if relation_id not in ids:
        return None
    others = [i for i in ids if i != relation_id]
    return others[0] if others else None


def _make_inferred_edge(
    relation: str,
    members: List[Dict[str, Any]],
    flavor: str,
    source_edge: Optional[str],
    axiom: Optional[str],
) -> Dict[str, Any]:
    """An ephemeral, never-persisted synthesized fact. No hyperkey, no
    mutations history — this is a read-time computation result, not a
    document; see the module docstring."""
    return {
        "relation": relation,
        "flavor": flavor,
        "members": members,
        "_inferred": True,
        "_source_edge": source_edge,
        "_axiom": axiom,
    }


def _atomic_facts(edge: Dict[str, Any]) -> Set[Tuple[str, str, str]]:
    """Every individual (relation, subject, object) fact this edge asserts.

    This — not the edge's own member list — is the real unit of "sameness"
    for closure dedup: the same underlying fact can arrive bundled two
    different ways (one 4-member hub edge vs. three separate 2-member
    edges asserting the same three pairs), and comparing whole edges misses
    that. Concretely, without this: projecting a rel:father fact up to
    rel:parent (whole-edge, unbundled) and then applying `owl:inverse-of`
    to derive rel:child facts, and then applying `owl:inverse-of` *again*
    to those (a legitimate step — inverse-of is symmetric) regenerates the
    same rel:parent facts one atomic pair at a time, which a whole-edge key
    would treat as "new" purely because the member list is shorter than
    the original. Comparing atomic fact sets recognizes it as already
    known and stops the closure from re-deriving already-known facts under
    a different bundling shape."""
    relation = edge.get("relation")
    flavor = edge.get("flavor", "hub")
    return {(relation, s, o) for s, o in atomic_pairs(edge.get("members", []), flavor)}


async def expand_edge(
    edge: Dict[str, Any],
    graph_ids: List[str],
    pit: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Single-pass axiom-driven expansion of one edge.

    Applies all three synthesis rules this reasoning engine supports, none
    of which are specific to any domain relation — every one is triggered
    only by an axiom hyperedge actually present in the graph:

    - `owl:inverse-of [R, R']`: for each (s, o) in atomic_pairs(edge),
      synthesize a 2-member hub edge — relation R', members [o, s].
    - `owl:symmetric`: for each (s, o) in atomic_pairs(edge), also
      synthesize (o, s) on the same relation.
    - `skos:narrowerTransitive`/`broaderTransitive` (superproperty
      projection): if this edge's relation is narrower than one or more
      broader relations (found via `walk_closure` over the axiom graph, so
      a multi-hop relation hierarchy projects through every level), copy
      this edge's members/flavor unchanged onto each broader relation.

    Returns synthesized edges only (not deduped against anything outside
    this single call — see `expand_edge_closure` for the fixed-point
    closure that dedupes and iterates to a stable result).
    """
    relation = edge.get("relation")
    members = edge.get("members", [])
    flavor = edge.get("flavor", "hub")
    source_id = edge.get("id") or edge.get("hyperkey")
    synthesized: List[Dict[str, Any]] = []

    for axiom_edge in await get_axiom_edges(relation, "owl:inverse-of", graph_ids, pit=pit):
        inverse_relation = _other_member(axiom_edge, relation)
        if not inverse_relation:
            continue
        for s, o in atomic_pairs(members, flavor):
            synthesized.append(_make_inferred_edge(
                relation=inverse_relation,
                members=[{"node_id": o, "seq": 0}, {"node_id": s, "seq": 1}],
                flavor="hub",
                source_edge=source_id,
                axiom=axiom_edge.get("id"),
            ))

    symmetric_axioms = await get_axiom_edges(relation, "owl:symmetric", graph_ids, pit=pit)
    if symmetric_axioms:
        axiom_edge = symmetric_axioms[0]
        for s, o in atomic_pairs(members, flavor):
            synthesized.append(_make_inferred_edge(
                relation=relation,
                members=[{"node_id": o, "seq": 0}, {"node_id": s, "seq": 1}],
                flavor="hub",
                source_edge=source_id,
                axiom=axiom_edge.get("id"),
            ))

    broader_chain = await walk_closure(
        relation, "skos:narrowerTransitive", graph_ids, direction="backward", pit=pit
    )
    for broader_relation, (axiom_edge_id, _predecessor) in broader_chain.items():
        synthesized.append(_make_inferred_edge(
            relation=broader_relation,
            members=members,
            flavor=flavor,
            source_edge=source_id,
            axiom=axiom_edge_id,
        ))

    return synthesized


async def expand_edge_closure(
    fact_edges: List[Dict[str, Any]],
    graph_ids: List[str],
    pit: Optional[datetime] = None,
    max_iterations: int = 10,
) -> List[Dict[str, Any]]:
    """Fixed-point closure of `expand_edge` over a starting set of fact edges.

    A single pass of `expand_edge` isn't enough — e.g. projecting a fact up
    to a broader relation only becomes eligible for `owl:inverse-of`
    expansion once that projection exists. This repeatedly expands the
    frontier (starting with `fact_edges`, then whatever was newly
    synthesized last round) until a round produces nothing new.

    A candidate is skipped once every individual atomic fact it asserts is
    already known — from an original fact edge, or from anything already
    synthesized — regardless of how that fact happens to be bundled into
    an edge's member list (see `_atomic_facts`). This dedup is also what
    breaks any cycle in the underlying axioms: a candidate that would only
    recreate already-known facts simply stops that branch of the frontier
    from growing. Bounded by `max_iterations` as a belt-and-suspenders
    safety valve underneath that.

    Returns only the newly-synthesized (`_inferred: true`) edges, not the
    original `fact_edges`.
    """
    known_facts: Set[Tuple[str, str, str]] = set()
    for e in fact_edges:
        known_facts |= _atomic_facts(e)

    all_inferred: List[Dict[str, Any]] = []
    frontier = fact_edges

    for _ in range(max_iterations):
        new_edges: List[Dict[str, Any]] = []
        for edge in frontier:
            for candidate in await expand_edge(edge, graph_ids, pit=pit):
                candidate_facts = _atomic_facts(candidate)
                if not candidate_facts <= known_facts:  # at least one genuinely new fact
                    known_facts |= candidate_facts
                    new_edges.append(candidate)
        if not new_edges:
            break
        all_inferred.extend(new_edges)
        frontier = new_edges

    return all_inferred


async def check_transitive(
    relation: str,
    graph_ids: List[str],
    start_id: str,
    end_id: Optional[str] = None,
    mode: str = "bool",
    max_depth: int = 10,
    pit: Optional[datetime] = None,
) -> Union[bool, List[str]]:
    """Transitive-closure reachability over *fact* edges of `relation`.

    Rebuilt on `walk_closure` — the same generic primitive `expand_edge`'s
    superproperty projection uses on *axiom* edges, applied here to
    ordinary facts (e.g. "contains" edges) instead. Self-verifies `relation`
    actually carries an `owl:transitive` axiom before walking anything —
    matching `expand_edge`'s own pattern of checking axioms itself rather
    than trusting the caller to have already checked — so calling this on a
    relation nobody declared transitive always safely reports "not
    reachable" instead of treating an incidental match as if it chains.

    `mode="bool"` (default): is `end_id` reachable from `start_id`? Returns
    a bool. Requires `end_id`.

    `mode="closure"`: every node id transitively reachable from `start_id`
    — the "give me every descendant" shape. `end_id` is ignored.

    `mode="path"`: the ordered chain of *hyperedge ids* connecting
    `start_id` to `end_id` (empty list if unreachable) — hyperedge ids, not
    node ids, so each hop can be hydrated/inspected the same way as any
    other edge, consistent with hyperedges being first-class. Requires
    `end_id`.
    """
    if mode not in ("bool", "closure", "path"):
        raise ValueError(f"check_transitive: mode must be 'bool', 'closure', or 'path', got {mode!r}")
    if mode in ("bool", "path") and end_id is None:
        raise ValueError(f"check_transitive: mode={mode!r} requires end_id")

    if not await get_axiom_edges(relation, "owl:transitive", graph_ids, pit=pit):
        return False if mode == "bool" else []

    reached = await walk_closure(start_id, relation, graph_ids, direction="forward", max_depth=max_depth, pit=pit)

    if mode == "closure":
        return sorted(reached.keys())

    if mode == "bool":
        return end_id in reached

    # mode == "path": follow predecessors backward from end_id to start_id
    if end_id not in reached:
        return []
    path_edges: List[str] = []
    node = end_id
    while node != start_id:
        edge_id, predecessor = reached[node]
        path_edges.append(edge_id)
        node = predecessor
    path_edges.reverse()
    return path_edges


# ─── Materialization ──────────────────────────────────────────────────────────
# Everything above this line is computed live, at read time, and never
# persisted. `project_inference` is the one deliberate exception — an
# explicit, user-triggered operation that writes inference results into a
# target hypergraph as ordinary, ongoing facts. It introduces no new
# reasoning logic: it's a persistence wrapper around expand_edge_closure and
# walk_closure, writing through the normal create_hyperedge() path so
# hyperkey dedup and the mutations audit trail apply exactly as they would
# to any hand-asserted fact.

async def project_inference(
    source_graph_ids: List[str],
    target_graph_id: str,
    mode: str,
    relation: Optional[str] = None,
    pit: Optional[datetime] = None,
    projected_by: str = "system",
    target_space_id: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Materialize inference results from source graph(s) into a target graph.

    `mode="expand"`: run `expand_edge_closure` over source fact edges
    (optionally filtered to `relation`), materialize every synthesized edge.

    `mode="transitive"` (requires `relation`): for every node that's a
    subject in some fact edge of `relation`, materialize every node
    transitively reachable from it via that relation — skipping 1-hop
    results, since those are already literal facts with nothing to
    materialize. Self-gated on an `owl:transitive` axiom, same as
    `check_transitive`.

    `mode="both"`: both of the above.

    Safe to re-run: every candidate is checked against
    `engine.find_duplicate_hyperedge` before writing, so an unchanged
    source produces zero new edges on a repeat run, and a source that
    gained new facts only adds the delta — never a duplicate.

    Each materialized edge's `attributes.provenance` records where it came
    from (`source_graphs`, `source_edge`, `axiom`, `pit`, `projected_by`,
    `projected_at`), so a materialized fact stays traceable to what
    produced it even though it's now an ordinary, independent stored edge —
    indistinguishable at the storage/query level from anything
    hand-asserted, and, notably, NOT kept in sync if the source changes
    later. This is a snapshot, not a live view.

    `dry_run=True` computes and returns exactly what would happen —
    including which candidates already exist (`skipped`) and which are new
    (`created`) — without writing anything at all, not even a new target
    hypergraph document. Intended for a UI (or any caller) to preview a
    projection before committing to it.

    Returns `{created, skipped, errors, error_details, edges, preview,
    dry_run}`. `edges` is the list of actually-created edge ids (empty when
    `dry_run`). `preview` is every candidate considered, each tagged with
    `status` ("new", "skip", or "error") plus its relation/members/
    provenance-relevant fields and, once written, its real edge id — this
    is populated identically whether `dry_run` is set or not, so the same
    rendering code can show a preview or a completed result.
    """
    from hgai.core.engine import create_hyperedge, find_duplicate_hyperedge
    from hgai.models.hyperedge import HyperedgeCreate
    from hgai_module_storage.filters import HyperedgeSearchFilters
    from hgai.models.common import now_utc

    if mode not in ("expand", "transitive", "both"):
        raise ValueError(f"project_inference: mode must be 'expand', 'transitive', or 'both', got {mode!r}")
    if mode in ("transitive", "both") and not relation:
        raise ValueError(f"project_inference: mode={mode!r} requires relation")

    candidates: List[Dict[str, Any]] = []

    if mode in ("expand", "both"):
        filters = HyperedgeSearchFilters(hypergraph_ids=source_graph_ids, relation=relation, pit=pit)
        fact_edges = await get_storage().hyperedges.search(filters, skip=0, limit=5000)
        candidates.extend(await expand_edge_closure(fact_edges, source_graph_ids, pit=pit))

    if mode in ("transitive", "both"):
        if await get_axiom_edges(relation, "owl:transitive", source_graph_ids, pit=pit):
            filters = HyperedgeSearchFilters(hypergraph_ids=source_graph_ids, relation=relation, pit=pit)
            fact_edges = await get_storage().hyperedges.search(filters, skip=0, limit=5000)
            subjects = {
                s for e in fact_edges
                for s, _o in atomic_pairs(e.get("members", []), e.get("flavor", "hub"))
            }
            for start_id in subjects:
                reached = await walk_closure(start_id, relation, source_graph_ids, direction="forward", pit=pit)
                for node_id, (edge_id, predecessor) in reached.items():
                    if predecessor == start_id:
                        continue  # 1-hop — already a literal edge
                    candidates.append(_make_inferred_edge(
                        relation=relation,
                        members=[{"node_id": start_id, "seq": 0}, {"node_id": node_id, "seq": 1}],
                        flavor="hub",
                        source_edge=None,
                        axiom=edge_id,
                    ))

    created, skipped, errors = 0, 0, 0
    created_edge_ids: List[str] = []
    error_details: List[str] = []
    preview: List[Dict[str, Any]] = []

    for candidate in candidates:
        member_ids = _member_ids(candidate)
        entry: Dict[str, Any] = {
            "relation": candidate["relation"],
            "flavor": candidate.get("flavor", "hub"),
            "members": candidate["members"],
            "source_edge": candidate.get("_source_edge"),
            "axiom": candidate.get("_axiom"),
        }

        dup = await find_duplicate_hyperedge(
            target_graph_id, candidate["relation"], member_ids, space_id=target_space_id,
        )
        if dup:
            skipped += 1
            entry["status"] = "skip"
            entry["existing_edge_id"] = dup.id
            preview.append(entry)
            continue

        if dry_run:
            created += 1
            entry["status"] = "new"
            preview.append(entry)
            continue

        provenance = {
            "source_graphs": source_graph_ids,
            "source_edge": candidate.get("_source_edge"),
            "axiom": candidate.get("_axiom"),
            "pit": pit.isoformat() if pit else None,
            "projected_by": projected_by,
            "projected_at": now_utc().isoformat(),
        }
        try:
            data = HyperedgeCreate(
                relation=candidate["relation"],
                flavor=candidate.get("flavor", "hub"),
                members=candidate["members"],
                attributes={"provenance": provenance},
            )
            edge = await create_hyperedge(target_graph_id, data, created_by=projected_by, space_id=target_space_id)
            created += 1
            created_edge_ids.append(edge.id)
            entry["status"] = "new"
            entry["created_edge_id"] = edge.id
        except Exception as e:
            errors += 1
            error_details.append(str(e))
            entry["status"] = "error"
            entry["error"] = str(e)
        preview.append(entry)

    return {
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "error_details": error_details,
        "edges": created_edge_ids,
        "preview": preview,
        "dry_run": dry_run,
    }
