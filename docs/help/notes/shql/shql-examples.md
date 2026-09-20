---
id: help-shql-examples
label: SHQL worked examples
name: shql-examples
description: A gallery of copy-and-paste SHQL queries over the hello-world and eden seed hypergraphs — joins, filters, OPTIONAL, UNION, PIT, aggregation, inference.
tags: ["//Query Language (SHQL)", shql, examples, hello-world, eden, cookbook]
status: active
---

# SHQL worked examples

These queries run against the two example hypergraphs in `scripts/seeds/` — **`hello-world`** (Three Stooges, Rat Pack and Beatles lineups over time) and **`eden`** (a small family tree). Load them with `python scripts/seed_data.py` (see the [Quick Start](help:help-quick-start)), then paste any query into the [Query screen](help:help-query-screen); each one runs as written.

> **Member patterns match by id and position only.** Inside an edge's `members:` a pattern matches on `node_id` (or `id`), `seq` and `bind`. To also constrain a member's own properties (`type`, `tags`, `attributes`), bind its id to a variable and join to a `node:` pattern on that id — see examples 3, 7, 8 and 17. Write patterns in block style: an unquoted `?variable` inside flow-style `{ ... }` or `[ ... ]` is not valid YAML.

## 1. Find all Person hypernodes

```yaml
shql:
  from: hello-world
  select:
    - ?person.id
    - ?person.label
    - ?person.description
  where:
    - node:
        bind: ?person
        type: Person
  order_by: ?person.label
```

## 2. Find which hyperedges contain a specific node (Moe)

```yaml
shql:
  from: hello-world
  select:
    - ?edge.id
    - ?edge.label
    - ?edge.relation
  where:
    - edge:
        bind: ?edge
        members:
          - node:
              id: person:moe
```

## 3. Multi-hop join — the members of every Three Stooges lineup

A member pattern matches on `node_id` and `seq` only — it binds the member's *id*. To also constrain the member's own properties (its `type`, `tags`, `attributes`), bind the id to a variable and join to a `node` pattern on that id. The shared `?person_id` is the join key:

```yaml
shql:
  from: hello-world
  select:
    - ?edge.label
    - ?stooge.label
  where:
    - edge:
        bind: ?edge
        relation: rel:member
        members:
          - node_id: group:three-stooges
          - node_id: ?person_id
    - node:
        bind: ?stooge
        id: ?person_id
        type: Person
  order_by:
    - ?edge.label
    - ?stooge.label
```

## 4. FILTER on a property

Match `description` text with a filter expression (see [Filter Expressions](help:help-shql-filters)). Node attributes can also be matched directly inside the pattern — here only Frank Sinatra has `rat_pack_member: true`:

```yaml
shql:
  from: hello-world
  select:
    - ?person.id
    - ?person.label
    - ?person.description
  where:
    - node:
        bind: ?person
        type: Person
    - filter: "CONTAINS(?person.description, 'Howard')"
```

## 5. Match node attributes in the pattern

```yaml
shql:
  from: hello-world
  select:
    - ?person.label
    - ?person.attributes
  where:
    - node:
        bind: ?person
        type: Person
        attributes:
          rat_pack_member: true
```

## 6. OPTIONAL — include the Howard-brothers edge where it exists

```yaml
shql:
  from: hello-world
  select:
    - ?person.label
    - ?brothers.label
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

## 7. UNION — members of the Beatles OR the Rat Pack

```yaml
shql:
  from: hello-world
  select:
    - ?person.id
    - ?person.label
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
  order_by: ?person.label
```

## 8. Point-in-time query — who was a Stooge in 1940?

```yaml
shql:
  from: hello-world
  at: "1940-06-01T00:00:00Z"
  select:
    - ?stooge.label
    - ?edge.label
  where:
    - edge:
        bind: ?edge
        relation: rel:member
        members:
          - node_id: group:three-stooges
          - node_id: ?person_id
    - node:
        bind: ?stooge
        id: ?person_id
        type: Person
```

## 9. A space-scoped graph

Graphs owned by a [space](help:help-spaces) use `space/graph`:

```yaml
shql:
  from: alpha/alpha-hg
  select:
    - ?person.id
    - ?person.label
  where:
    - node:
        bind: ?person
        type: Person
  order_by: ?person.label
```

## 10. Several graphs at once

```yaml
shql:
  from:
    - hello-world
    - eden
  select:
    - ?n.id
    - ?n.label
    - ?n.type
  where:
    - node: ?n
```

## 11. A remote server through a mesh

```yaml
shql:
  from: my-mesh.remote-server.alpha.alpha-hg
  select:
    - ?n.id
    - ?n.label
    - ?n._mesh_server_id
  where:
    - node:
        bind: ?n
        type: Person
```

## 12. Positional member filter — find the first member by seq

Combine `seq` with `node_id` inside the same member pattern to require both to hold on the **same** array element, rather than "contains this node anywhere." The query below only matches `rel:lineup` edges whose *first* member (`seq: 0`) is `group:three-stooges` (the lineups edge, which also lists other edges as members):

```yaml
shql:
  from: hello-world
  select:
    - ?edge.id
    - ?edge.label
    - ?edge.members
  where:
    - edge:
        bind: ?edge
        relation: rel:lineup
        members:
          - node_id: group:three-stooges
            seq: 0
```

## 13. Aggregate — count edges grouped by relation

`aggregate` is computed over the full matched, deduplicated result set, before `order_by`/`limit`/`offset` paginate it. `group_by` names the *projected row key* a `select:` entry produces (no leading `?`) — here `?edge.relation` in `select:` becomes the row key `edge.relation`:

```yaml
shql:
  from: hello-world
  select:
    - ?edge.relation
  where:
    - edge:
        bind: ?edge
  aggregate:
    count: true
    group_by: edge.relation
```

## 14. Inferencing — axiom-driven expansion

`infer: true` extends the live candidate set with synthesized edges before member-pattern matching runs. The `hello-world` seed declares an `owl:inverse-of` axiom between `rel:member` and `rel:member-of`, so this query returns `rel:member-of` edges (the reverse of each literal `rel:member` fact) tagged `_inferred: true`, though none is stored:

```yaml
shql:
  from: hello-world
  infer: true
  select:
    - ?edge.relation
    - ?edge.members
    - ?edge._inferred
    - ?edge._axiom
  where:
    - edge:
        bind: ?edge
        relation: rel:member-of
```

## 15. Multi-key sort with descending order

`order_by` takes a list to sort by more than one field, and each field may carry a trailing `asc`/`desc` (default `asc`) — independent per field:

```yaml
shql:
  from: hello-world
  select:
    - ?edge.relation
    - ?edge.label
  where:
    - edge:
        bind: ?edge
  order_by:
    - ?edge.relation desc
    - ?edge.label
```

## 16. Eden — who are the parents of Cain?

The `eden` seed is a small family tree. A `rel:parent` edge is a hub edge: the child is the hub (`seq: 0`) and the parents follow.

```yaml
shql:
  from: eden
  select:
    - ?parent.label
  where:
    - edge:
        relation: rel:parent
        members:
          - node_id: person:cain
            seq: 0
          - node_id: ?parent_id
    - node:
        bind: ?parent
        id: ?parent_id
```

## 17. Eden — who is the mother of Cain?

Join to the parent's node and test its `sex` attribute:

```yaml
shql:
  from: eden
  select:
    - ?mother.label
  where:
    - edge:
        relation: rel:parent
        members:
          - node_id: person:cain
            seq: 0
          - node_id: ?parent_id
    - node:
        bind: ?mother
        id: ?parent_id
        attributes:
          sex: female
```

## 18. Eden — inferred: who is Enoch's parent?

Only Seth's `rel:child` edge (Seth → Enosh, Enoch) is stored. With `infer: true` the `owl:inverse-of` axiom between `rel:child` and `rel:parent` derives the reverse fact, so Enoch's parent is found:

```yaml
shql:
  from: eden
  infer: true
  select:
    - ?ancestor.label
  where:
    - edge:
        relation: rel:parent
        members:
          - node_id: person:enoch
            seq: 0
          - node_id: ?ancestor_id
    - node:
        bind: ?ancestor
        id: ?ancestor_id
  distinct: true
```

Learn each piece in [Patterns](help:help-shql-patterns), [Filters](help:help-shql-filters) and [Advanced SHQL](help:help-shql-advanced).
