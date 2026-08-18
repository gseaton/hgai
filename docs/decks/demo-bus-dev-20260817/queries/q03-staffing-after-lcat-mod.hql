# q03 — identical query to q02, one field changed (the "at:" timestamp),
# pinned to 1 Jun 2025 — after the P00003 LCAT mod. Returns 2 results:
# Maria now as Senior Data Engineer, Devon still as Systems Engineer.
# Run q02 and q03 back-to-back — the difference is the whole point.
hql:
  from: defense-bd-demo
  at: "2025-06-01T00:00:00Z"
  match:
    type: hyperedge
    relation: staffed-on
  where:
    members:
      node_id: taskorder:to-047
  return:
    - members
    - attributes
  as: to047_roster_after_mod
