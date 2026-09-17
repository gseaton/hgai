"""Tests for parameterized-query template parsing/rendering
(hgai.core.query_templates) — the /$name:type:default$/ placeholder syntax.
"""

import pytest

from hgai.core.query_templates import (
    QueryTemplateError,
    parse_parameters,
    render_query,
    resolve_parameter_values,
)


def test_parse_bare_placeholder_defaults_to_str_required():
    specs = parse_parameters("shql:\n  from: /$graph$/\n")
    assert len(specs) == 1
    assert specs[0].name == "graph"
    assert specs[0].type == "str"
    assert specs[0].default is None
    assert specs[0].enum is None


def test_parse_typed_placeholder():
    specs = parse_parameters("limit: /$limit:int$/")
    assert specs[0].name == "limit"
    assert specs[0].type == "int"
    assert specs[0].default is None


def test_parse_typed_placeholder_with_default():
    specs = parse_parameters("category: /$category:str:Shoes$/")
    assert specs[0].type == "str"
    assert specs[0].default == "Shoes"


def test_parse_int_default_is_coerced_to_int():
    specs = parse_parameters("limit: /$limit:int:10$/")
    assert specs[0].default == 10
    assert isinstance(specs[0].default, int)


def test_parse_enum_placeholder():
    specs = parse_parameters("size: /$size:str:Small|Medium|Large$/")
    assert specs[0].enum == ["Small", "Medium", "Large"]
    assert specs[0].default is None


def test_parse_hyphenated_name():
    specs = parse_parameters("x: /$parameter-name$/")
    assert specs[0].name == "parameter-name"


def test_parse_rejects_unsupported_type():
    with pytest.raises(QueryTemplateError, match="unsupported type"):
        parse_parameters("x: /$foo:widget$/")


def test_parse_rejects_bad_default_for_declared_type():
    with pytest.raises(QueryTemplateError, match="expects a int value"):
        parse_parameters("x: /$limit:int:abc$/")


def test_parse_multiple_distinct_parameters_in_order():
    specs = parse_parameters(
        "shql:\n  from: /$graph:str$/\n  where:\n    - edge:\n        relation: /$relation:str:rel:member$/\n"
    )
    names = [s.name for s in specs]
    assert names == ["graph", "relation"]


def test_parse_repeated_bare_reference_reuses_first_declaration():
    template = "a: /$limit:int:5$/\nb: /$limit$/\n"
    specs = parse_parameters(template)
    assert len(specs) == 1
    assert specs[0].default == 5


def test_parse_conflicting_redeclaration_raises():
    template = "a: /$limit:int:5$/\nb: /$limit:int:10$/\n"
    with pytest.raises(QueryTemplateError, match="more than once"):
        parse_parameters(template)


def test_parse_no_placeholders_returns_empty_list():
    assert parse_parameters("shql:\n  from: hello-world\n") == []


# ── resolve_parameter_values ────────────────────────────────────────────────

def test_resolve_uses_default_when_omitted():
    specs = parse_parameters("x: /$category:str:Shoes$/")
    resolved = resolve_parameter_values(specs, {})
    assert resolved == {"category": "Shoes"}


def test_resolve_overrides_default_with_provided_value():
    specs = parse_parameters("x: /$category:str:Shoes$/")
    resolved = resolve_parameter_values(specs, {"category": "Hats"})
    assert resolved == {"category": "Hats"}


def test_resolve_coerces_int_string():
    specs = parse_parameters("x: /$limit:int$/")
    resolved = resolve_parameter_values(specs, {"limit": "42"})
    assert resolved == {"limit": 42}
    assert isinstance(resolved["limit"], int)


def test_resolve_coerces_float_string():
    specs = parse_parameters("x: /$score:float$/")
    resolved = resolve_parameter_values(specs, {"score": "3.5"})
    assert resolved == {"score": 3.5}


def test_resolve_coerces_bool_variants():
    specs = parse_parameters("x: /$flag:bool$/")
    for text, expected in [("true", True), ("0", False), ("Yes", True), ("off", False)]:
        assert resolve_parameter_values(specs, {"flag": text}) == {"flag": expected}


def test_resolve_missing_required_raises():
    specs = parse_parameters("x: /$graph$/")
    with pytest.raises(QueryTemplateError, match="required"):
        resolve_parameter_values(specs, {})


def test_resolve_bad_int_raises():
    specs = parse_parameters("x: /$limit:int$/")
    with pytest.raises(QueryTemplateError, match="expects a int value"):
        resolve_parameter_values(specs, {"limit": "not-a-number"})


def test_resolve_enum_accepts_valid_choice():
    specs = parse_parameters("x: /$size:str:Small|Medium|Large$/")
    assert resolve_parameter_values(specs, {"size": "Medium"}) == {"size": "Medium"}


def test_resolve_enum_rejects_invalid_choice():
    specs = parse_parameters("x: /$size:str:Small|Medium|Large$/")
    with pytest.raises(QueryTemplateError, match="must be one of"):
        resolve_parameter_values(specs, {"size": "ExtraLarge"})


def test_resolve_enum_without_value_is_required():
    specs = parse_parameters("x: /$size:str:Small|Medium|Large$/")
    with pytest.raises(QueryTemplateError, match="requires a value"):
        resolve_parameter_values(specs, {})


def test_resolve_reports_all_errors_together():
    specs = parse_parameters("a: /$limit:int$/\nb: /$graph$/\n")
    with pytest.raises(QueryTemplateError) as exc_info:
        resolve_parameter_values(specs, {"limit": "nope"})
    msg = str(exc_info.value)
    assert "limit" in msg and "graph" in msg


# ── render_query ─────────────────────────────────────────────────────────────

def test_render_substitutes_string_value():
    result = render_query("relation: /$relationship:str$/", {"relationship": "rel:member"})
    assert result == "relation: rel:member"


def test_render_substitutes_int_value_unquoted():
    result = render_query("limit: /$limit:int$/", {"limit": "5"})
    assert result == "limit: 5"


def test_render_quotes_string_needing_yaml_escaping():
    result = render_query("x: /$v:str$/", {"v": "has: colon"})
    assert result == "x: 'has: colon'"


def test_render_uses_default_when_value_omitted():
    result = render_query("category: /$category:str:Shoes$/", {})
    assert result == "category: Shoes"


def test_render_substitutes_every_occurrence_of_repeated_parameter():
    template = "a: /$x:int:1$/\nb: /$x$/\n"
    result = render_query(template, {"x": "9"})
    assert result == "a: 9\nb: 9\n"


def test_render_full_shql_example_from_spec():
    template = (
        "shql:\n"
        "  from: hello-world\n"
        "  where:\n"
        "    - edge: ?e\n"
        "      relation: /$relationship:str$/\n"
        "  select:\n"
        "    - ?e.relation\n"
    )
    result = render_query(template, {"relationship": "rel:member"})
    assert "relation: rel:member" in result
    assert "/$" not in result


def test_render_raises_on_missing_required_value():
    with pytest.raises(QueryTemplateError):
        render_query("x: /$graph$/", {})
