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

Values are ordered the same way everywhere: missing/`null` first, then numbers, then text (so a column that mixes types still sorts). Rows that tie on every `order_by` key keep their natural order in memory, and are ordered by `id` when sorted by storage.

### Sorting and paging on large graphs

A query whose `where:` is a single `node:` or `edge:` pattern (same shape rules as [exact aggregates](#exact-aggregates-on-large-graphs), and the pattern must `bind` a variable) is sorted and paged **by the storage layer**: only the requested `limit` rows are read, `offset` pages are consistent, and nothing is cut off by the candidate cap. Each `order_by` key must be a scalar field of that variable that `select:` projects (or `select:` projects the whole variable, e.g. `*`). `meta.paging_pushdown` is `true` when this happened; otherwise rows are fetched up to the candidate cap and sorted in memory, and `meta.truncated` says whether the cap cut them short. Queries with an in-memory aggregate always take the in-memory path, because the aggregate needs every row.

### Joins over many matches

When a pattern is evaluated against many earlier matches — for example an `edge:` whose `members:` reuse a `?person` bound by a previous `node:` — the storage layer is queried once per *distinct* value, not once per match, and many values are fetched per query (for edges: "touching any of these node ids", then split back to each match; for nodes: "any of these ids"). Identical lookups are shared, so a cross join of two patterns reads the second one once. The number of values per query is `HGAI_SHQL_JOIN_BATCH_SIZE` (default 200). Results, their order and `meta.truncated` are the same as one query per match: if a batch might have lost documents to the candidate cap, it is transparently redone one value at a time.

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

### sum, avg, min, max

Numeric reducers name projected row keys too — one key or a list — and may be combined with `count` and `group_by`:

```yaml
select:
  - ?p.attributes.dept
  - ?p.attributes.salary
where:
  - node:
      bind: ?p
      type: Person
aggregate:
  count: true
  group_by: p.attributes.dept
  sum: p.attributes.salary
  avg: [p.attributes.salary]
  max: p.attributes.salary
```

`meta` then holds `sum`, `avg` and `max` as `{"<row key>": value}` over all matched rows, and `group_measures` as `{"<group>": {"sum": {"<row key>": value}, ...}}` next to `groups`. Semantics: `sum` and `avg` use numeric values only (text, booleans and missing values are ignored; `sum` of nothing is `0`, `avg` of nothing is `null`); `min` and `max` skip missing values and order numbers before text. `count_numeric: <row key>` reports how many values were numeric (the divisor of `avg`). Write row keys without a leading `?`.

### Exact aggregates on large graphs

A query whose `where:` is a single `node:` or `edge:` pattern — no `filter`, `optional`, `union`, `members`, `distinct` or `infer`, and every `group_by`/`sum`/`avg`/`min`/`max` key a scalar field such as `type`, `relation`, `flavor` or `attributes.<key>` that `select:` projects — (`count`, `sum`, `avg`, `min` and `max`, with an optional `group_by`) is aggregated **by the storage layer**. The result is exact however large the graph, is not limited by the per-pattern candidate cap, and `meta.aggregate_pushdown` is `true`. Any other query is aggregated in memory over the fetched candidates (`meta.aggregate_pushdown: false`), where `meta.truncated` tells you when the candidate cap cut the data short.

When you only need the aggregate, add `limit: 0` (allowed only together with `aggregate`) and no rows are fetched at all:

```yaml
shql:
  from: hello-world
  select:
    - ?edge.relation
  where:
    - edge: ?edge
  limit: 0
  aggregate:
    count: true
    group_by: edge.relation
```

A missing attribute is counted under the group `"None"`, as in the in-memory path. `group_by` on `tags` always uses the in-memory path.

## Point-in-time

`at: "<iso datetime>"` — see [Point-in-time queries](help:help-point-in-time).

## Inferencing

`infer: true` adds axiom-derived edges to matching — see [Inferencing](help:help-inferencing).

## Several graphs, spaces and meshes

`from:` may list several graphs (for example `hello-world` and `alpha/alpha-hg`, in a YAML list). Servers in a [mesh](help:help-meshes) are queried concurrently, using dot-notation such as `mesh.server.graph` (administrators only). Aggregates over a mesh are computed per server and merged exactly — see [Aggregates across servers](help:help-meshes).

## Permissions

A query runs as the calling account. Every graph named in `from:` must be accessible to it and the account needs the `query` operation on it — through `permissions.graphs` for unowned graphs, or space membership for `space_id/graph_id` references. A **logical graph** also requires access to each graph it composes. If any graph is refused the whole query is refused, before anything runs (`403` on REST, a `PermissionDenied` result over MCP); results are never partially filtered. Administrators can query everything. Mesh references require the admin role.

More: [Worked examples](help:help-shql-examples).
