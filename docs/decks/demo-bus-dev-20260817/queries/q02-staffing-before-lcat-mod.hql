# q02 — same filter as q01, pinned to 1 Jan 2025 — before the P00003 LCAT
# mod took effect (2025-04-01). Returns 2 results: Maria as Systems
# Engineer, Devon as Systems Engineer.
hql:
  from: defense-bd-demo
  at: "2025-01-01T00:00:00Z"
  match:
    type: hyperedge
    relation: staffed-on
  where:
    members:
      node_id: taskorder:to-047
  return:
    - members
    - attributes
  as: to047_roster_before_mod
