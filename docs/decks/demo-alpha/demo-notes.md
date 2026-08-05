Demo:

## Queries


### Beatles / No Beatles Yet

```yaml
hql:
  from: hg-bravo-alpha
  at: "1917-05-01T00:00:00Z"
  match:
    type: hyperedge
    relation: rel:member
  return:
    - members
    - attributes
    - valid_from
    - valid_to
```

### Beatles / Stuart

```yaml
hql:
  from: hg-bravo-alpha
  at: "1961-05-01T00:00:00Z"
  match:
    type: hyperedge
    relation: rel:member
  return:
    - members
    - attributes
    - valid_from
    - valid_to
```


### Beatles / Pete

```yaml
hql:
  from: hg-bravo-alpha
  at: "1962-07-01T00:00:00Z"
  match:
    type: hyperedge
    relation: rel:member
  return:
    - members
    - attributes
    - valid_from
    - valid_to
```

### Beatles / Ringo

```yaml
hql:
  from: hg-bravo-alpha
  at: "1969-09-01T00:00:00Z"
  match:
    type: hyperedge
    relation: rel:member
  return:
    - members
    - attributes
    - valid_from
    - valid_to
```