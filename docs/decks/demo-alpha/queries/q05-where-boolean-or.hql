hql:
  from: acme-eng
  match:
    type: hyperedge
  where:
    $or:
      - relation: mentors
      - relation: collaborates-with
  return:
    - id
    - relation
    - members
    - attributes
  as: mentorship_or_collaboration_edges
