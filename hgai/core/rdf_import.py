"""RDF import: Turtle (.ttl), RDF/XML (.rdf, .xml), JSON-LD (.jsonld) and
Notation3 (.n3) files, mapped into a hypergraph.

The mapping (deliberately simple — RDF has no native n-ary relationships,
so every triple becomes one two-member hyperedge, not a fused hyperedge):

  * Every subject, and every object that is an IRI or a blank node (never a
    literal), becomes a **hypernode**. A prefix is always expanded to its
    full absolute IRI for the id — never left as a compact `prefix:local`
    CURIE (`ex:adam` with `@prefix ex: <http://example.com/>` becomes id
    `http://example.com/adam`) — because the id is a plain *value*, not a
    document key, so the dots an IRI routinely contains are harmless there.
    A blank node's id is `bnode:<rdflib's blank node label>` (it has no IRI
    to expand).
  * `rdf:type` triples set the hypernode's `type` (the first type's local
    name, sorted for determinism when there is more than one — a short,
    display-friendly category, deliberately not expanded) and are also kept
    in full, as expanded IRIs, in `attributes.rdf_type`.
  * A label is taken from the first of `rdfs:label`, `skos:prefLabel`,
    `foaf:name`, `dc:title`, `dcterms:title` found on the subject, else the
    IRI's own local name (never the full IRI — a label is for display).
  * Every other **literal**-valued predicate becomes a hypernode attribute.
    Unlike every identifier above, the attribute *key* is kept as a
    sanitized `prefix:local` CURIE, not expanded to the full predicate IRI:
    attribute keys become literal MongoDB subdocument field names, and
    SHQL's `attributes: {key: value}` pattern filter builds a MongoDB
    dot-path query from that key (`hgai_module_storage_mongodb/stores/
    hypernodes.py`, `f"attributes.{k}"`) — a key containing '.' would make
    that filter address the wrong (nonexistent, nested) path and silently
    stop matching. This is the one deliberate exception to "expand every
    prefix." The attribute *value* is classified by the literal's own
    lexical form, not its RDF/XSD datatype: a value whose lexical string
    starts with an ASCII digit is always stored as a number (int if it
    parses as one, else float; -1 if neither parse succeeds) — even a
    literal RDF typed as a string, e.g. `"12345"` with no datatype at all,
    still becomes numeric. Everything else is stored as text. Booleans and
    dates/timestamps (`xsd:boolean`, `xsd:date`, `xsd:dateTime`) are the
    exception to the digit rule: a boolean stays a native bool, a
    `dateTime` converts to a native Python `datetime.datetime`, and a bare
    `date` falls back to its lexical string (BSON can't store a
    `datetime.date`). Multiple values for the same predicate become a list.
  * Every **IRI/blank-node**-valued predicate becomes a `hub` hyperedge:
    relation = the predicate's full expanded IRI, members = [subject, object]
    — with two OWL vocabulary exceptions, recognized by the real, canonical
    OWL IRI (regardless of what prefix a file locally binds to it) and
    mapped onto HypergraphAI's own axiom relations (hgai/core/inference.py),
    so an ontology's own transitivity/inverse declarations are usable by
    `infer: true` immediately on import, the same as one hand-asserted in a
    seed file (see scripts/seeds/hgai-hypergraph-eden.export.yml):
      - `<P> a owl:TransitiveProperty` — instead of (only) folding into
        `<P>`'s `type`/`attributes.rdf_type` like any other rdf:type triple
        — ALSO synthesizes a `hub` hyperedge: relation `owl:transitive`,
        a single member (seq 0) `<P>`.
      - `<P> owl:inverseOf <Q>` — a `hub` hyperedge: relation
        `owl:inverse-of` (HypergraphAI's own spelling — note the hyphen,
        never the real predicate's own CURIE `owl:inverseOf`), members
        `[<P> (seq 0), <Q> (seq 1)]` — the same shape any other
        resource-valued triple gets, only the relation string differs.
      - `<P> a owl:SymmetricProperty` — both of the following, together:
        every *data* triple already using `<P>` as its predicate (anywhere
        in the file, subject or object of the property declaration itself
        aside) gets flavor `symmetric` instead of `hub` — relation stays
        `<P>`'s own full expanded IRI, members stay `[subject (seq 0),
        object (seq 1)]` — a direct, `infer`-free translation, since a
        `symmetric` hyperedge already reads both directions unconditionally
        (`atomic_pairs` in hgai/core/inference.py); AND, exactly like
        `owl:TransitiveProperty` above, a single-member `hub` axiom edge:
        relation `owl:symmetric`, a single member (seq 0) `<P>` — a safety
        net for `infer: true` if `<P>` is ever also asserted through a
        `hub`-flavored edge this import never sees (e.g. one added by hand
        later).

Not handled (documented limitations, not silent data loss — everything not
listed above still round-trips as ordinary triples/attributes):
  * RDF Collections (`rdf:first`/`rdf:rest`/`rdf:nil` list structures) are
    imported as plain triples on their blank-node cells, not flattened into
    a native list attribute or an n-ary hyperedge.
  * JSON-LD named graphs (`@graph` blocks with multiple graphs) are merged
    into one triple set — the graph name is dropped. HypergraphAI hyperedges
    aren't a general quad store; use one import per named graph if you need
    them kept apart.
  * RDF reification (`rdf:Statement`/`rdf:subject`/... quadruples describing
    a triple) round-trips as ordinary triples on the reification node, not
    as edge-level provenance.
"""

from __future__ import annotations

import datetime
import os
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    import rdflib
    from rdflib import BNode, Literal, URIRef
    from rdflib.namespace import DC, DCTERMS, FOAF, OWL, RDF, RDFS, SKOS
except ImportError:  # pragma: no cover — rdflib is a hard dependency (requirements.txt); this
    rdflib = None    # guard only helps a misconfigured/partial install fail with a clear message.


class RdfFormatError(ValueError):
    """The uploaded text isn't parseable RDF, or the requested format is unknown."""


# ─── Format resolution ─────────────────────────────────────────────────────────

# Public aliases -> the rdflib parser plugin name. Keeping this mapping (rather
# than accepting rdflib's own names directly) is what lets the API/UI use the
# same short words as the file extensions named in the request ("rdf", "xml"
# both mean RDF/XML) without leaking rdflib's own vocabulary ("xml", "json-ld")
# into the public contract.
_FORMAT_ALIASES: Dict[str, str] = {
    "ttl": "turtle", "turtle": "turtle",
    "n3": "n3", "notation3": "n3",
    "rdf": "xml", "xml": "xml", "rdfxml": "xml", "rdf-xml": "xml", "rdf/xml": "xml",
    "jsonld": "json-ld", "json-ld": "json-ld",
}
_EXTENSION_FORMATS: Dict[str, str] = {
    ".ttl": "turtle", ".n3": "n3", ".rdf": "xml", ".xml": "xml", ".jsonld": "json-ld",
}
SUPPORTED_FORMATS = sorted(set(_FORMAT_ALIASES))


def resolve_format(fmt: Optional[str], filename: Optional[str] = None) -> str:
    """An explicit `fmt` wins; otherwise inferred from `filename`'s extension.

    Returns the rdflib parser plugin name ('turtle', 'n3', 'xml', 'json-ld').
    """
    if fmt and fmt.strip():
        key = fmt.strip().lower()
        if key not in _FORMAT_ALIASES:
            raise RdfFormatError(
                f"Unknown RDF format '{fmt}' — use one of: {', '.join(SUPPORTED_FORMATS)}"
            )
        return _FORMAT_ALIASES[key]
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext in _EXTENSION_FORMATS:
            return _EXTENSION_FORMATS[ext]
        raise RdfFormatError(
            f"Can't infer the RDF format from '{filename}' — pass format= explicitly "
            f"({', '.join(SUPPORTED_FORMATS)})"
        )
    raise RdfFormatError("RDF import needs a format (ttl, n3, rdf/xml, json-ld) or a filename to infer it from")


# ─── Id / key sanitizing ────────────────────────────────────────────────────────

# '.' is deliberately excluded: it's the delimiter for cross-graph member
# references (EdgeMember.node_id, "other-graph.local-id") and is rejected by
# MongoDB in a subdocument key (attribute names). Everything else disallowed
# collapses to '_' rather than being dropped, so two different unsafe
# characters never accidentally merge into the same id.
_UNSAFE = re.compile(r"[^A-Za-z0-9:_-]+")


def _sanitize(s: str) -> str:
    s = _UNSAFE.sub("_", s.strip())
    return s or "_"


_LABEL_PREDICATES = [RDFS.label, SKOS.prefLabel, FOAF.name, DC.title, DCTERMS.title]

# OWL vocabulary -> HypergraphAI's own axiom control-vocabulary strings (see
# hgai/core/inference.py's module docstring: "owl:transitive", "owl:inverse-of",
# ... are recognized by exact string match, never derived from a source file's
# own prefix bindings). Detected by the real, canonical OWL IRI — regardless
# of what local prefix a given file happens to bind to the OWL namespace — so
# these are the only two relation *values* in this whole module that are
# never the predicate's expanded IRI or a CURIE, but a fixed HypergraphAI
# spelling a source file could never itself produce (rdflib's own compact
# form for the real predicate would be "owl:inverseOf", not "owl:inverse-of").
_AXIOM_RELATION_OVERRIDES = {OWL.inverseOf: "owl:inverse-of"}

# Text-vs-numeric attribute-value classification, driven by the literal's
# own LEXICAL form (its first character) rather than its RDF/XSD datatype —
# a lexical value starting with an ASCII digit is always parsed as a number
# (int if it parses as one, else float; -1 if neither parse succeeds), even
# when RDF typed it as a plain string (e.g. `"12345"` with no datatype, a
# zip code written as a quoted string, still becomes numeric). Anything else
# — a letter, punctuation, the contents of a quoted string — is text. This
# is why `ex:Eve ex:rating 12.2` (Turtle's default xsd:decimal, whose
# .toPython() gives a non-BSON-safe decimal.Decimal) still becomes a native
# float 12.2: the lexical string "12.2" is parsed directly, sidestepping
# toPython() for the digit-led case entirely.
#
# Two RDF/XSD types are exempt from the digit-led rule even though their
# lexical form usually starts with a digit, because "parse it as a number"
# would destroy them rather than convert them: booleans (RDF's "true"/
# "false" don't start with a digit anyway, but are matched first for
# clarity) and dates/timestamps (xsd:date, xsd:dateTime) — those keep their
# pre-existing handling: a dateTime converts to a native datetime.datetime,
# a bare date (BSON can't store datetime.date) falls back to its lexical
# string, same as before this change.
def _literal_value(lit: "Literal") -> Any:
    try:
        v = lit.toPython()
    except Exception:
        v = None

    if isinstance(v, bool):
        return v
    if isinstance(v, datetime.date):
        return v if type(v) is datetime.datetime else str(lit)

    s = str(lit)
    if s[:1].isdigit():
        try:
            return int(s)
        except ValueError:
            pass
        try:
            return float(s)
        except ValueError:
            return -1

    # Not digit-led: an already-native (RDF-typed) int/float — e.g. a
    # negative number, whose lexical form starts with '-' — still passes
    # through as-is rather than falling to text.
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        # An invalid lexical value (e.g. "abc"^^xsd:integer) makes toPython()
        # return the Literal itself unconverted rather than raising — and
        # Literal is itself a str subclass, so it passes this isinstance
        # check without str(v) normalizing it away. Without this, an rdflib
        # Literal object (not a plain str) would leak into `attributes` and
        # fail comparisons/serialization downstream.
        return str(v)
    return str(lit)


class _IdMinter:
    """Assigns each RDF term (IRI or blank node) a stable hypernode id: a URIRef's
    id is its full, expanded IRI (an ordinary string value, not a document key —
    see the module docstring for why that's fine even though an IRI routinely
    contains '.'); a BNode's id is `bnode:<label>` (it has no IRI to expand).

    Both are already unique by construction (two different URIRef terms always
    have different string forms; rdflib's own blank-node labels are unique
    within one parse), so the collision-suffix loop below is unreachable in
    practice — kept only as a defensive "never silently merge two different
    terms" safety net, matching this codebase's existing style elsewhere for
    identifier minting.
    """

    def __init__(self, graph: "rdflib.Graph"):
        self._graph = graph
        self._ids: Dict[Any, str] = {}
        self._used: set = set()

    def id_for(self, term: Any) -> str:
        cached = self._ids.get(term)
        if cached is not None:
            return cached
        candidate = f"bnode:{_sanitize(str(term))}" if isinstance(term, BNode) else str(term)
        base, n = candidate, 2
        while candidate in self._used:
            candidate = f"{base}-{n}"
            n += 1
        self._used.add(candidate)
        self._ids[term] = candidate
        return candidate


def _qname(graph: "rdflib.Graph", term: URIRef) -> str:
    """A sanitized `prefix:local` CURIE — used ONLY for literal-attribute keys
    (see the module docstring for why those, alone, stay compacted rather
    than expanded to the full IRI)."""
    prefix, _ns, local = graph.compute_qname(str(term), generate=True)
    return _sanitize(f"{prefix}:{local}" if prefix else local)


def _local_name(graph: "rdflib.Graph", term: URIRef) -> str:
    """Just the local part of a term's CURIE (no prefix) — for a short,
    display-friendly fallback label or `type` value, never an identifier."""
    _prefix, _ns, local = graph.compute_qname(str(term), generate=True)
    return local


def _pick_label(graph: "rdflib.Graph", subject: Any, literals_by_pred: Dict[Any, List["Literal"]]) -> Optional[str]:
    for pred in _LABEL_PREDICATES:
        values = literals_by_pred.get(pred)
        if not values:
            continue
        # Prefer a language-less literal, else English, else the first (sorted for determinism).
        ranked = sorted(values, key=lambda lit: (0 if not lit.language else (0 if lit.language.startswith("en") else 1), str(lit)))
        return str(ranked[0])
    return None


def rdf_to_export_document(
    text: str, fmt: str, graph_id: str, label: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse `text` (already resolved to an rdflib format name — see
    resolve_format) and return an in-memory document in the same shape
    `hgai.core.transfer.import_document` already knows how to load
    (`{"hgai_export": "1.0", "graph": ..., "nodes": [...], "edges": [...]}`),
    so RDF import gets the exact same create/merge, permission-check,
    per-item error handling and dedup behavior as a native export file —
    just with a different source format upstream of it.
    """
    if rdflib is None:
        raise RdfFormatError("RDF import requires the 'rdflib' package, which is not installed on this server")

    graph = rdflib.Graph()
    try:
        graph.parse(data=text, format=fmt)
    except RdfFormatError:
        raise
    except Exception as e:
        detail = str(e).strip().splitlines()[0] if str(e).strip() else e.__class__.__name__
        raise RdfFormatError(f"Could not parse as {fmt}: {detail}")

    ids = _IdMinter(graph)

    # Every subject, and every IRI/blank-node object of a non-rdf:type triple
    # (never a literal), needs a hypernode — including "object only" resources
    # that are never themselves a subject, so every hyperedge member below
    # resolves to a real node. An rdf:type OBJECT (a class) is deliberately
    # excluded here: type is folded into the subject's own `type`/`rdf_type`
    # fields (see below), not turned into an edge, so a class referenced by
    # nothing but rdf:type triples would otherwise become a disconnected,
    # edge-less node for every distinct type in the file. A class that IS
    # also used as an ordinary subject or object elsewhere (e.g. it has its
    # own rdfs:label or rdfs:subClassOf) still gets a node from that use.
    # Every predicate declared `<P> a owl:SymmetricProperty` anywhere in the
    # graph — found in this same pass, since it's a property of the PREDICATE
    # of a later, unrelated triple (e.g. ex:cain ex:sibling ex:abel), not of
    # the entity whose own triples are grouped in the per-entity loop below.
    entities: List[Any] = []
    seen_entities: set = set()
    symmetric_properties: set = set()
    for s, p, o in graph:
        if p == RDF.type and o == OWL.SymmetricProperty:
            symmetric_properties.add(s)
        terms = (s,) if p == RDF.type else (s, o)
        for term in terms:
            if isinstance(term, (URIRef, BNode)) and term not in seen_entities:
                seen_entities.add(term)
                entities.append(term)

    nodes: List[Dict[str, Any]] = []
    # (relation, flavor, ordered member ids, sort_key) — member ids become
    # seq 0, 1, ... in order; almost always 2 (subject, object), except a
    # synthesized owl:transitive axiom edge below, which is 1 (the property
    # alone).
    edge_tuples: List[Tuple[str, str, Tuple[str, ...], str]] = []

    for entity in entities:
        # Group this entity's own outgoing triples by predicate, split into
        # rdf:type / literal-valued / resource-valued — a single pass over
        # the (small, per-entity) triple set rather than three graph scans.
        types: List[URIRef] = []
        literals_by_pred: Dict[Any, List[Literal]] = {}
        resources_by_pred: Dict[Any, List[Any]] = {}
        for _s, p, o in graph.triples((entity, None, None)):
            if p == RDF.type and isinstance(o, URIRef):
                types.append(o)
            elif isinstance(o, Literal):
                literals_by_pred.setdefault(p, []).append(o)
            elif isinstance(o, (URIRef, BNode)):
                resources_by_pred.setdefault(p, []).append(o)

        node_id = ids.id_for(entity)  # the full expanded IRI for a URIRef, bnode:<label> for a blank node
        attributes: Dict[str, Any] = {}

        entity_type = "Entity"
        if types:
            type_names = sorted({_local_name(graph, t) for t in types})
            entity_type = type_names[0]
            attributes["rdf_type"] = sorted(str(t) for t in types)

        label_value = _pick_label(graph, entity, literals_by_pred)
        if not label_value:
            label_value = _local_name(graph, entity) if isinstance(entity, URIRef) else node_id

        for pred, values in literals_by_pred.items():
            key = _qname(graph, pred)
            converted = sorted((_literal_value(v) for v in values), key=str)
            attributes[key] = converted[0] if len(converted) == 1 else converted

        nodes.append({
            "id": node_id, "label": label_value, "type": entity_type, "attributes": attributes,
        })

        for pred, objs in resources_by_pred.items():
            # The predicate's full expanded IRI — except owl:inverseOf, whose
            # relation is always the fixed "owl:inverse-of" axiom string
            # (see _AXIOM_RELATION_OVERRIDES).
            relation = _AXIOM_RELATION_OVERRIDES.get(pred, str(pred))
            # A property declared owl:SymmetricProperty gets its data edges
            # (not just an axiom edge) flavored "symmetric" directly — unlike
            # owl:transitive/owl:inverse-of, whose axiom edges are what teach
            # `infer: true` to derive the missing direction on read, a
            # `symmetric`-flavored edge already reads both directions
            # unconditionally (atomic_pairs), which is the more direct,
            # infer-free translation of what owl:SymmetricProperty asserts.
            flavor = "symmetric" if pred in symmetric_properties else "hub"
            for obj in objs:
                obj_id = ids.id_for(obj)
                edge_tuples.append((relation, flavor, (node_id, obj_id), f"{relation}\0{flavor}\0{node_id}\0{obj_id}"))

        # owl:TransitiveProperty -> a single-member "owl:transitive" axiom
        # edge naming this property, so hgai/core/inference.py's `infer: true`
        # recognizes it exactly as it would one hand-asserted in a seed file
        # (see scripts/seeds/hgai-hypergraph-eden.export.yml's edge:child-trans).
        if OWL.TransitiveProperty in types:
            edge_tuples.append(("owl:transitive", "hub", (node_id,), f"owl:transitive\0{node_id}"))

        # owl:SymmetricProperty -> ALSO a single-member "owl:symmetric" axiom
        # edge naming this property, exactly mirroring owl:transitive above —
        # in addition to (not instead of) every data edge on this property
        # already being flavor "symmetric" (see the flavor= line above). The
        # axiom edge lets `infer: true` recognize the property as symmetric
        # even where it's asserted through *other* hyperedges this import
        # never sees (e.g. a `hub`-flavored edge added later by hand), the
        # same safety net owl:transitive's axiom edge already provides.
        if OWL.SymmetricProperty in types:
            edge_tuples.append(("owl:symmetric", "hub", (node_id,), f"owl:symmetric\0{node_id}"))

    nodes.sort(key=lambda n: n["id"])
    edge_tuples.sort(key=lambda t: t[3])
    edges = [
        {
            "relation": relation, "flavor": flavor,
            "members": [{"node_id": mid, "seq": i} for i, mid in enumerate(member_ids)],
        }
        for relation, flavor, member_ids, _key in edge_tuples
    ]

    graph_label = label or graph_id
    return {
        "hgai_export": "1.0",
        "graph": {
            "id": graph_id,
            "label": graph_label,
            "type": "instantiated",
            "tags": ["rdf-import"],
            "attributes": {"rdf_source_format": fmt, "rdf_triple_count": len(graph)},
        },
        "nodes": nodes,
        "edges": edges,
    }
