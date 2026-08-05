hql:
  from: acme-eng
  match:
    type: hypernode
    node_type: Person
  where:
    attributes.hired_year:
      $lte: 2020
  return:
    - id
    - label
    - attributes.title
    - attributes.hired_year
  as: tenured_employees
