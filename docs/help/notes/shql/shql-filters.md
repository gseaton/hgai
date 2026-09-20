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

Both can express "the description mentions Howard" or "the sex attribute is female". Use an `attributes:` operator inside the pattern when you're matching while binding; use a `filter:` when the comparison involves a variable that is already bound, or combines several conditions with `AND`/`OR`.

Back to [SHQL patterns](help:help-shql-patterns) or the [overview](help:help-shql-overview).
