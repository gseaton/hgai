---
id: help-shql-patterns
label: SHQL node and edge patterns
name: shql-patterns
description: The node and edge pattern syntax, binding variables, member patterns, and positional seq matching.
tags: ["//Query Language (SHQL)", shql, node, edge, pattern, members, seq]
status: active
---

# Node and edge patterns

Each entry in `where:` is a `node:` or `edge:` pattern (or a [filter/optional/union](help:help-shql-advanced)). Patterns are evaluated in order, binding variables as they match.

## Node pattern

```yaml
- node:
    bind: ?var          # bind matched node to this variable
    id: my-node-id      # exact id (a literal or a ?var)
    type: Person        # node type ("node_type:" also works)
    tags: [stooge]      # must have all listed tags
    status: active      # default: active
    attributes:
      born: { $lt: "1910-01-01" }   # MongoDB operators work here
```

There is also a compact form: `- node: ?person` (binds without conditions).

## Edge pattern

```yaml
- edge:
    bind: ?edge
    id: my-edge-id
    relation: has-member
    flavor: hub
    tags: [original]
    attributes:
      era: classic
    members:                        # member patterns (order-independent)
      - node: { bind: ?group, id: three-stooges }
      - node: { bind: ?stooge }     # bind any other member
```

The compact form is `- edge: ?e` followed by `relation:`, `members:`, and so on at the same level.

## Member patterns

`members:` entries can be written two ways:

- `node: { bind: ?x, id: ..., type: ... }` — match a member node by its properties, or
- `node_id: <literal or ?var>` with an optional `seq: <n>`.

**Positional `seq`.** When `seq` is combined with `node_id` in the same member pattern, both must hold on the *same* member — e.g. "the edge whose **first** member (`seq: 0`) is `three-stooges`":

```yaml
- edge:
    bind: ?edge
    relation: has-member
    members:
      - node_id: three-stooges
        seq: 0
```

If the edge's seq-0 slot holds someone else, the pattern simply doesn't match.

## Variables and joins

```yaml
where:
  - edge:
      bind: ?e
      relation: rel:president-of
      members:
        - node_id: nation:usa
        - node_id: ?president_id     # binds the other member's id
          seq: 0
  - node: ?president
    id: ?president_id                # join: look up that id
    node_type: Person
```

A variable used in several patterns must agree everywhere. Bound ids can be reused as `id:`/`node_id:`.

## MongoDB operators

Inside `attributes:` you may use standard operators (`$lt`, `$lte`, `$gt`, `$gte`, `$ne`, `$in`, `$all`, `$regex`, …), and top-level `$or`/`$and`/`$nor`/`$not` pass through unchanged — any unrecognized key maps straight to the underlying MongoDB query. For expressions over an already-bound variable use a [filter](help:help-shql-filters).

See also: [Worked examples](help:help-shql-examples), [Hyperedges](help:help-hyperedges).
