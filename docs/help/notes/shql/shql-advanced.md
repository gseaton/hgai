---
id: help-shql-advanced
label: OPTIONAL, UNION, aggregate, ordering and PIT
name: shql-advanced
description: Left outer joins, unions, multi-key sorting, aggregation, DISTINCT, inferencing and multi-graph queries in SHQL.
tags: ["//Query Language (SHQL)", shql, optional, union, aggregate, order_by, distinct]
status: active
---

# Advanced SHQL

## OPTIONAL — left outer join

Rows are kept even when the optional patterns don't match; their variables are simply unbound (test with `BOUND(?var)` in a [filter](help:help-shql-filters)).

```yaml
where:
  - node:
      bind: ?person
      type: Person
  - optional:
      - edge:
          bind: ?brothers
          relation: family:brother
          members:
            - node:
                bind: ?person
```

## UNION — alternatives

```yaml
where:
  - union:
      - patterns:
          - edge:
              relation: rel:member
              members:
                - node_id: group:beatles
                - node_id: ?member_id
      - patterns:
          - edge:
              relation: rel:member
              members:
                - node_id: group:rat-pack
                - node_id: ?member_id
  - node:
      bind: ?person
      id: ?member_id
      type: Person
distinct: true
```

## Ordering, paging, distinct

`order_by` takes a field or a list; each may end in `asc` (default) or `desc`:

```yaml
order_by:
  - ?edge.relation desc
  - ?edge.label
limit: 100
offset: 0
distinct: true
```

## Aggregation

`aggregate` is computed over the full matched, de-duplicated result **before** `order_by`/`limit`/`offset`. `group_by` names the *projected row key* (no leading `?`) that a `select:` entry produces — `?edge.relation` in `select:` becomes `edge.relation`:

```yaml
select:
  - ?edge.relation
where:
  - edge:
      bind: ?edge
aggregate:
  count: true
  group_by: edge.relation
```

The response `meta` then includes `count` (total matched rows) and `groups` (`{"<relation>": <count>}`).

## Point-in-time

`at: "<iso datetime>"` — see [Point-in-time queries](help:help-point-in-time).

## Inferencing

`infer: true` adds axiom-derived edges to matching — see [Inferencing](help:help-inferencing).

## Several graphs, spaces and meshes

`from:` may list several graphs (for example `hello-world` and `alpha/alpha-hg`, in a YAML list). Servers in a [mesh](help:help-meshes) are queried concurrently, using dot-notation such as `mesh.server.graph`.

More: [Worked examples](help:help-shql-examples).
