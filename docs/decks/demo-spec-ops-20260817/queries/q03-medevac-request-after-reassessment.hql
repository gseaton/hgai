# q03 — identical query to q02, one field changed (the "at:" timestamp),
# pinned to 14:25Z — after Anvil's status was reassessed. Returns 1
# result: precedence "urgent-surgical". Run q02 and q03 back-to-back —
# the difference is the whole point.
hql:
  from: defense-bd-demo-specops
  at: "2026-08-10T14:25:00Z"
  match:
    type: hyperedge
    relation: medevac-request
  where:
    members:
      node_id: loc:pz-bravo
  return:
    - members
    - attributes
  as: pz_bravo_request_after_reassessment
