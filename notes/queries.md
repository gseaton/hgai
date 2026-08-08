

## Member Edges (HQL)

### Three Stooges
```yaml
  hql:
    from: hello-world
    match:
      type: hyperedge
      relation: rel:member
    where:
      members:
        node_id: group:three-stooges
    return:
      - id
      - relation
      - members
      - attributes
    as: memberships
```

### Rat Pack
```yaml
  hql:
    from: hello-world
    match:
      type: hyperedge
      relation: rel:member
    where:
      members:
        node_id: group:rat-pack
    return:
      - id
      - relation
      - members
      - attributes
    as: memberships

```

## Member Query (SHQL)

```yaml
  shql:
    from: hello-world
    where:
      - edge: ?edge
        relation: rel:member
        members:
          - node_id: group:three-stooges
    select:
      - ?edge.id
      - ?edge.relation
      - ?edge.members
      - ?edge.attributes
    as: memberships
```

```yaml
shql:
  from: hello-world
  at: "1934-01-01T00:00:00Z"
  where:
    - edge: ?e
      relation: "rel:member"
      members:
        - node_id: "group:three-stooges"
          seq: 0
  select:
    - ?e.id
    - ?e.relation
    - ?e.members
    - ?e.attributes
  as: first_member_is_stooges
```

## Member Node Attributes (SHQL)

The queries above return the raw `members` array — just `{node_id, seq}` pairs,
no `label`/`attributes`. HQL can't resolve that (no cross-collection join);
SHQL can, by adding a `node:` sub-pattern for the member you want resolved.
Anchor the known member (`group:three-stooges`) and let the other member slot
(`?member`) expand to the full node doc:

```yaml
shql:
  from: hello-world
  where:
    - edge:
        relation: "rel:member"
        members:
          - node: { id: "group:three-stooges" }
          - node: { bind: "?member" }
  select:
    - ?member.id
    - ?member.label
    - ?member.attributes
  as: three_stooges_member_attributes
```

```yaml
shql:
  from: hello-world
  at: "1935-01-01T00:00:00Z"
  where:
    - edge:
        relation: "rel:member"
        members:
          - node: { id: "group:three-stooges" }
          - node: { bind: "?member" }
  select:
    - ?member.id
    - ?member.label
    - ?member.attributes
  as: three_stooges_member_attributes
```

If you already know the specific edge's id (rather than anchoring by a known
member), filter on it directly instead — `edge: id:` now works:

```yaml
shql:
  from: hello-world
  where:
    - edge:
        id: "<edge-id>"
        members:
          - node: { bind: "?member" }
  select:
    - ?member.id
    - ?member.label
    - ?member.attributes
  as: edge_member_attributes
```