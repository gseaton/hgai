hql:
  from: acme-eng
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
    - valid_from
    - valid_to
  as: perception_team_all_versions
