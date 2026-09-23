"""Tests for hgai.core.rdf_import: format resolution and the RDF -> hypergraph mapping.

rdf_to_export_document() is pure (no storage access) — it returns a plain dict in
the same shape hgai.core.transfer already knows how to load, so these tests verify
that shape and content directly rather than through the storage-backed import
pipeline (transfer.import_document is exercised by tests/test_transfer.py already,
and reused unchanged here — see the docstring in rdf_import.py).

Identifiers (hypernode/hyperedge ids, relation, rdf_type values) are the RDF
term's full, expanded IRI — never a compact prefix:local CURIE. The one
deliberate exception is literal-attribute *keys*, which stay CURIE-compacted
(see test_attribute_keys_stay_curie_compacted_not_expanded for why).
"""

import pytest

from hgai.core.rdf_import import (
    RdfFormatError,
    SUPPORTED_FORMATS,
    _IdMinter,
    resolve_format,
    rdf_to_export_document,
)


# ─── Format resolution ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("alias,expected", [
    ("ttl", "turtle"), ("turtle", "turtle"), ("TTL", "turtle"),
    ("n3", "n3"), ("notation3", "n3"),
    ("rdf", "xml"), ("xml", "xml"), ("rdfxml", "xml"), ("rdf-xml", "xml"), ("rdf/xml", "xml"),
    ("jsonld", "json-ld"), ("json-ld", "json-ld"),
])
def test_resolve_format_by_alias(alias, expected):
    assert resolve_format(alias) == expected


@pytest.mark.parametrize("filename,expected", [
    ("data.ttl", "turtle"), ("data.n3", "n3"), ("data.rdf", "xml"),
    ("data.xml", "xml"), ("data.jsonld", "json-ld"), ("DATA.TTL", "turtle"),
])
def test_resolve_format_by_extension(filename, expected):
    assert resolve_format(None, filename) == expected


def test_resolve_format_explicit_wins_over_filename():
    assert resolve_format("ttl", "data.jsonld") == "turtle"


def test_resolve_format_unknown_alias():
    with pytest.raises(RdfFormatError, match="Unknown RDF format"):
        resolve_format("bogus")


def test_resolve_format_unknown_extension():
    with pytest.raises(RdfFormatError, match="Can't infer"):
        resolve_format(None, "data.ttlx")


def test_resolve_format_nothing_given():
    with pytest.raises(RdfFormatError, match="needs a format"):
        resolve_format(None, None)


def test_supported_formats_are_all_resolvable():
    for alias in SUPPORTED_FORMATS:
        resolve_format(alias)  # must not raise


# ─── rdf_to_export_document: shape ──────────────────────────────────────────────

TTL_BASIC = """
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix ex: <http://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:alice a foaf:Person ;
    foaf:name "Alice" ;
    foaf:age "30"^^xsd:integer ;
    foaf:knows ex:bob, ex:carol .
ex:bob a foaf:Person ;
    foaf:name "Bob" .
"""

ALICE = "http://example.org/alice"
BOB = "http://example.org/bob"
CAROL = "http://example.org/carol"
KNOWS = "http://xmlns.com/foaf/0.1/knows"
PERSON = "http://xmlns.com/foaf/0.1/Person"


def _doc(text=TTL_BASIC, fmt="turtle", graph_id="test-graph", label=None):
    return rdf_to_export_document(text, fmt, graph_id, label=label)


def _node(doc, node_id):
    return next(n for n in doc["nodes"] if n["id"] == node_id)


def test_document_shape_is_a_valid_export_document():
    from hgai.core.transfer import validate_export
    doc = _doc()
    validated = validate_export(doc)  # must not raise
    assert validated["graph"]["id"] == "test-graph"


def test_graph_metadata():
    doc = _doc(graph_id="g1", label="My Graph")
    assert doc["hgai_export"] == "1.0"
    assert doc["graph"] == {
        "id": "g1", "label": "My Graph", "type": "instantiated", "tags": ["rdf-import"],
        "attributes": {"rdf_source_format": "turtle", "rdf_triple_count": 7},
    }


def test_graph_label_defaults_to_graph_id():
    doc = _doc(graph_id="g1", label=None)
    assert doc["graph"]["label"] == "g1"


# ─── Prefix expansion (the point of this feature) ───────────────────────────────

def test_prefixed_subject_expands_to_full_iri_example_com_slash():
    # The exact example from the request: ex:adam -> http://example.com/adam
    # with @prefix ex: <http://example.com/>.
    ttl = "@prefix ex: <http://example.com/> . ex:adam ex:p \"v\" ."
    doc = _doc(ttl, graph_id="g")
    ids = {n["id"] for n in doc["nodes"]}
    assert ids == {"http://example.com/adam"}


def test_prefixed_object_expands_to_full_iri_hash_namespace():
    # The exact example from the request: meh:eve -> http://meh.io#eve
    # with @prefix meh: <http://meh.io#>.
    ttl = "@prefix ex: <http://example.com/> . @prefix meh: <http://meh.io#> . ex:adam meh:knows meh:eve ."
    doc = _doc(ttl, graph_id="g")
    ids = {n["id"] for n in doc["nodes"]}
    assert ids == {"http://example.com/adam", "http://meh.io#eve"}


def test_no_curie_form_survives_in_ids_or_relation():
    doc = _doc()
    assert all(n["id"].startswith(("http://", "https://", "bnode:")) for n in doc["nodes"])
    assert all(e["relation"].startswith(("http://", "https://")) for e in doc["edges"])
    assert not any(n["id"].startswith(("ex:", "foaf:")) for n in doc["nodes"])
    assert not any(e["relation"].startswith(("ex:", "foaf:")) for e in doc["edges"])


def test_relation_is_the_predicates_full_iri_not_a_curie():
    doc = _doc()
    assert {e["relation"] for e in doc["edges"]} == {KNOWS}


def test_rdf_type_values_are_full_iris():
    doc = _doc()
    assert _node(doc, ALICE)["attributes"]["rdf_type"] == [PERSON]


def test_attribute_keys_stay_curie_compacted_not_expanded():
    # The one deliberate exception: an attribute key becomes a literal MongoDB
    # subdocument field name, and SHQL's `attributes: {key: value}` pattern
    # filter builds a MongoDB dot-path query from that key
    # (hgai_module_storage_mongodb/stores/hypernodes.py: f"attributes.{k}") —
    # a '.'-containing key would make that filter address the wrong path.
    doc = _doc()
    attrs = _node(doc, ALICE)["attributes"]
    assert "foaf:name" in attrs and "foaf:age" in attrs
    assert not any(k.startswith("http://") for k in attrs if k != "rdf_type")


def test_type_field_is_a_short_local_name_not_a_curie_or_iri():
    doc = _doc()
    assert _node(doc, ALICE)["type"] == "Person"


def test_label_fallback_is_local_name_not_a_curie_or_iri():
    ttl = '@prefix ex: <http://example.org/> . ex:someResource ex:p "v" .'
    doc = _doc(ttl, graph_id="g")
    assert _node(doc, "http://example.org/someResource")["label"] == "someResource"


# ─── Subjects, objects, literals ────────────────────────────────────────────────

def test_every_subject_becomes_a_node():
    doc = _doc()
    ids = {n["id"] for n in doc["nodes"]}
    assert {ALICE, BOB} <= ids


def test_object_only_resource_becomes_a_node_too():
    # carol is never a subject, only an object of foaf:knows.
    doc = _doc()
    ids = {n["id"] for n in doc["nodes"]}
    assert CAROL in ids
    carol = _node(doc, CAROL)
    assert carol["label"] == "carol"
    assert carol["type"] == "Entity"


def test_rdf_type_object_alone_does_not_become_a_node():
    # foaf:Person is referenced only via rdf:type — it must not appear as an
    # orphan, edge-less node (see the docstring in rdf_import.py).
    doc = _doc()
    ids = {n["id"] for n in doc["nodes"]}
    assert PERSON not in ids
    assert len(doc["nodes"]) == 3  # alice, bob, carol — not the Person class


def test_literal_object_becomes_an_attribute_not_a_node_or_edge():
    doc = _doc()
    alice = _node(doc, ALICE)
    assert alice["attributes"]["foaf:name"] == "Alice"
    assert alice["attributes"]["foaf:age"] == 30
    assert isinstance(alice["attributes"]["foaf:age"], int)
    # No node or edge was created for the literal itself.
    assert all(n["id"] not in ("Alice", "30") for n in doc["nodes"])
    assert not any("name" in e["relation"] or "age" in e["relation"] for e in doc["edges"])


def test_resource_object_becomes_a_hub_edge_subject_first_object_second():
    doc = _doc()
    knows_edges = [e for e in doc["edges"] if e["relation"] == KNOWS]
    assert len(knows_edges) == 2
    for e in knows_edges:
        assert e["flavor"] == "hub"
        assert [m["seq"] for m in e["members"]] == [0, 1]
        assert e["members"][0]["node_id"] == ALICE
    targets = {e["members"][1]["node_id"] for e in knows_edges}
    assert targets == {BOB, CAROL}


def test_multi_valued_literal_predicate_becomes_a_sorted_list():
    ttl = """
    @prefix ex: <http://example.org/> .
    ex:a ex:tag "z", "x", "y" .
    """
    doc = _doc(ttl, graph_id="g")
    assert _node(doc, "http://example.org/a")["attributes"]["ex:tag"] == ["x", "y", "z"]


def test_single_valued_literal_predicate_is_not_wrapped_in_a_list():
    doc = _doc()
    assert _node(doc, BOB)["attributes"]["foaf:name"] == "Bob"


# ─── rdf:type handling ──────────────────────────────────────────────────────────

def test_single_type_sets_node_type():
    doc = _doc()
    assert _node(doc, ALICE)["type"] == "Person"
    assert _node(doc, ALICE)["attributes"]["rdf_type"] == [PERSON]


def test_multiple_types_pick_first_sorted_and_keep_full_list():
    ttl = """
    @prefix ex: <http://example.org/> .
    ex:a a ex:Zebra, ex:Aardvark .
    """
    doc = _doc(ttl, graph_id="g")
    node = _node(doc, "http://example.org/a")
    assert node["type"] == "Aardvark"
    assert node["attributes"]["rdf_type"] == ["http://example.org/Aardvark", "http://example.org/Zebra"]


def test_no_type_defaults_to_entity():
    ttl = '@prefix ex: <http://example.org/> . ex:a ex:p "v" .'
    doc = _doc(ttl, graph_id="g")
    node = _node(doc, "http://example.org/a")
    assert node["type"] == "Entity"
    assert "rdf_type" not in node["attributes"]


# ─── Labels ──────────────────────────────────────────────────────────────────────

def test_label_prefers_rdfs_label_over_foaf_name():
    ttl = """
    @prefix ex: <http://example.org/> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix foaf: <http://xmlns.com/foaf/0.1/> .
    ex:a rdfs:label "Preferred Label" ; foaf:name "Other Name" .
    """
    doc = _doc(ttl, graph_id="g")
    assert _node(doc, "http://example.org/a")["label"] == "Preferred Label"


def test_label_falls_back_to_local_name_when_no_label_predicate():
    ttl = '@prefix ex: <http://example.org/> . ex:someResource ex:p "v" .'
    doc = _doc(ttl, graph_id="g")
    assert _node(doc, "http://example.org/someResource")["label"] == "someResource"


def test_label_prefers_language_less_literal_over_tagged():
    ttl = """
    @prefix ex: <http://example.org/> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    ex:a rdfs:label "Untagged", "Etiquette"@fr .
    """
    doc = _doc(ttl, graph_id="g")
    assert _node(doc, "http://example.org/a")["label"] == "Untagged"


# ─── Literal type conversion (BSON/JSON-safe only) ──────────────────────────────

LITERAL_TTL = """
@prefix ex: <http://example.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:a ex:when "2026-09-23T10:00:00Z"^^xsd:dateTime ;
     ex:active "true"^^xsd:boolean ;
     ex:price "19.99"^^xsd:decimal ;
     ex:score "3.5"^^xsd:float ;
     ex:dob "2026-09-23"^^xsd:date ;
     ex:plain "hello" .
"""


def test_literal_conversion_safe_types():
    import datetime
    doc = _doc(LITERAL_TTL, graph_id="g")
    attrs = _node(doc, "http://example.org/a")["attributes"]
    assert isinstance(attrs["ex:when"], datetime.datetime)
    assert attrs["ex:active"] is True
    assert isinstance(attrs["ex:score"], float) and attrs["ex:score"] == 3.5
    assert attrs["ex:plain"] == "hello"


def test_literal_conversion_digit_led_decimal_becomes_native_float():
    # xsd:decimal's .toPython() gives a non-BSON-safe decimal.Decimal, but
    # the lexical form "19.99" starts with a digit, so it's parsed directly
    # into a native float rather than falling back to lexical text.
    doc = _doc(LITERAL_TTL, graph_id="g")
    attrs = _node(doc, "http://example.org/a")["attributes"]
    assert attrs["ex:price"] == 19.99 and isinstance(attrs["ex:price"], float)


def test_literal_conversion_bare_date_still_falls_back_to_lexical_string():
    # A bare xsd:date is exempt from digit-led numeric parsing (it would
    # otherwise fail to cast and become -1) — it keeps its pre-existing
    # fallback to lexical text, since BSON can't store a datetime.date.
    doc = _doc(LITERAL_TTL, graph_id="g")
    attrs = _node(doc, "http://example.org/a")["attributes"]
    assert attrs["ex:dob"] == "2026-09-23" and isinstance(attrs["ex:dob"], str)


def test_malformed_literal_does_not_raise():
    # An out-of-range integer literal: toPython() may raise internally — must
    # still fall back to the lexical string rather than crash the import.
    # "not-a-number" isn't digit-led, so the digit-sniffing rule doesn't apply.
    ttl = '@prefix ex: <http://example.org/> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> . ex:a ex:n "not-a-number"^^xsd:integer .'
    doc = _doc(ttl, graph_id="g")
    assert _node(doc, "http://example.org/a")["attributes"]["ex:n"] == "not-a-number"


# ─── Digit/quote lexical sniffing (text vs. numeric attribute values) ───────────

def test_user_example_quoted_string_becomes_text_bare_decimal_becomes_numeric():
    ttl = """
    @prefix ex: <http://example.com/> .
    ex:Eve ex:sex "female" .
    ex:Eve ex:rating 12.2 .
    """
    doc = _doc(ttl, graph_id="g")
    attrs = _node(doc, "http://example.com/Eve")["attributes"]
    assert attrs["ex:sex"] == "female" and isinstance(attrs["ex:sex"], str)
    assert attrs["ex:rating"] == 12.2 and isinstance(attrs["ex:rating"], float)


def test_digit_led_value_wins_even_when_rdf_typed_as_a_plain_string():
    # A quoted string that happens to look like a number is still numeric —
    # classification is driven by the lexical form's first character, not
    # by the RDF-declared datatype (here, an untyped/xsd:string literal).
    ttl = '@prefix ex: <http://example.com/> . ex:Eve ex:zip "12345" .'
    doc = _doc(ttl, graph_id="g")
    attrs = _node(doc, "http://example.com/Eve")["attributes"]
    assert attrs["ex:zip"] == 12345 and isinstance(attrs["ex:zip"], int)


def test_digit_led_value_that_fails_to_cast_falls_back_to_negative_one():
    ttl = '@prefix ex: <http://example.com/> . ex:Eve ex:code "12.2abc" .'
    doc = _doc(ttl, graph_id="g")
    attrs = _node(doc, "http://example.com/Eve")["attributes"]
    assert attrs["ex:code"] == -1 and isinstance(attrs["ex:code"], int)


def test_negative_typed_number_still_passes_through_natively():
    # Not digit-led (starts with '-'), but still an RDF-typed number — keeps
    # passing through as a native int rather than falling back to text.
    ttl = '@prefix ex: <http://example.com/> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> . ex:Eve ex:balance "-5"^^xsd:integer .'
    doc = _doc(ttl, graph_id="g")
    attrs = _node(doc, "http://example.com/Eve")["attributes"]
    assert attrs["ex:balance"] == -5 and isinstance(attrs["ex:balance"], int)


def test_resource_valued_object_is_never_swept_into_an_attribute():
    # A digit-led or quote-led lexical rule only applies to LITERAL objects.
    # An IRI/blank-node object — never starting with a digit or a quote in
    # this sense — still becomes an ordinary hyperedge reference, not an
    # attribute, regardless of anything in the digit/quote value rule above.
    ttl = """
    @prefix ex: <http://example.com/> .
    ex:Eve ex:sex "female" .
    ex:Eve ex:sibling ex:Cain .
    """
    doc = _doc(ttl, graph_id="g")
    eve = _node(doc, "http://example.com/Eve")
    assert "ex:sibling" not in eve["attributes"]
    assert any(
        e["relation"] == "http://example.com/sibling"
        and e["members"] == [
            {"node_id": "http://example.com/Eve", "seq": 0},
            {"node_id": "http://example.com/Cain", "seq": 1},
        ]
        for e in doc["edges"]
    )


# ─── Blank nodes ─────────────────────────────────────────────────────────────────

def test_blank_node_gets_a_stable_bnode_prefixed_id():
    # Blank nodes have no IRI to expand — they keep the bnode:<label> scheme.
    n3 = '@prefix ex: <http://example.org/> . _:x ex:knows ex:eve .'
    doc = rdf_to_export_document(n3, "n3", "g")
    bnode_ids = [n["id"] for n in doc["nodes"] if n["id"].startswith("bnode:")]
    assert len(bnode_ids) == 1
    edge = doc["edges"][0]
    assert edge["members"][0]["node_id"] == bnode_ids[0]
    assert edge["members"][1]["node_id"] == "http://example.org/eve"


def test_blank_node_repeated_reference_reuses_same_id():
    n3 = '@prefix ex: <http://example.org/> . _:x ex:p ex:a . _:x ex:q ex:b .'
    doc = rdf_to_export_document(n3, "n3", "g")
    bnode_ids = {m["node_id"] for e in doc["edges"] for m in e["members"] if m["node_id"].startswith("bnode:")}
    assert len(bnode_ids) == 1  # same blank node in both triples, not minted twice


def test_blank_node_id_has_no_dots():
    # rdflib blank node labels are alnum already, but assert the invariant
    # explicitly since bnode ids stay sanitized (unlike URIRef ids, which are
    # now full IRIs and may legitimately contain '.').
    n3 = '@prefix ex: <http://example.org/> . _:x ex:p ex:a .'
    doc = rdf_to_export_document(n3, "n3", "g")
    bnode_id = next(n["id"] for n in doc["nodes"] if n["id"].startswith("bnode:"))
    assert "." not in bnode_id


# ─── Id minting ──────────────────────────────────────────────────────────────────

def test_ids_are_the_full_iri_string_verbatim():
    ttl = '@prefix ex: <http://example.org/> . <http://example.org/a.b.c> ex:p "v" .'
    doc = _doc(ttl, graph_id="g")
    assert {n["id"] for n in doc["nodes"]} == {"http://example.org/a.b.c"}


def test_different_namespaces_same_local_name_get_different_ids():
    ttl = """
    @prefix a: <http://example.org/a#> .
    @prefix b: <http://example.org/b#> .
    a:x a:p "1" .
    b:x b:p "2" .
    """
    doc = _doc(ttl, graph_id="g")
    ids = {n["id"] for n in doc["nodes"]}
    assert ids == {"http://example.org/a#x", "http://example.org/b#x"}


def test_id_minter_dedup_guard_never_merges_two_different_terms():
    # The dedup-suffix loop is unreachable in ordinary use (full IRIs and
    # bnode labels are already unique) — this forces it directly to prove
    # the "never silently merge two different terms" guard still works.
    import rdflib
    g = rdflib.Graph()
    t = rdflib.URIRef("http://example.org/dup")
    minter = _IdMinter(g)
    minter._used.add(str(t))  # simulate a prior, different term having already minted this id
    got = minter.id_for(t)
    assert got != str(t)
    assert got.startswith(f"{t}-")
    assert minter.id_for(t) == got  # cached on second call, not re-suffixed


# ─── Determinism ─────────────────────────────────────────────────────────────────

def test_output_is_deterministic_across_repeated_parses():
    doc1 = _doc()
    doc2 = _doc()
    assert doc1 == doc2


def test_nodes_sorted_by_id():
    doc = _doc()
    ids = [n["id"] for n in doc["nodes"]]
    assert ids == sorted(ids)


# ─── Cross-format equivalence ─────────────────────────────────────────────────────

RDFXML_EQUIV = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:foaf="http://xmlns.com/foaf/0.1/"
         xmlns:ex="http://example.org/">
  <foaf:Person rdf:about="http://example.org/carol">
    <foaf:name>Carol</foaf:name>
    <foaf:knows rdf:resource="http://example.org/dave"/>
  </foaf:Person>
</rdf:RDF>"""

JSONLD_EQUIV = """{
  "@context": {"foaf": "http://xmlns.com/foaf/0.1/", "ex": "http://example.org/",
               "knows": {"@id": "foaf:knows", "@type": "@id"}},
  "@id": "ex:carol",
  "@type": "foaf:Person",
  "foaf:name": "Carol",
  "knows": "ex:dave"
}"""

N3_EQUIV = """
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix ex: <http://example.org/> .
ex:carol a foaf:Person ; foaf:name "Carol" ; foaf:knows ex:dave .
"""


@pytest.mark.parametrize("text,fmt", [
    (RDFXML_EQUIV, "xml"), (JSONLD_EQUIV, "json-ld"), (N3_EQUIV, "n3"),
])
def test_equivalent_rdf_in_different_formats_produces_the_same_mapping(text, fmt):
    doc = rdf_to_export_document(text, fmt, "g")
    carol = _node(doc, CAROL)
    assert carol["label"] == "Carol"
    assert carol["type"] == "Person"
    assert doc["edges"] == [{
        "relation": KNOWS, "flavor": "hub",
        "members": [{"node_id": CAROL, "seq": 0}, {"node_id": "http://example.org/dave", "seq": 1}],
    }]


# ─── Error handling ───────────────────────────────────────────────────────────────

def test_malformed_turtle_raises_rdf_format_error():
    with pytest.raises(RdfFormatError, match="Could not parse as turtle"):
        rdf_to_export_document("this is not { valid turtle @@@", "turtle", "g")


def test_malformed_jsonld_raises_rdf_format_error():
    with pytest.raises(RdfFormatError, match="Could not parse as json-ld"):
        rdf_to_export_document("{not valid json", "json-ld", "g")


def test_wrong_format_for_content_raises_rdf_format_error():
    # Feeding Turtle text to the RDF/XML parser must fail cleanly, not hang or crash.
    with pytest.raises(RdfFormatError):
        rdf_to_export_document(TTL_BASIC, "xml", "g")


def test_empty_graph_produces_empty_nodes_and_edges():
    doc = rdf_to_export_document("", "turtle", "g")
    assert doc["nodes"] == [] and doc["edges"] == []


# ─── OWL axioms -> HypergraphAI axiom hyperedges ────────────────────────────────
# hgai/core/inference.py recognizes "owl:transitive" and "owl:inverse-of" by
# exact string match against a relation's atomic axiom hyperedges (see
# scripts/seeds/hgai-hypergraph-eden.export.yml's edge:child-trans and
# edge:parent-inv-child for the hand-asserted shape these must match).

HAS_PARENT = "http://example.com/hasParent"
HAS_CHILD = "http://example.com/hasChild"


def test_owl_transitive_property_becomes_a_single_member_axiom_edge():
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:hasParent a owl:TransitiveProperty .
    """
    doc = _doc(ttl, graph_id="g")
    trans = [e for e in doc["edges"] if e["relation"] == "owl:transitive"]
    assert trans == [{
        "relation": "owl:transitive", "flavor": "hub",
        "members": [{"node_id": HAS_PARENT, "seq": 0}],
    }]


def test_owl_inverse_of_becomes_a_two_member_axiom_edge_subject_then_object():
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:hasParent owl:inverseOf ex:hasChild .
    """
    doc = _doc(ttl, graph_id="g")
    assert doc["edges"] == [{
        "relation": "owl:inverse-of", "flavor": "hub",
        "members": [{"node_id": HAS_PARENT, "seq": 0}, {"node_id": HAS_CHILD, "seq": 1}],
    }]


def test_owl_inverse_of_relation_is_the_fixed_hgai_spelling_not_the_owl_curie_or_iri():
    # HypergraphAI's inference engine hardcodes the literal string
    # "owl:inverse-of" (hyphenated) — never rdflib's own CURIE for the real
    # predicate ("owl:inverseOf", no hyphen) and never the full OWL IRI,
    # regardless of what prefix the source file happens to bind.
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix o: <http://www.w3.org/2002/07/owl#> .
    ex:hasParent o:inverseOf ex:hasChild .
    """
    doc = _doc(ttl, graph_id="g")
    assert doc["edges"][0]["relation"] == "owl:inverse-of"


def test_owl_transitive_and_inverse_of_together_reproduce_the_eden_seed_shape():
    # The exact combination from the request: ex:hasParent is both
    # transitive and the inverse of ex:hasChild.
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:hasParent a owl:TransitiveProperty ;
        owl:inverseOf ex:hasChild .
    """
    doc = _doc(ttl, graph_id="g")
    edges = {e["relation"]: e for e in doc["edges"]}
    assert set(edges) == {"owl:transitive", "owl:inverse-of"}
    assert edges["owl:transitive"]["members"] == [{"node_id": HAS_PARENT, "seq": 0}]
    assert edges["owl:inverse-of"]["members"] == [
        {"node_id": HAS_PARENT, "seq": 0}, {"node_id": HAS_CHILD, "seq": 1},
    ]
    # The property's own rdf:type handling is unaffected/additive: it still
    # gets a normal `type`/`attributes.rdf_type` like any other rdf:type triple.
    parent_node = _node(doc, HAS_PARENT)
    assert parent_node["type"] == "TransitiveProperty"
    assert parent_node["attributes"]["rdf_type"] == ["http://www.w3.org/2002/07/owl#TransitiveProperty"]


def test_owl_inverse_of_object_still_becomes_its_own_hypernode():
    # ex:hasChild is never a subject here — only object-only-resource
    # handling (already covered generally) makes it a node at all.
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:hasParent owl:inverseOf ex:hasChild .
    """
    doc = _doc(ttl, graph_id="g")
    ids = {n["id"] for n in doc["nodes"]}
    assert ids == {HAS_PARENT, HAS_CHILD}


def test_non_transitive_property_gets_no_axiom_edge():
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:hasNickname a owl:DatatypeProperty .
    """
    doc = _doc(ttl, graph_id="g")
    assert doc["edges"] == []
    assert _node(doc, "http://example.com/hasNickname")["type"] == "DatatypeProperty"


def test_multiple_inverse_of_values_each_become_their_own_axiom_edge():
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:hasParent owl:inverseOf ex:hasChild, ex:hasOffspring .
    """
    doc = _doc(ttl, graph_id="g")
    inv = sorted((e["members"][1]["node_id"] for e in doc["edges"] if e["relation"] == "owl:inverse-of"))
    assert inv == ["http://example.com/hasChild", "http://example.com/hasOffspring"]


def test_owl_axiom_edges_match_the_eden_seed_shape_exactly():
    # scripts/seeds/hgai-hypergraph-eden.export.yml's edge:child-trans and
    # edge:parent-inv-child are hand-asserted, not RDF-imported — this proves
    # an RDF import produces byte-identical relation/flavor/member shapes,
    # so hgai/core/inference.py treats them exactly alike.
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:hasChild a owl:TransitiveProperty .
    ex:hasParent a owl:TransitiveProperty ;
        owl:inverseOf ex:hasChild .
    """
    doc = _doc(ttl, graph_id="g")
    edges_by_relation = {}
    for e in doc["edges"]:
        edges_by_relation.setdefault(e["relation"], []).append(e)
    assert len(edges_by_relation["owl:transitive"]) == 2
    assert all(e["flavor"] == "hub" for e in doc["edges"])
    assert all(set(e.keys()) == {"relation", "flavor", "members"} for e in doc["edges"])


# ─── owl:SymmetricProperty -> symmetric-flavored data edges + an axiom edge ─────
# Two things together: every data triple using the property gets its edge's
# FLAVOR changed to "symmetric" (a `symmetric` hyperedge already reads both
# directions unconditionally — atomic_pairs in hgai/core/inference.py — so
# this part needs no `infer: true`); AND, exactly like owl:transitive, a
# single-member "owl:symmetric" axiom edge naming the property is added too,
# as a safety net for any OTHER edge on that property `infer: true` might
# need to reason about (e.g. one asserted by hand as plain `hub`).

SIBLING = "http://example.com/sibling"
CAIN = "http://example.com/cain"
ABEL = "http://example.com/abel"
SETH = "http://example.com/seth"


def test_owl_symmetric_property_reproduces_the_request_exactly_two_edges():
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:sibling a owl:SymmetricProperty .
    ex:cain ex:sibling ex:abel .
    """
    doc = _doc(ttl, graph_id="g")
    assert len(doc["edges"]) == 2
    assert {
        "relation": SIBLING, "flavor": "symmetric",
        "members": [{"node_id": CAIN, "seq": 0}, {"node_id": ABEL, "seq": 1}],
    } in doc["edges"]
    assert {
        "relation": "owl:symmetric", "flavor": "hub",
        "members": [{"node_id": SIBLING, "seq": 0}],
    } in doc["edges"]


def test_owl_symmetric_relation_stays_the_full_predicate_iri_not_an_axiom_string():
    # Unlike owl:inverse-of, the relation is NOT replaced by a fixed
    # HypergraphAI spelling — it's still ex:sibling's own expanded IRI.
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:sibling a owl:SymmetricProperty .
    ex:cain ex:sibling ex:abel .
    """
    doc = _doc(ttl, graph_id="g")
    assert doc["edges"][0]["relation"] == SIBLING
    assert doc["edges"][0]["relation"] != "owl:symmetric"


def test_owl_symmetric_property_also_produces_a_single_member_axiom_edge():
    # Exactly mirrors owl:transitive's axiom edge: relation "owl:symmetric",
    # a single member (seq 0) naming the property itself.
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:sibling a owl:SymmetricProperty .
    ex:cain ex:sibling ex:abel .
    """
    doc = _doc(ttl, graph_id="g")
    axiom = [e for e in doc["edges"] if e["relation"] == "owl:symmetric"]
    assert axiom == [{
        "relation": "owl:symmetric", "flavor": "hub",
        "members": [{"node_id": SIBLING, "seq": 0}],
    }]


def test_owl_symmetric_property_detected_regardless_of_local_prefix():
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix o: <http://www.w3.org/2002/07/owl#> .
    ex:sibling a o:SymmetricProperty .
    ex:cain ex:sibling ex:abel .
    """
    doc = _doc(ttl, graph_id="g")
    assert doc["edges"][0]["flavor"] == "symmetric"


def test_every_triple_using_a_symmetric_property_gets_the_flavor_not_just_the_first():
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:sibling a owl:SymmetricProperty .
    ex:cain ex:sibling ex:abel .
    ex:cain ex:sibling ex:seth .
    ex:abel ex:sibling ex:seth .
    """
    doc = _doc(ttl, graph_id="g")
    data_edges = [e for e in doc["edges"] if e["relation"] == SIBLING]
    assert len(data_edges) == 3
    assert all(e["flavor"] == "symmetric" for e in data_edges)
    # The axiom edge is per-PROPERTY, not per-triple — exactly one, however
    # many data triples use ex:sibling.
    axiom_edges = [e for e in doc["edges"] if e["relation"] == "owl:symmetric"]
    assert len(axiom_edges) == 1
    assert len(doc["edges"]) == 4


def test_non_symmetric_property_data_edge_stays_hub():
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:knows a owl:ObjectProperty .
    ex:cain ex:knows ex:abel .
    """
    doc = _doc(ttl, graph_id="g")
    assert doc["edges"][0]["flavor"] == "hub"


def test_symmetric_property_own_node_still_gets_ordinary_rdf_type_handling():
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:sibling a owl:SymmetricProperty .
    ex:cain ex:sibling ex:abel .
    """
    doc = _doc(ttl, graph_id="g")
    sibling_node = _node(doc, SIBLING)
    assert sibling_node["type"] == "SymmetricProperty"
    assert sibling_node["attributes"]["rdf_type"] == ["http://www.w3.org/2002/07/owl#SymmetricProperty"]


def test_symmetric_transitive_and_inverse_of_can_coexist_on_different_properties():
    # A composite scenario exercising all three OWL rules at once, matching
    # the pattern established across this feature's three requests.
    ttl = """
    @prefix ex: <http://example.com/> .
    @prefix owl: <http://www.w3.org/2002/07/owl#> .
    ex:sibling a owl:SymmetricProperty .
    ex:hasParent a owl:TransitiveProperty ;
        owl:inverseOf ex:hasChild .
    ex:cain ex:sibling ex:abel .
    ex:cain ex:hasParent ex:adam .
    """
    doc = _doc(ttl, graph_id="g")
    by_relation = {}
    for e in doc["edges"]:
        by_relation.setdefault(e["relation"], []).append(e)
    assert by_relation[SIBLING][0]["flavor"] == "symmetric"
    assert by_relation["owl:symmetric"] == [{
        "relation": "owl:symmetric", "flavor": "hub",
        "members": [{"node_id": SIBLING, "seq": 0}],
    }]
    assert by_relation["owl:transitive"][0]["flavor"] == "hub"
    assert by_relation["owl:inverse-of"][0]["flavor"] == "hub"
    assert by_relation["http://example.com/hasParent"][0]["flavor"] == "hub"
