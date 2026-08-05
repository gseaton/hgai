hql:
  from: acme-eng
  match:
    type: hyperedge
    relation: staffed-on
  where:
    members.node_id:
      $all: [person:dana-kim, person:priya-nair]
  return:
    - id
    - relation
    - members
    - attributes
  as: shared_project_staffing
