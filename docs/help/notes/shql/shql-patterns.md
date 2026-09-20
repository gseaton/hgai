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
      rat_pack_member: true         # exact match on an attribute
      # born: { $lt: "1910-01-01" } # MongoDB operators work here too
```

There is also a compact form: `- node: ?person` (binds without conditions).

## Edge pattern

```yaml
- edge:
    bind: ?edge
    id: edge:classic-stooges
    relation: rel:member
    flavor: hub
    tags: [some-tag]
    attributes:
      some_key: some-value
    members:                        # member patterns (order-independent)
      - node:
          bind: ?group
          id: group:three-stooges
      - node:
          bind: ?other              # bind any other member
```

The compact form is `- edge: ?e` followed by `relation:`, `members:`, and so on at the same level.

## Member patterns

`members:` entries can be written two ways:

- `node: { id: ... }` / `node:` with `bind:` and/or `id:` — bind or require a member, or
- `node_id: <literal or ?var>` with an optional `seq: <n>`.

A member pattern matches on **id and position only** (`id`/`node_id`, `seq`, `bind`); a `type`, `tags` or `attributes` written inside it is ignored. To constrain the member's own properties, bind its id and join to a `node:` pattern — see *Variables and joins* below.

**Positional `seq`.** When `seq` is combined with `node_id` in the same member pattern, both must hold on the *same* member — e.g. "the edge whose **first** member (`seq: 0`) is `group:three-stooges`":

```yaml
- edge:
    bind: ?edge
    relation: rel:lineup
    members:
      - node_id: group:three-stooges
        seq: 0
```

If the edge's seq-0 slot holds someone else, the pattern simply doesn't match.

## Variables and joins

```yaml
where:
  - edge:
      bind: ?e
      relation: rel:member
      members:
        - node_id: group:beatles
        - node_id: ?member_id        # binds another member's id
  - node:
      bind: ?member
      id: ?member_id                 # join: look that id up as a node ...
      type: Person                   # ... so its own properties can be constrained
```

A variable used in several patterns must agree everywhere. Bound ids can be reused as `id:`/`node_id:`. (Write patterns in block style — an unquoted `?variable` inside flow-style `{ ... }` is not valid YAML.)

## MongoDB operators

Inside `attributes:` you may use standard operators (`$lt`, `$lte`, `$gt`, `$gte`, `$ne`, `$in`, `$all`, `$regex`, …), and top-level `$or`/`$and`/`$nor`/`$not` pass through unchanged — any unrecognized key maps straight to the underlying MongoDB query. For expressions over an already-bound variable use a [filter](help:help-shql-filters).

See also: [Worked examples](help:help-shql-examples), [Hyperedges](help:help-hyperedges).
