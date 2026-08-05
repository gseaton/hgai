hql:
  from: acme-eng
  match:
    type: hyperedge
  where:
    members.node_id:
      $in: [person:dana-kim, person:priya-nair]
  return:
    - id
    - relation
    - members
  as: edges_with_dana_or_priya
