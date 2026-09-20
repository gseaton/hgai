---
id: help-parameterized-queries
label: Parameterized Queries
name: parameterized-queries
description: Reusable SHQL templates with typed /$name$/ placeholders, saved and run from the UI.
tags: ["//Using the Web UI", shql, template, parameters, prepared-statement]
status: active
---

# Parameterized Queries

A **parameterized query** is a saved [SHQL](help:help-shql-overview) *template* — ordinary SHQL text with placeholders — stored like a Note or Media item, independent of any hypergraph. It has a **name**, **label**, **description**, tags, and the SHQL text. You can list, search, tag and run them from the **Parameterized Queries** screen or pick one from the [Query screen](help:help-query-screen).

## Placeholder syntax

Placeholders are written `/$name$/` and may appear anywhere a YAML value can:

| Form | Meaning |
|---|---|
| `/$name$/` | Untyped (a string), required |
| `/$name:type$/` | Typed and required — `str`, `int`, `float` or `bool` |
| `/$name:type:default$/` | Typed, with a default value |
| `/$name:type:a\|b\|c$/` | Typed and restricted to a list of choices |

The same parameter can be used several times in a template; declare its type/default on the first use and simply repeat `/$name$/` afterwards (if you redeclare, it must match exactly).

## Example

```yaml
shql:
  from: hello-world
  where:
    - edge:
        bind: ?e
        relation: /$relationship:str:has-member$/
        members:
          - node: { bind: ?n, type: /$kind:str:Person$/ }
  select:
    - ?n.label
  limit: /$max:int:50$/
```

Running it shows a form with `relationship`, `kind` and `max`; supplied values are rendered as safe YAML scalars before the query runs. Missing required values, wrong types, or values outside the allowed choices are rejected with a clear message.

## API

Parameterized queries are managed under `/api/v1/parameterized-queries` ([REST API](help:help-rest-api)).
