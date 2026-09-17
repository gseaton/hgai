"""Parameterized SHQL query templates (prepared statements).

Placeholder syntax, embedded anywhere in an otherwise-ordinary SHQL text
(typically as a YAML value, e.g. `relation: /$relationship:str$/`):

    /$name$/                       — untyped (defaults to str), required
    /$name:type$/                  — typed, required (type: str/int/float/bool)
    /$name:type:default$/          — typed, with a default value
    /$name:type:choice1|choice2$/  — typed, restricted to an enum of choices

The same parameter may be referenced more than once in one template (e.g.
used in both a `where:` filter and echoed in `select:`) — only the first
occurrence needs the full `:type:default` declaration; later ones may just
repeat `/$name$/`, but if they DO redeclare type/default/enum it must match
exactly, or `parse_parameters` raises (ambiguous — which one wins?).

Nothing here is SHQL-specific beyond the fact that substituted values are
rendered as YAML scalars (`_yaml_scalar`) so they drop safely into SHQL's
YAML syntax; the placeholder mechanism itself has no idea what SHQL is.
"""

import re
from typing import Any, Dict, List, Optional

import yaml

from hgai.models.parameterized_query import QueryParameter

SUPPORTED_TYPES = ("str", "int", "float", "bool")

# Group 1: name. Group 2: optional type (letters only — see module docstring,
# a bare `/$name:default$/` two-segment form is not supported, matching the
# spec's own examples, which always spell the type out before a default).
# Group 3: optional third segment (either a single default or a `|`-joined
# enum) — [^$]* so it can contain "|" and spaces but not a literal "$".
_TOKEN_RE = re.compile(r"/\$([A-Za-z_][A-Za-z0-9_-]*)(?::([A-Za-z]+))?(?::([^$]*))?\$/")


class QueryTemplateError(ValueError):
    """A template's placeholders are malformed, or the values supplied to
    render it don't satisfy them (missing required / wrong type / not in
    the declared enum)."""


def _coerce(raw: Any, type_: str, param_name: str) -> Any:
    """Convert `raw` (a string from a template default/form field, or
    already a native Python value from a JSON body) to `type_`."""
    if type_ == "str":
        return str(raw)
    text = str(raw).strip()
    try:
        if type_ == "int":
            return int(text)
        if type_ == "float":
            return float(text)
        if type_ == "bool":
            low = text.lower()
            if low in ("true", "1", "yes", "on"):
                return True
            if low in ("false", "0", "no", "off"):
                return False
            raise ValueError(text)
    except ValueError:
        pass
    raise QueryTemplateError(f"Parameter '{param_name}' expects a {type_} value, got {raw!r}")


def parse_parameters(template: str) -> List[QueryParameter]:
    """Every distinct parameter declared in `template`, in first-seen order.

    Raises QueryTemplateError for an unsupported type, a default that
    doesn't match its own declared type, or the same parameter name
    redeclared with a different type/default/enum at a later occurrence.
    """
    specs: Dict[str, QueryParameter] = {}
    for m in _TOKEN_RE.finditer(template or ""):
        name, type_raw, rest = m.group(1), m.group(2), m.group(3)

        # A bare `/$name$/` re-reference carries no declaration of its own
        # (type_raw and rest both None) — it always just means "the same
        # parameter already declared elsewhere", never a conflict, however
        # that parameter was declared. Only an occurrence that actually
        # spells out a type and/or default/enum can conflict with an
        # earlier declaration.
        if type_raw is None and rest is None and name in specs:
            continue

        type_ = (type_raw or "str").lower()
        if type_ not in SUPPORTED_TYPES:
            raise QueryTemplateError(
                f"Parameter '{name}' declares unsupported type '{type_raw}' "
                f"(supported: {', '.join(SUPPORTED_TYPES)})"
            )

        enum: Optional[List[str]] = None
        default: Optional[Any] = None
        if rest:
            if "|" in rest:
                enum = list(rest.split("|"))
            else:
                default = _coerce(rest, type_, name)

        spec = QueryParameter(name=name, type=type_, default=default, enum=enum)
        if name in specs:
            existing = specs[name]
            if existing.type != spec.type or existing.default != spec.default or existing.enum != spec.enum:
                raise QueryTemplateError(
                    f"Parameter '{name}' is declared more than once with a different type/default/enum"
                )
            continue
        specs[name] = spec
    return list(specs.values())


def _yaml_scalar(value: Any) -> str:
    """`value` rendered as a single YAML scalar, safe to splice into a line
    of SHQL text — e.g. a string containing ": " gets quoted automatically.
    `safe_dump` on a bare scalar appends a "...\n" document-end marker on
    its OWN line, never on the scalar's own line, so the first line alone
    is always exactly the scalar's rendered form."""
    return yaml.safe_dump(value, default_flow_style=True).splitlines()[0]


def resolve_parameter_values(specs: List[QueryParameter], provided: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce and validate `provided` against `specs`, filling in defaults
    for anything omitted. Collects every problem before raising (missing
    required / bad type / not in enum) rather than stopping at the first,
    so a caller — e.g. a wizard form — can report the whole picture at once.
    """
    resolved: Dict[str, Any] = {}
    errors: List[str] = []
    for spec in specs:
        raw = provided.get(spec.name)
        if raw is not None and raw != "":
            if spec.enum is not None and str(raw) not in spec.enum:
                errors.append(f"Parameter '{spec.name}' must be one of: {', '.join(spec.enum)}")
                continue
            try:
                resolved[spec.name] = _coerce(raw, spec.type, spec.name)
            except QueryTemplateError as e:
                errors.append(str(e))
        elif spec.default is not None:
            resolved[spec.name] = spec.default
        elif spec.enum:
            errors.append(f"Parameter '{spec.name}' requires a value (one of: {', '.join(spec.enum)})")
        else:
            errors.append(f"Parameter '{spec.name}' is required")
    if errors:
        raise QueryTemplateError("; ".join(errors))
    return resolved


def render_query(template: str, provided: Dict[str, Any]) -> str:
    """`template` with every `/$...$/` placeholder substituted by its
    resolved, YAML-safe value. Raises QueryTemplateError if `provided`
    doesn't satisfy every declared parameter — see resolve_parameter_values.
    """
    specs = parse_parameters(template)
    resolved = resolve_parameter_values(specs, provided)
    return _TOKEN_RE.sub(lambda m: _yaml_scalar(resolved[m.group(1)]), template)
