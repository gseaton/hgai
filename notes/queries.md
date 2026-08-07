

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