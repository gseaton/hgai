hql:
  from: acme-eng
  at: "2023-06-01T00:00:00Z"
  match:
    type: hyperedge
    relation: has-member
  where:
    members:
      node_id: team:perception
  return:
    - id
    - members
    - attributes
  as: perception_roster_mid_2023
