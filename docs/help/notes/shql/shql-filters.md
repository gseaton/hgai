---
id: help-shql-filters
label: SHQL filter expressions
name: shql-filters
description: The FILTER expression syntax — comparisons, IN, CONTAINS, STARTS_WITH, BOUND, IS_TYPE and boolean operators.
tags: ["//Query Language (SHQL)", shql, filter, expression]
status: active
---

# Filter expressions

A `filter:` entry in `where:` applies an expression to already-bound variables:

```yaml
where:
  - node:
      bind: ?person
      type: Person
  - filter: "CONTAINS(?person.description, 'Howard')"
```

## Operators and functions

| Syntax | Description |
|---|---|
| `?var.field = value` | Equality |
| `?var.field != value` | Inequality |
| `?var.field < 10` | Comparison (`<`, `>`, `<=`, `>=`) |
| `?var.field IN [a, b, c]` | Membership |
| `CONTAINS(?var.label, "text")` | Case-insensitive substring |
| `STARTS_WITH(?var.label, "Mo")` | Prefix match |
| `ENDS_WITH(?var.label, "ard")` | Suffix match |
| `BOUND(?var)` | The variable is bound (useful after [OPTIONAL](help:help-shql-advanced)) |
| `IS_TYPE(?var, "Person")` | Type check |
| `expr AND expr` | Logical AND |
| `expr OR expr` | Logical OR |
| `NOT expr` | Logical NOT |

## Filter or attribute operator?

Both can express "the description mentions Howard" or "the sex attribute is female". Use an `attributes:` operator inside the pattern when you're matching while binding; use a `filter:` when the comparison involves a variable that is already bound, or combines several conditions with `AND`/`OR`. `IN` above and `attributes: {field: {$in: [...]}}` ([MongoDB operators](help:help-shql-patterns)) are the same idea at these two different points: filter-side membership on an already-bound field, versus pattern-side membership while the search itself runs.

## Coming from SPARQL?

`?var.field IN [a, b, c]` and `attributes: {field: {$in: [a, b, c]}}` already cover SPARQL's `VALUES` for the common case — matching a field against a list of literals — with no translation needed. Full SPARQL `VALUES` does more than that (binding several variables per row, or injecting a binding with no backing pattern at all), which neither of the above attempts; a fuller SPARQL-to-SHQL conversion, including `VALUES` for that general case, is tracked in `docs/architecture/sparql-to-shql-conversion-plan.md` and `docs/architecture/sparql-vs-shql-gaps.md`.

Back to [SHQL patterns](help:help-shql-patterns) or the [overview](help:help-shql-overview).
