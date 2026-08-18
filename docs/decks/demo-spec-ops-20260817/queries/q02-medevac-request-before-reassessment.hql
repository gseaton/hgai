# q02 — same filter as q01, pinned to shortly after the initial request
# (14:05Z) — before Anvil's status was reassessed at 14:20Z. Returns 1
# result: precedence "priority".
hql:
  from: defense-bd-demo-specops
  at: "2026-08-10T14:05:00Z"
  match:
    type: hyperedge
    relation: medevac-request
  where:
    members:
      node_id: loc:pz-bravo
  return:
    - members
    - attributes
  as: pz_bravo_request_before_reassessment
