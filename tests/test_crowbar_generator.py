"""Consistency of the authored ontology tables and helpers in
scripts/generators/crowbar_cyber_fraud.py (no database or source files needed).

The generator's data-driven output was verified against the real source files
when it ran; these tests keep the *authored* parts (classes, relation types,
axioms, concept hierarchies) internally consistent so a later edit can't
silently create a dangling reference in a generated ontology."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("crowbar_gen", ROOT / "scripts" / "generators" / "crowbar_cyber_fraud.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

RELATION_IDS = {r[0] for r in gen.RELATIONS}
CLASS_IDS = {c[0] for c in gen.CLASSES}


def test_ids_are_unique():
    assert len(RELATION_IDS) == len(gen.RELATIONS)
    assert len(CLASS_IDS) == len(gen.CLASSES)


def test_class_parents_exist_and_form_a_tree_rooted_at_entity():
    for id_, _label, _desc, parent in gen.CLASSES:
        if parent is None:
            assert id_ == "class:Entity"
        else:
            assert parent in CLASS_IDS, f"{id_} has unknown parent {parent}"
    for id_ in CLASS_IDS:               # every class reaches the root
        seen, cur = set(), id_
        while cur != "class:Entity":
            assert cur not in seen, f"cycle at {cur}"
            seen.add(cur)
            cur = next(c[3] for c in gen.CLASSES if c[0] == cur)


def test_relation_domains_ranges_and_inverses_are_consistent():
    by_id = {r[0]: r for r in gen.RELATIONS}
    for rid, _l, _d, inverse, domain, range_, broader in gen.RELATIONS:
        assert set(domain) <= CLASS_IDS and set(range_) <= CLASS_IDS, rid
        if broader:
            assert broader in RELATION_IDS, f"{rid}: unknown broader relation {broader}"
        if inverse:
            assert inverse in RELATION_IDS, f"{rid}: unknown inverse {inverse}"
            back = by_id[inverse]
            assert back[3] == rid, f"inverse of {rid} is {inverse}, but {inverse} names {back[3]}"
            assert set(back[4]) == set(range_) and set(back[5]) == set(domain), f"{rid}/{inverse}: domain/range not swapped"


def test_axioms_only_mention_declared_relations():
    for rid in gen.SYMMETRIC + gen.TRANSITIVE:
        assert rid in RELATION_IDS, rid
    for narrow, broad in gen.BROADER_TRANSITIVE + gen.NARROWER_TRANSITIVE:
        assert narrow in RELATION_IDS and broad in RELATION_IDS, (narrow, broad)


def test_relation_hierarchies_have_no_cycles():
    for pairs in (gen.BROADER_TRANSITIVE, [(n, b) for b, n in gen.NARROWER_TRANSITIVE]):
        up = {}
        for narrow, broad in pairs:
            up.setdefault(narrow, set()).add(broad)
        for start in up:
            seen, stack = set(), [start]
            while stack:
                for nxt in up.get(stack.pop(), ()):
                    assert nxt != start, f"cycle through {start}"
                    if nxt not in seen:
                        seen.add(nxt)
                        stack.append(nxt)


def test_the_five_axiom_kinds_the_request_names_are_all_present():
    assert gen.SYMMETRIC and gen.TRANSITIVE and gen.BROADER_TRANSITIVE and gen.NARROWER_TRANSITIVE
    assert any(r[3] for r in gen.RELATIONS)                       # owl:inverse-of


def test_concept_hierarchies_reference_known_concepts():
    groups = set(gen.MCAT_GROUPS)
    for label, (cid, parents, _d) in gen.MCAT_LEAVES.items():
        assert parents and set(parents) <= groups, label
    fraud_ids = set(gen.FRAUD_GROUPS) | {cid for cid, _ in gen.FRAUD_LEAVES.values()}
    for gid, (_l, _d, broaders) in gen.FRAUD_GROUPS.items():
        assert set(broaders) <= fraud_ids, gid
    for label, (cid, parents) in gen.FRAUD_LEAVES.items():
        assert parents and set(parents) <= fraud_ids, label
    for _a, _b, rel in gen.MCAT_MATCHES:
        assert rel in RELATION_IDS
    for label, (cid, group, _d) in gen.CHANNELS.items():
        assert group in gen.CHANNEL_GROUPS


def test_every_country_has_a_region_and_regions_are_rooted_at_world():
    for code, (_name, region) in gen.COUNTRIES.items():
        assert region in gen.REGIONS, code
    for rid, (_l, parent) in gen.REGIONS.items():
        assert (parent is None) == (rid == "region:world")


@pytest.mark.parametrize("text, expected", [("49", 49), ("49.0", 49), ("0", 0), ("0.0", 0), ("-3", -3), ("2171.42", 2171.42), ("0.5", 0.5), ("25000.0", 25000)])
def test_num_keeps_integral_values_as_ints_and_never_rounds(text, expected):
    got = gen.num(text)
    assert got == expected and type(got) is type(expected)


def test_flag_slug_chunks_iso():
    assert gen.flag("1") is True and gen.flag("0") is False and gen.flag("1.0") is True and gen.flag("0.0") is False
    assert gen.slug("Aaron's  Ville!") == "aaron-s-ville"
    assert [len(c) for c in gen.chunks(list(range(7)), 3)] == [3, 3, 1]
    assert gen.iso("2023-02-21 08:02:38") == "2023-02-21T08:02:38"
