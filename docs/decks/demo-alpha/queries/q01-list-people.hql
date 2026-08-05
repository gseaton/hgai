hql:
  from: acme-eng
  match:
    type: hypernode
    node_type: Person
  return:
    - id
    - label
    - attributes
  as: all_people
