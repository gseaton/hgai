---
id: help-shql-examples
label: SHQL worked examples
name: shql-examples
description: A gallery of copy-and-paste SHQL queries over the hello-world data — joins, filters, OPTIONAL, UNION, PIT, aggregation, inference.
tags: ["//Query Language (SHQL)", shql, examples, hello-world, cookbook]
status: active
---

# SHQL worked examples

All examples use the `hello-world` seed data (the Three Stooges). Paste them into the [Query screen](help:help-query-screen).

## 1. All Person hypernodes

```yaml
shql:
  from: hello-world
  select: [?person.id, ?person.label, ?person.attributes]
  where:
    - node: { bind: ?person, type: Person }
  order_by: ?person.label
```

## 2. Which hyperedges contain Moe Howard?

```yaml
shql:
  from: hello-world
  select: [?edge.id, ?edge.relation, ?edge.attributes]
  where:
    - edge:
        bind: ?edge
        members:
          - node: { id: moe-howard }
```

## 3. Multi-hop join — the classic-era lineup

`?stooge` and `?edge` are bound across node and edge patterns; the shared variable is the join key.

```yaml
shql:
  from: hello-world
  select: [?stooge.id, ?stooge.label, ?edge.attributes.era]
  where:
    - edge:
        bind: ?edge
        relation: has-member
        attributes: { era: classic }
        members:
          - node: { bind: ?group, id: three-stooges }
          - node: { bind: ?stooge, type: Person }
  order_by: ?stooge.label
```

## 4. FILTER on an attribute

```yaml
shql:
  from: hello-world
  select: [?person.id, ?person.label, ?person.attributes.born]
  where:
    - node: { bind: ?person, type: Person }
    - filter: "?person.attributes.born < '1900-01-01'"
```

## 5. OPTIONAL — siblings where they exist

```yaml
shql:
  from: hello-world
  select: [?person.label, ?sibling_edge.relation]
  where:
    - node: { bind: ?person, type: Person }
    - optional:
        - edge:
            bind: ?sibling_edge
            relation: sibling
            members:
              - node: { bind: ?person }
```

## 6. UNION — born before 1900 *or* named Curly

```yaml
shql:
  from: hello-world
  select: [?person.id, ?person.label]
  where:
    - union:
        - patterns:
            - node: { bind: ?person, type: Person }
            - filter: "?person.attributes.born < '1900-01-01'"
        - patterns:
            - node: { bind: ?person, type: Person }
            - filter: "CONTAINS(?person.label, 'Curly')"
  distinct: true
```

## 7. Point-in-time — who was a stooge in 1940?

```yaml
shql:
  from: hello-world
  at: "1940-06-01T00:00:00Z"
  select: [?stooge.label, ?edge.attributes]
  where:
    - edge:
        bind: ?edge
        relation: has-member
        members:
          - node: { id: three-stooges }
          - node: { bind: ?stooge, type: Person }
```

## 8. A space-scoped graph

```yaml
shql:
  from: alpha/alpha-hg
  select: [?person.id, ?person.label]
  where:
    - node: { bind: ?person, type: Person }
  order_by: ?person.label
```

## 9. Several graphs at once

```yaml
shql:
  from:
    - hello-world
    - alpha/alpha-hg
  select: [?n.id, ?n.label, ?n.type]
  where:
    - node: ?n
```

## 10. A remote server through a mesh

```yaml
shql:
  from: my-mesh.remote-server.alpha.alpha-hg
  select: [?n.id, ?n.label, ?n._mesh_server_id]
  where:
    - node: { bind: ?n, type: Person }
```

## 11. Positional member filter

Only edges whose **first** member (`seq: 0`) is `three-stooges`:

```yaml
shql:
  from: hello-world
  select: [?edge.id, ?edge.relation, ?edge.members]
  where:
    - edge:
        bind: ?edge
        relation: has-member
        members:
          - node_id: three-stooges
            seq: 0
```

## 12. Aggregate — edges per relation

```yaml
shql:
  from: hello-world
  select: [?edge.relation]
  where:
    - edge: { bind: ?edge }
  aggregate:
    count: true
    group_by: edge.relation
```

## 13. Inferencing — inverse relations

With an `owl:inverse-of [has-member, member-of]` axiom declared, this also returns synthesized `member-of` edges (`_inferred: true`):

```yaml
shql:
  from: hello-world
  infer: true
  select: [?edge.relation, ?edge.members, ?edge._inferred, ?edge._source_edge, ?edge._axiom]
  where:
    - edge: { bind: ?edge, relation: has-member }
```

## 14. Multi-key sort

```yaml
shql:
  from: hello-world
  select: [?edge.relation, ?edge.members]
  where:
    - edge: { bind: ?edge, relation: rel:member }
  order_by:
    - ?edge.relation desc
    - ?edge.members
```

Learn each piece in [Patterns](help:help-shql-patterns), [Filters](help:help-shql-filters) and [Advanced SHQL](help:help-shql-advanced).
