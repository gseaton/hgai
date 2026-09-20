---
id: help-point-in-time
label: Point-in-time queries
name: point-in-time
description: "Ask what was true at a given instant using valid_from/valid_to and the SHQL `at:` key."
tags: ["//Concepts", temporal, pit, history, at]
status: active
---

# Point-in-time (PIT) queries

Hypernodes and hyperedges may carry `valid_from` and `valid_to`. A **point-in-time** query returns only what was valid at a chosen instant, so you can reconstruct "the state of the world" on any date.

## In SHQL

Add `at:` with an ISO-8601 datetime:

```yaml
shql:
  from: hello-world
  at: "1940-06-01T00:00:00Z"
  where:
    - edge:
        bind: ?edge
        relation: has-member
        members:
          - node: { id: three-stooges }
          - node: { bind: ?stooge, type: Person }
  select:
    - ?stooge.label
    - ?edge.attributes
```

`at:` is applied at every stage — both edge and node lookups — and works the same for [space-scoped graphs](help:help-spaces) and [mesh](help:help-meshes) references.

## In the Visualize screen

The **At (point-in-time)** field renders only hyperedges valid at that instant. Hypernodes are never filtered by it — they always render ([Visualize](help:help-visualize)).

More: [SHQL examples](help:help-shql-examples) (#7 and #12), [SHQL overview](help:help-shql-overview).
