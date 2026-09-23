"""'Suppress Attribute Prefixes' import option (hgai.api.transfer_http).

Pure, storage-free unit tests for the local-name extraction and the
attribute-key rewriting it drives — no server, no DB."""

from hgai.api.transfer_http import (
    _local_attribute_name,
    _strip_attribute_key_prefixes,
    strip_attribute_prefixes_in_doc,
)


# ─── _local_attribute_name ──────────────────────────────────────────────────

def test_curie_strips_at_the_colon():
    assert _local_attribute_name("ex:sex") == "sex"


def test_full_iri_strips_at_the_last_slash():
    assert _local_attribute_name("http://example.org/description") == "description"


def test_full_iri_with_fragment_strips_at_the_hash():
    assert _local_attribute_name("http://www.w3.org/1999/02/22-rdf-syntax-ns#type") == "type"


def test_key_with_no_separator_is_unchanged():
    assert _local_attribute_name("plainkey") == "plainkey"


def test_key_ending_in_its_only_usable_separator_is_unchanged():
    # The last '/' has nothing after it — no usable local name, and it must
    # NOT fall back to splitting on the ':' from the IRI's own scheme.
    assert _local_attribute_name("http://example.org/") == "http://example.org/"


def test_key_ending_in_its_colon_is_unchanged():
    assert _local_attribute_name("ex:") == "ex:"


# ─── _strip_attribute_key_prefixes ──────────────────────────────────────────

def test_strips_a_single_unambiguous_curie_key():
    assert _strip_attribute_key_prefixes({"ex:sex": "female"}) == {"sex": "female"}


def test_strips_a_full_iri_key():
    assert _strip_attribute_key_prefixes({"http://example.org/description": "hello"}) == {"description": "hello"}


def test_empty_or_none_attributes_pass_through_unchanged():
    assert _strip_attribute_key_prefixes({}) == {}
    assert _strip_attribute_key_prefixes(None) is None


def test_key_with_no_prefix_is_unchanged():
    assert _strip_attribute_key_prefixes({"plain": "x"}) == {"plain": "x"}


def test_colliding_prefixed_keys_are_both_left_untouched():
    # foaf:name and dc:name would both strip to "name" — ambiguous, so neither is rewritten.
    attrs = {"foaf:name": "Alice", "dc:name": "A. Alice"}
    assert _strip_attribute_key_prefixes(attrs) == attrs


def test_stripped_key_colliding_with_an_existing_unprefixed_key_is_left_untouched():
    attrs = {"name": "Alice", "foaf:name": "A. Alice"}
    assert _strip_attribute_key_prefixes(attrs) == attrs


def test_multiple_unambiguous_keys_all_strip_independently():
    attrs = {"ex:sex": "female", "ex:rating": 12.2, "http://example.org/description": "hi"}
    assert _strip_attribute_key_prefixes(attrs) == {"sex": "female", "rating": 12.2, "description": "hi"}


# ─── strip_attribute_prefixes_in_doc ────────────────────────────────────────

def test_strips_both_node_and_edge_attributes_in_a_doc():
    doc = {
        "nodes": [
            {"id": "n1", "attributes": {"ex:sex": "female"}},
            {"id": "n2"},  # no attributes key at all — must not gain one
            {"id": "n3", "attributes": {}},  # empty — left as empty, not mutated into something new
        ],
        "edges": [
            {"id": "e1", "attributes": {"ex:weight": 3}},
        ],
    }
    result = strip_attribute_prefixes_in_doc(doc)
    assert result["nodes"][0]["attributes"] == {"sex": "female"}
    assert "attributes" not in result["nodes"][1]
    assert result["nodes"][2]["attributes"] == {}
    assert result["edges"][0]["attributes"] == {"weight": 3}


def test_doc_with_no_nodes_or_edges_keys_does_not_raise():
    assert strip_attribute_prefixes_in_doc({}) == {}
