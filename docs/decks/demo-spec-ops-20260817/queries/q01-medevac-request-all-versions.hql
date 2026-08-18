# q01 — every medevac-request fact ever recorded for PZ Bravo, no
# point-in-time filter. Returns both versions (original + reassessed) —
# nothing is hidden by default.
hql:
  from: defense-bd-demo-specops
  match:
    type: hyperedge
    relation: medevac-request
  where:
    members:
      node_id: loc:pz-bravo
  return:
    - id
    - members
    - attributes
    - valid_from
    - valid_to
  as: pz_bravo_requests_all_versions
